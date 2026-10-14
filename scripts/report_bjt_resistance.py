#!/usr/bin/env python3
"""Build a technical report from completed, real ngspice scan artifacts."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def number(value: object) -> str:
    if pd.isna(value):
        return "—"
    return f"{float(value):.7g}"


def table(frame: pd.DataFrame, columns: list[tuple[str, str]]) -> str:
    lines = ["| " + " | ".join(label for _, label in columns) + " |",
             "| " + " | ".join("---" for _ in columns) + " |"]
    for _, row in frame.iterrows():
        values = []
        for key, _ in columns:
            value = row[key]
            values.append(number(value) if isinstance(value, (float, int, np.number))
                          else str(value).replace("|", "\\|"))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/bjt")
    parser.add_argument("--model-dir", type=Path,
                        help="Directory containing the Code Model validation report")
    args = parser.parse_args()
    directory = args.output_dir.expanduser().resolve()
    summary = json.loads((directory / "simulation_summary.json").read_text())
    model_directory = (args.model_dir or (
        directory / "code_models" if (directory / "code_models").is_dir()
        else directory.parent / "code_model_validation"
        if (directory.parent / "code_model_validation").is_dir()
        else ROOT / "examples/code_model_validation")).resolve()
    model_result = json.loads((model_directory / "model_report.json").read_text())
    model_link = Path(os.path.relpath(model_directory / "model_report.md", directory)).as_posix()
    if not model_result["passed"]:
        raise ValueError("Code Model validation failed; do not produce a readiness report")
    op = pd.read_csv(directory / "operating_points.csv")
    ac = pd.read_csv(directory / "impedance.csv")
    calibration = pd.read_csv(directory / "calibration.csv")
    # Reject incomplete output rather than producing a plausible-looking report.
    required = {"run_id", "bias_kind", "target_ohm", "temperature_c",
                "sample_current_a", "port_voltage_v", "apparent_resistance_ohm",
                "incremental_fd_ohm", "within_voltage_window"}
    if not required <= set(op.columns):
        raise ValueError(f"Missing operating-point columns: {required - set(op.columns)}")
    calibrated = op[(op.bias_kind == "calibrated") & (op.sample_current_a != 0)].copy()
    if calibrated.empty or calibration.empty or ac.empty:
        raise ValueError("Calibration or AC scan is missing; report cannot establish readiness")
    calibrated["static_error_percent"] = (
        calibrated.apparent_resistance_ohm / calibrated.target_ohm - 1) * 100
    calibrated["incremental_error_percent"] = (
        calibrated.incremental_fd_ohm / calibrated.target_ohm - 1) * 100
    calibrated["within_voltage_window"] = calibrated.within_voltage_window.map(
        lambda value: str(value).lower() == "true")
    calibrated["sample_current_ua"] = calibrated.sample_current_a * 1e6
    nominal = calibrated[np.isclose(calibrated.sample_current_a, 50e-6)
                         & (calibrated.temperature_c == 25)].copy()
    nominal = nominal.merge(ac[np.isclose(ac.frequency_hz, 1)][["run_id", "z_real_ohm", "z_imag_ohm"]],
                            on="run_id", validate="one_to_one")
    zero = op[(op.bias_kind == "calibrated") & (op.sample_current_a == 0)
              & (op.temperature_c == 25)].copy()
    frozen_rows = []
    for target, group in calibrated.groupby("target_ohm", sort=False):
        passed = (group.static_error_percent.abs() <= 1) & group.within_voltage_window
        frozen_rows.append({
            "target_ohm": target, "conditions": len(group),
            "within_window": int(group.within_voltage_window.sum()),
            "pass_count": int(passed.sum()),
            "worst_static_error_percent": group.static_error_percent.abs().max(),
            "worst_incremental_error_percent": group.incremental_error_percent.abs().max(),
        })
    frozen = pd.DataFrame(frozen_rows)
    all_conditions_pass = bool((frozen.pass_count == frozen.conditions).all())
    dynamic_pass_count = int((calibrated.incremental_error_percent.abs() <= 1).sum())
    backpower = calibrated[(calibrated.port_voltage_v > 0)
                           & (calibrated.sample_current_a < 0)].copy()
    reference = op[(op.bias_kind == "reference") & (op.sample_current_a != 0)]
    if reference.empty:
        # The circuit field is also explicit in every reference deck.
        reference = op[(op.circuit == "reference") & (op.sample_current_a != 0)]
    reference_error = ((reference.apparent_resistance_ohm / reference.target_ohm - 1) * 100).abs().max()
    report_summary = {key: value for key, value in summary.items()
                      if key not in ("warnings", "failures")}
    diagnostics = {
        "warning_run_count": len(summary.get("warnings", [])),
        "failure_run_count": len(summary.get("failures", [])),
        "unique_warning_messages": sorted({message for record in summary.get("warnings", [])
                                            for message in record.get("warnings", [])}),
    }
    text = [
        "# BJT 表观电阻：真实 ngspice 参数扫描报告", "",
        "正式扫描时间（Asia/Shanghai）：" + datetime.fromisoformat(
            summary["timestamp_utc"]).astimezone(ZoneInfo("Asia/Shanghai")).isoformat(), "",
        "## 实测结论", "",
        ("此模型与拓扑在本次全部测试点满足示例 1% 静态误差指标。"
         if all_conditions_pass else
         "此模型与拓扑未能在本次电流、温度与方向组合下稳定模拟三个目标电阻。"
         "在名义点调到正确 V/I 并不意味着在其他条件下等效为电阻。"), "",
        "该结论限定于本报告的 generic NPN 模型与外部基极偏置拓扑；"
        "不能推广为所有 BJT 电路都不可实现，也不预测 DS3930 或未知 HVAC 控制器。", "",
        "## 电路、符号与实验边界", "",
        "参考电路分别使用 3399 Ω、2641 Ω、1858 Ω 的真实 SPICE 电阻元件，"
        "温度系数未设置，因此在本实验中为理想恒值电阻。BJT 使用 ngspice 内建标准"
        " Gummel–Poon NPN，显式模型参数保存在 circuits/bjt_resistance/。"
        "这是教学模型，不是厂商器件保证值，也不是 DS3930 内部模型。", "",
        "BJT 集电极接测试端口、发射极接地，基极通过 10 kΩ 接外部偏置电压源。"
        "正电流定义为从地注入测试端口；测试负电流时保持器件和偏置的连接不变。"
        "这是一种带独立偏置电源的有源三端电路，不是隔离的无源两端电阻。", "",
        "扫描 ±10、±50、±100 µA，0、25、50°C，以及固定偏置和一次校准后冻结的偏置。"
        "还测量零采样电流的开路端口偏移；零电流时 V/I 未定义，CSV 使用空值。"
        "每个目标仅在 25°C、+50 µA 校准一次。"
        "其他电流、温度和方向保持同一偏置，不逐点调参。", "",
        "±5 V 是本次报告采用的示例评估窗口，不是 HVAC 实际供电或采样限制。"
        "超出窗口的数学解被保留并标记，不能当成可实现的工作点。"
        "模型没有雪崩击穿和自热；尤其不能把理想电流源驱动产生的大电压外推到真实器件。"
        "1% 误差只是探索用判据，不是已知的 HVAC 或 DS3930 产品规格。", "",
        "## 静态与动态的区别", "",
        "静态表观电阻 R_static = V_DC / I_DC。增量电阻 r_diff = dV/dI，"
        "以固定温度和偏置的对称 DC 电流扰动求差分，非零工作点 ΔI = 0.001|I|。"
        "AC 分析在相同工作点线性化，Z(f) = ΔV(f)/ΔI(f)，"
        "独立偏置电压源的 AC 值为零，但仍保留 10 kΩ 基极终端。", "",
        "AC 的 1 µA 源是线性化分析的归一化系数，不代表另一次有限幅度瞬态。"
        "输出 1 Hz、1 kHz、100 kHz 的复阻抗。低频 Re(Z) 应与 DC 差分比较，"
        "高频 |Z| 是阻抗幅值，不能称作电阻。"
        "本实验未宣称完成某种未知 HVAC 采样波形的瞬态验证。", "",
        "## 名义单点校准后的实测值", "",
        table(nominal.sort_values("target_ohm", ascending=False), [
            ("target_ohm", "目标 Ω"), ("bias_v", "冻结偏置 V"),
            ("port_voltage_v", "端口 V"), ("apparent_resistance_ohm", "V/I Ω"),
            ("static_error_percent", "静态误差 %"),
            ("incremental_fd_ohm", "DC 差分 Ω"), ("z_real_ohm", "1 Hz Re(Z) Ω"),
        ]), "",
        "## 冻结偏置后的全部非零电流条件", "",
        table(frozen, [("target_ohm", "目标 Ω"), ("conditions", "条件数"),
                       ("within_window", "窗口内"), ("pass_count", "静态误差 ≤1% 且窗口内"),
                       ("worst_static_error_percent", "全部数学解最大静态误差 %"),
                       ("worst_incremental_error_percent", "全部数学解最大增量误差 %")]), "",
        "上表的最坏值保留所有求解结果，包含超出窗口的非物理高压解。"
        "应结合下表的窗口标志判断，而不能把最坏值当作真实器件测量。", "",
        f"冻结偏置的 {len(calibrated)} 个非零条件中，动态 DC 差分误差 ≤1% 的条件数为"
        f" {dynamic_pass_count}。详见各条件误差 CSV。", "",
        "### 电流与方向影响（25°C）", "",
        table(calibrated[calibrated.temperature_c == 25].sort_values(
            ["target_ohm", "sample_current_a"], ascending=[False, True]), [
                ("target_ohm", "目标 Ω"), ("sample_current_ua", "采样 µA"),
                ("port_voltage_v", "端口 V"), ("apparent_resistance_ohm", "V/I Ω"),
                ("static_error_percent", "静态误差 %"),
                ("incremental_fd_ohm", "DC 差分 Ω"),
                ("within_voltage_window", "±5 V 内")]), "",
        "### 温度影响（+50 µA，冻结名义偏置）", "",
        table(calibrated[np.isclose(calibrated.sample_current_a, 50e-6)].sort_values(
            ["target_ohm", "temperature_c"], ascending=[False, True]), [
                ("target_ohm", "目标 Ω"), ("temperature_c", "温度 °C"),
                ("port_voltage_v", "端口 V"), ("apparent_resistance_ohm", "V/I Ω"),
                ("static_error_percent", "静态误差 %"),
                ("within_voltage_window", "±5 V 内")]), "",
        "### 零采样电流偏移（25°C）", "",
        table(zero.sort_values("target_ohm", ascending=False), [
            ("target_ohm", "目标 Ω"), ("bias_v", "偏置 V"),
            ("port_voltage_v", "零电流端口 V"), ("base_current_a", "基极 A")]), "",
        f"参考真实电阻的最大静态相对误差为 {number(reference_error)}%。"
        "所有参考与 BJT 条件均保存在 CSV 中，包含电压、电流、偏置和温度。", "",
        "## 物理解释与限制", "",
        "固定基极偏置并不控制一个线性的 C–E 电阻：前向有源区的集电极主要表现为"
        "电流源，Early 效应给出输出增量电阻；进入饱和或改变方向后，"
        "BC/BE 结及反向增益参与导通，V/I 和 dV/dI 会不同。"
        "偏置温度漂移来自结电流的温度依赖与固定电压偏置。", "",
        "端口电流为负而端口电压仍为正时，V/I 为负、V×I 为负，"
        "表示外部偏置电源向测量端供能；它不具有普通正值无源电阻的双向特性。"
        "负的静态 V/I 不等于动态负阻，仍应独立查看 dV/dI 和 Re(Z)。"
        "判断控制器可否兼容还需要实际采样方向、波形、允许电压、温度误差和端口隔离需求。"
        "本报告不假设这些未知条件，亦不通过逐点校准强行制造等效电阻。", "",
        "以下是实际观察到的反向采样、正端口电压条件；端口功率按电流进入端口为正。", "",
        table(backpower.sort_values("target_ohm", ascending=False), [
            ("target_ohm", "目标 Ω"), ("temperature_c", "°C"),
            ("sample_current_ua", "采样 µA"), ("port_voltage_v", "端口 V"),
            ("apparent_resistance_ohm", "V/I Ω"), ("incremental_fd_ohm", "dV/dI Ω"),
            ("port_power_w", "端口吸收 W"), ("bias_power_delivered_w", "偏置提供 W")]), "",
        "## 数值验证、版本、警告及失败", "",
        "以下为测试程序的实际汇总记录；真实运行的命令、退出码、警告、"
        "原始 deck/日志/数据及 SHA-256 以 manifest 和归档保存。"
        "求解器成功与电阻模拟成功是两个不同结论。", "",
        "```json", json.dumps(report_summary, ensure_ascii=False, indent=2), "```", "",
        "诊断统计：", "", "```json",
        json.dumps(diagnostics, ensure_ascii=False, indent=2), "```", "",
        "逐次诊断见 [完整汇总](simulation_summary.json) 与 [执行清单](run_manifest.jsonl)。", "",
    ]
    sensitivity = directory / "gmin_sensitivity.csv"
    if sensitivity.is_file():
        sensitivity_frame = pd.read_csv(sensitivity)
        text += ["### gmin 敏感性复验", "",
                 "这是检查数值漏导敏感性的额外实际求解；改变 gmin 不会补上缺失的击穿或自热模型。"
                 "本模型的三端写法默认将衬底接地，相关数值 gmin 支路电流未计入仅三端的电流读出之和。"
                 "高压三端残差不能被解释成电荷守恒破坏；补充四端对照可单独读取该数值衬底电流。", "",
                 table(sensitivity_frame, [(key, key) for key in (
                     "comparison", "gmin_s", "port_voltage_v", "incremental_fd_ohm",
                     "voltage_ratio_to_baseline", "within_voltage_window", "status")
                     if key in sensitivity_frame.columns]), ""]
    substrate = directory / "substrate_diagnostic/substrate_comparison.csv"
    if substrate.exists():
        probe = pd.read_csv(substrate)
        probe_summary = json.loads((substrate.parent / "summary.json").read_text())
        if not probe_summary["passed"]:
            raise ValueError("Supplemental substrate diagnostics did not pass")
        text += ["### 默认衬底数值支路的实际四端对照", "",
                 "另执行 8 次 OP，把同一器件的默认接地衬底改为显式第四端并加零伏测流源。"
                 "两个连接方式的工作点相同；计入实测衬底电流后，"
                 "极端数学解的三端读出不平衡降为符合相对求解容差的剩余残差。", "",
                 table(probe[probe.substrate_connection == "explicit_ground"], [
                     ("case", "条件"), ("gmin_s", "gmin S"),
                     ("port_voltage_v", "端口 V"), ("substrate_current_out_a", "衬底流出 A"),
                     ("three_terminal_sum_a", "仅三端和 A"),
                     ("external_sum_including_substrate_a", "计入衬底后残差 A")]), "",
                 "[补充报告](substrate_diagnostic/report.md)记录符号、检查门限、"
                 "软件版本、官方实现参考、实际命令以及开发期间请求不可用内部向量的失败。"
                 "该补充没有把数值 gmin 电流视作真实器件的衬底漏电或击穿。", ""]
    text += ["## Code Model 环境修复", "",
             "旧 RC 日志保留了六个库加载失败的证据。原因是 rootless 解包后，"
             "包内 spinit 仍使用 /usr/lib/... 的系统绝对路径。"
             "安装脚本保持包内文件不变，在 .local/ngspice-runtime/spinit 生成重定位配置，"
             "并由 wrapper 设置 ngspice 官方支持的 SPICE_SCRIPTS。", "",
             f"独立验证见 [Code Model 测试报告]({model_link})。"
             "验证包含库动态链接依赖、模型注册及真实 analog/digital 电路计算。"
             "BJT 标准 NPN 是 ngspice 内建器件，BJT 或 RC 通过本身不能证明 XSPICE 库已加载。"
             "OSDI 默认仍未启用，本次没有宣称 OSDI 插件已验证。", "",
             "## 复现与产物", "", "```bash",
             "cd /workspace/spice-lab", "bash scripts/run_bjt_experiment.sh", "```", "",
             "若需刷新此实验分支的修复配置，先执行 bash scripts/setup_env.sh。"
             "使用当前现有环境与检出目录，不初始化新仓库或环境。", ""]
    development = directory / "development_attempt/first_run/simulation_summary.json"
    if development.exists():
        initial = json.loads(development.read_text())
        text += ["### 开发期间的检查失败", "",
                 "首次开发扫描得到真实工作点，但初始校验未全部通过。"
                 "高压下仅三端的电流输出之和没有计入默认接地衬底的数值 gmin 支路，"
                 "不能把这个三端读出残差解释为电荷守恒失败；"
                 "修正版加入独立的发射极零伏测流源验证外部 KCL，保留 intrinsic 残差供诊断。"
                 "第二轮的三端零伏传感器仍未测量默认接地衬底，因此读出残差仍包含衬底 gmin 电流。"
                 "最终版本将严格物理 KCL 验证限定在明确的 ±5 V 示例窗口，"
                 "同时报告全域残差及 gmin 修正诊断，没有把高压数据静默删除。"
                 "此外零采样点的初始 ±10 nA 差分扰动在高阻工作点不够小，"
                 "因此仅将零点扰动改为 ±0.1 nA，并再次实际求解与 AC 交叉验证。"
                 "非零采样点仍使用 ±0.1% 扰动。", "",
                 "初次开发检查：", "", "```json",
                 json.dumps(initial.get("checks", {}), indent=2, ensure_ascii=False), "```", "",
                 "[初次扫描记录](development_attempt/first_run/simulation_summary.json)及执行清单单独保留，"
                 "不将初次失败的校验描述为通过。", ""]
        second = directory / "development_attempt/second_run/simulation_summary.json"
        if second.exists():
            second_summary = json.loads(second.read_text())
            text += ["第二轮开发检查：", "", "```json",
                     json.dumps(second_summary.get("checks", {}), indent=2, ensure_ascii=False),
                     "```", "", "详细记录见 [开发诊断说明](development_attempt/README.md)。", ""]
    for path in sorted(directory.glob("*.png")):
        if path.name == "bjt_resistance_errors.png":
            text += ["误差图包含保留的窗口外数学解；极大误差来自无击穿模型外推，"
                     "不是真实器件预测。图中圆点是实际求解点，连接线仅辅助观察，"
                     "没有单独把窗口外圆点标成不同符号；请结合 CSV 的 within_voltage_window 列。", ""]
        elif path.name == "bjt_operating_points.png":
            text += ["工作点图的 ±5 V 水平线标示示例窗口。全部圆点为真实工作点，"
                     "窗口外数学解同样显示以保留诊断证据。", ""]
        text += [f"![{path.stem}]({path.name})", ""]
    text += ["数据：[工作点](operating_points.csv)、[复阻抗](impedance.csv)、"
             "[各目标误差](resistance_comparisons.csv)、[单点校准](calibration.csv)、"
             "[零电流偏移](offset.csv)。", ""]
    report = directory / "report.md"
    report.write_text("\n".join(text), encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
