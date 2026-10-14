#!/usr/bin/env python3
"""Verify ngspice's default grounded BJT substrate with independent OP probes.

This supplements the main scan; it does not replace or modify its data.  Each
case is run with an omitted substrate and with an explicitly grounded fourth
terminal.  The explicit terminal has a zero-volt current-sensing source.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "circuits/bjt_resistance/generic_npn.lib"
CASE_PARAMETERS = [
    ("extreme", 0.45, 0.0, 100e-6),
    ("nominal", 0.5844508316056654, 25.0, 50e-6),
]
SOURCE_LINKS = [
    "https://github.com/ngspice/ngspice/blob/master/src/spicelib/devices/bjt/bjtload.c#L458",
    "https://github.com/ngspice/ngspice/blob/master/src/spicelib/devices/bjt/bjtsetup.c#L454",
    "https://github.com/ngspice/ngspice/blob/master/src/spicelib/devices/bjt/bjtask.c#L239",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_op(path: Path) -> dict[str, float]:
    """Parse one real ngspice ASCII OP without any third-party dependencies."""
    header, values = path.read_text().split("Values:\n", 1)
    if "Flags: real" not in header or "No. Points: 1" not in header:
        raise ValueError(f"Expected one real OP sample in {path}")
    names = [line.split()[1] for line in header.split("Variables:\n", 1)[1].splitlines()
             if line.strip()]
    lines = [line.strip() for line in values.splitlines() if line.strip()]
    if len(names) != len(lines):
        raise ValueError(f"Variable/value count differs in {path}")
    numbers = [float(lines[0].split(maxsplit=1)[1])] + [float(line) for line in lines[1:]]
    import math
    if not all(math.isfinite(value) for value in numbers):
        raise ValueError(f"Non-finite OP sample in {path}")
    return dict(zip(names, numbers))


def netlist(name: str, bias: float, temperature: float, current: float,
            gmin: float, explicit: bool, model: str) -> str:
    substrate = " substrate" if explicit else ""
    substrate_source = "Vsubstrate substrate 0 DC 0" if explicit else ""
    substrate_readout = " i(vsubstrate)" if explicit else ""
    return f"""Default versus explicitly grounded BJT substrate: {name}
* Positive collector current enters Q; Vsubstrate current leaves Q to ground.
Isample 0 port DC {current:.16g}
Vcollector port collector DC 0
Q1 collector base emitter{substrate} GENERIC_NPN
Vemitter emitter 0 DC 0
{substrate_source}
Rbias supply base 10k
Vbias supply 0 DC {bias:.16g}
{model}
.temp {temperature:.16g}
.options tnom=25 reltol=1e-7 abstol=1e-13 vntol=1e-10 gmin={gmin:.16g}
.control
set noaskquit
set filetype=ascii
set numdgt=15
op
write op.raw v(port) v(base) i(vcollector) i(vbias) i(vemitter){substrate_readout} @q1[ic] @q1[ib] @q1[ie] @q1[is] @q1[gdsub]
quit
.endc
.end
"""


def observations(raw: dict[str, float]) -> dict[str, float]:
    # The three external-current sum omits the default grounded substrate path.
    three_terminal_sum = raw["i(vcollector)"] - raw["i(vbias)"] - raw["i(vemitter)"]
    substrate_out = raw.get("i(vsubstrate)", raw["@q1[is]"])
    model_sum = raw["@q1[ic]"] + raw["@q1[ib]"] + raw["@q1[ie]"]
    return {
        "port_voltage_v": raw["v(port)"],
        "base_voltage_v": raw["v(base)"],
        "collector_current_into_device_a": raw["i(vcollector)"],
        "base_current_into_device_a": -raw["i(vbias)"],
        "emitter_current_into_device_a": -raw["i(vemitter)"],
        "substrate_current_out_a": substrate_out,
        "model_is_a": raw["@q1[is]"],
        "model_gdsub_s": raw["@q1[gdsub]"],
        "three_terminal_sum_a": three_terminal_sum,
        "external_sum_including_substrate_a": three_terminal_sum - substrate_out,
        "model_readout_sum_a": model_sum,
        "model_readout_sum_including_is_a": model_sum + raw["@q1[is]"],
    }


def write_report(output: Path, summary: dict, rows: list[dict]) -> None:
    instant = datetime.fromisoformat(summary["timestamp_utc"]).astimezone(ZoneInfo("Asia/Shanghai"))
    lines = ["# BJT 默认接地衬底数值支路：补充实际验证", "",
             f"结果：**{'通过' if summary['passed'] else '失败'}**。时间：{instant.isoformat()}。", "",
             "本补充设计包含 8 次 OP：极端高压点及名义校准点 × 两个 gmin × 默认/显式接地衬底。",
             f"本次实际运行 {summary['counts']['ngspice_processes']} 次，得到 {summary['counts']['valid_op_samples']} 个有效 OP 样本。",
             "不修改主扫描的 252 个条件、298 次运行或原始数据。", "",
             "三端写法省略的衬底默认为地；显式四端写法加零伏源独立测量该支路。",
             "正集电极/基极/发射极电流定义进入器件；表内衬底电流为流出器件到地。",
             "故包含衬底的外部残差为三端电流和减去衬底流出电流。",
             "@q1 电流读出自身采用不同的支路记账；其 ic+ib+ie+is 和单独记录，",
             "不把这些读出直接等同于外部零伏测流源。", "",
             "| 条件 | gmin S | 衬底连接 | 端口 V | 衬底流出 A | 三端和 A | 计入衬底后残差 A | 读出 ic+ib+ie+is A |",
             "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |"]
    for row in rows:
        lines.append("| " + " | ".join([
            row["case"], f"{row['gmin_s']:.4g}", row["substrate_connection"],
            f"{row['port_voltage_v']:.10g}", f"{row['substrate_current_out_a']:.10g}",
            f"{row['three_terminal_sum_a']:.10g}", f"{row['external_sum_including_substrate_a']:.10g}",
            f"{row['model_readout_sum_including_is_a']:.10g}",
        ]) + " |")
    lines += ["", "显式与默认接地得到相同工作点。极端点的大部分三端电流和来自未计入的衬底数值支路；",
              "计入该支路后剩余约 10⁻¹¹ A 的求解残差，验证阈值使用 10⁻⁶ 相对电流及 10⁻¹² A 绝对项。",
              "这不代表真实器件的衬底泄漏、击穿或任何可实现的高压工作点，也不表示电荷守恒被破坏。", "",
              "## 复现", "", "```bash", "source .local/env.sh",
              "python scripts/verify_bjt_substrate.py --output-dir results/bjt_substrate", "```", "",
              "每次执行的 deck、日志、原始 OP 及 SHA-256 见 case 子目录与 run_manifest.jsonl。",
              "主验证使用当前安装 ngspice 44.2 实测；以下官方 GitHub 镜像 master 链接提供实现参照，",
              "不声称该网页快照与 Debian 二进制源码版本完全相同：", ""]
    lines += [f"- {link}" for link in SOURCE_LINKS]
    lines += ["", "当前 gdsub 实测等于 gmin，降低 gmin 可改变高压解，但不能补充缺失的击穿或自热模型。", "",
              "## 软件、执行与检查", "", "```json", json.dumps(summary, indent=2, ensure_ascii=False), "```", ""]
    development = output / "development_attempt"
    if development.is_dir():
        previous = summary.get("previous_formal_runs", [])
        previous_count = sum(item["ngspice_processes"] for item in previous)
        total_count = summary["counts"]["ngspice_processes"] + 16 + previous_count
        valid_count = summary["counts"]["valid_op_samples"] + 8 + sum(item["valid_op_samples"] for item in previous)
        lines += ["## 保留的诊断开发记录", "",
                  "development_attempt/ 保留首次临时探测的 16 次运行和原始文件：",
                  "其中前 8 次请求不可用内部节点向量而未生成 OP 输出，尽管 ngspice 退出码为零；",
                  "后 8 次删除该无效读出后成功。这些运行不计入本补充的 8 次正式验证或主扫描。",
                  f"当前验证、此前正式复跑与探索合计执行 {total_count} 次 ngspice；{valid_count} 个有效 OP 输出，8 个读出失败。",
                  "保存的执行清单为 development_attempt/manifest.json 与 readout_manifest.json；",
                  "前者记录首轮命令，读出重试使用相同 ngspice -b -o ngspice.log probe.cir 参数。",
                  "本次计数也见 summary.json 的 development_attempt 字段。", ""]
        if previous:
            lines += ["此前正式执行的摘要及可用原始证据保存于 run_history/；",
                      "其中首次正式执行曾被旧版脚本的重复执行覆盖，只保留实际运行摘要；",
                      "第二次正式执行的全部生成文件已在修复拒绝覆盖行为前归档。", ""]
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/bjt_substrate")
    parser.add_argument("--ngspice", default="ngspice")
    args = parser.parse_args()
    output = args.output_dir.expanduser().resolve()
    if (output / "run_manifest.jsonl").exists() or any(
            output.glob("*_ground_gmin*")):
        parser.error(f"Refusing to overwrite existing probe evidence: {output}; use a fresh output directory")
    output.mkdir(parents=True, exist_ok=True)
    rows, records = [], []
    summary = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "passed": False,
               "command": shlex.join([sys.executable, str(Path(__file__).resolve()),
                                      "--output-dir", str(output), "--ngspice", args.ngspice]),
               "python_version": platform.python_version(), "source_links": SOURCE_LINKS,
               "main_scan_is_unchanged": True,
               "source_sha256": {"scripts/verify_bjt_substrate.py": sha256(Path(__file__)),
                                  "circuits/bjt_resistance/generic_npn.lib": sha256(MODEL_PATH)}}
    try:
        executable = shutil.which(args.ngspice)
        if executable is None:
            raise RuntimeError(f"ngspice executable not found: {args.ngspice}")
        executable = str(Path(executable).resolve())
        version = subprocess.run([executable, "--version"], capture_output=True, text=True,
                                 timeout=30, check=True)
        summary["ngspice_version"] = next((line.strip("* ") for line in version.stdout.splitlines()
                                          if "ngspice-" in line), "unknown")
        (output / "ngspice_version.txt").write_text(version.stdout + version.stderr)
        model = MODEL_PATH.read_text()
        for case, bias, temperature, current in CASE_PARAMETERS:
            for gmin in [1e-12, 1e-14]:
                for explicit in [False, True]:
                    connection = "explicit_ground" if explicit else "implicit_ground"
                    name = f"{case}_{connection}_gmin{12 if gmin == 1e-12 else 14}"
                    directory = output / name
                    directory.mkdir(exist_ok=True)
                    for generated in ["op.raw", "ngspice.log", "console.log"]:
                        (directory / generated).unlink(missing_ok=True)
                    deck = directory / "probe.cir"
                    deck.write_text(netlist(name, bias, temperature, current, gmin, explicit, model))
                    command = [executable, "-b", "-o", "ngspice.log", "probe.cir"]
                    record = {"run_id": name, "cwd": str(directory), "command": shlex.join(command)}
                    process = subprocess.run(command, cwd=directory, capture_output=True, text=True,
                                             timeout=60, check=False)
                    record["returncode"] = process.returncode
                    (directory / "console.log").write_text(process.stdout + process.stderr)
                    log = (directory / "ngspice.log").read_text() if (directory / "ngspice.log").exists() else ""
                    record["warnings"] = [line for line in log.splitlines()
                                          if re.search(r"warning|singular|gmin stepping|source stepping", line, re.I)]
                    record["errors"] = [line for line in log.splitlines()
                                        if re.search(r"(^|\s)error|no writable vector|no convergence|failed", line, re.I)]
                    record["sha256"] = {str(path.relative_to(output)): sha256(path)
                                        for path in sorted(directory.iterdir()) if path.is_file()}
                    record["passed"] = process.returncode == 0 and not record["errors"] and (directory / "op.raw").is_file()
                    records.append(record)
                    if not record["passed"]:
                        raise RuntimeError(f"ngspice failed or produced invalid data: {name}")
                    row = {"case": case, "run_id": name, "substrate_connection": connection,
                           "bias_v": bias, "temperature_c": temperature, "sample_current_a": current,
                           "gmin_s": gmin, **observations(read_op(directory / "op.raw"))}
                    rows.append(row)
        checks = {
            "eight_valid_op_runs": len(rows) == 8 and all(record["passed"] for record in records),
            "model_readout_sum_with_is_below_1e-12_a": all(abs(row["model_readout_sum_including_is_a"]) < 1e-12 for row in rows),
            "external_kcl_with_substrate_within_solver_tolerance": all(
                abs(row["external_sum_including_substrate_a"]) < 1e-12 + 1e-6 * max(
                    abs(row[key]) for key in ["collector_current_into_device_a", "base_current_into_device_a",
                                             "emitter_current_into_device_a", "substrate_current_out_a"])
                for row in rows),
            "explicit_substrate_sensor_matches_model_is": all(
                abs(row["substrate_current_out_a"] - row["model_is_a"]) < 1e-12 for row in rows
                if row["substrate_connection"] == "explicit_ground"),
            "gdsub_equals_gmin": all(abs(row["model_gdsub_s"] / row["gmin_s"] - 1) < 1e-12 for row in rows),
        }
        paired = [(rows[index], rows[index + 1]) for index in range(0, len(rows), 2)]
        checks["implicit_and_explicit_ground_match"] = all(
            abs(first["port_voltage_v"] - second["port_voltage_v"]) < 1e-10 * max(1, abs(first["port_voltage_v"]))
            and abs(first["collector_current_into_device_a"] - second["collector_current_into_device_a"]) < 1e-12
            for first, second in paired)
        summary.update(checks=checks, passed=all(checks.values()))
    except Exception as error:
        summary["error"] = f"{type(error).__name__}: {error}"
    finally:
        if rows:
            with (output / "substrate_comparison.csv").open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
        (output / "run_manifest.jsonl").write_text("".join(json.dumps(record) + "\n" for record in records))
        summary["counts"] = {"ngspice_processes": len(records), "valid_op_samples": len(rows),
                             "warning_runs": sum(bool(record.get("warnings")) for record in records),
                             "failed_runs": sum(not record.get("passed", False) for record in records)}
        development = output / "development_attempt"
        if development.is_dir():
            exploratory_records = []
            for filename in ["manifest.json", "readout_manifest.json"]:
                path = development / filename
                if path.is_file():
                    exploratory_records.extend(json.loads(path.read_text()))
            summary["development_attempt"] = {
                "ngspice_processes": len(exploratory_records),
                "valid_op_outputs": sum((development / record["name"] / "op.raw").is_file()
                                        for record in exploratory_records),
                "missing_op_outputs": sum(not (development / record["name"] / "op.raw").is_file()
                                          for record in exploratory_records),
                "note": "Initial eight runs requested an unavailable internal-node vector; eight readout retries succeeded. All original evidence is preserved separately.",
            }
        history = output / "run_history/previous_formal_runs.json"
        if history.is_file():
            summary["previous_formal_runs"] = json.loads(history.read_text())
        (output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
        write_report(output, summary, rows)
    print(f"BJT substrate diagnostic: {'PASS' if summary['passed'] else 'FAIL'}")
    print(f"Report: {output / 'report.md'}")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
