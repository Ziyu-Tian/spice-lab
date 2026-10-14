#!/usr/bin/env python3
"""Validate relocated XSPICE libraries using real ngspice calculations.

The original system spinit is also exercised as a labelled expected failure.
Exit status alone is insufficient: ngspice may return zero after init errors.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
LIBRARIES = {
    "spice2poly.cm": "spice2poly",
    "analog.cm": "gain",
    "digital.cm": "d_inverter",
    "xtradev.cm": "cmeter",
    "xtraevt.cm": "real_gain",
    "table.cm": "table2d",
}
DIAGNOSTICS = re.compile(r"(?im)^.*\b(?:error|warning|fatal)\b.*$")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/code_models")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    commands: list[dict] = []
    checks: list[dict] = []

    def run(command: list[str], name: str, *, env: dict | None = None) -> dict:
        try:
            process = subprocess.run(command, cwd=output, env=env, text=True,
                                     capture_output=True, timeout=60, check=False)
            console = process.stdout + process.stderr
            exit_code = process.returncode
        except (OSError, subprocess.TimeoutExpired) as error:
            console = f"ERROR: {type(error).__name__}: {error}\n"
            exit_code = 124 if isinstance(error, subprocess.TimeoutExpired) else 127
        (output / f"{name}_console.log").write_text(console)
        record = {"command": shlex.join(command), "cwd": str(output),
                  "exit_code": exit_code, "console_log": f"{name}_console.log"}
        if env is not None:
            # Only explicit nonsecret model-path overrides; never dump env.
            record["environment_overrides"] = {key: env[key] for key in ("LD_LIBRARY_PATH", "SPICE_SCRIPTS")
                                               if key in env and env[key] != os.environ.get(key)}
        commands.append(record)
        return {**record, "text": console}

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    multiarch_result = run(["dpkg-architecture", "-qDEB_HOST_MULTIARCH"], "multiarch")
    multiarch = multiarch_result["text"].strip()
    prefix = ROOT / ".local/ngspice"
    model_dir = prefix / "usr/lib" / multiarch / "ngspice"
    wrapper = ROOT / ".local/bin/ngspice"
    ngspice = str(wrapper if wrapper.is_file() else Path(shutil.which("ngspice") or "ngspice"))
    version_result = run([ngspice, "--version"], "ngspice_version")
    versions = {"Python": sys.version.split()[0], "ngspice": version_result["text"].strip()}
    for name in ("numpy", "scipy", "matplotlib", "pandas"):
        versions[name] = importlib.metadata.version(name)

    library_env = os.environ.copy()
    library_env["LD_LIBRARY_PATH"] = str(prefix / "usr/lib" / multiarch) + (
        ":" + library_env["LD_LIBRARY_PATH"] if library_env.get("LD_LIBRARY_PATH") else "")
    libraries = []
    for filename, model in LIBRARIES.items():
        path = model_dir / filename
        present = path.is_file()
        ldd_result = run(["ldd", str(path)], filename.replace(".cm", "_ldd"), env=library_env)
        resolved = present and ldd_result["exit_code"] == 0 and "not found" not in ldd_result["text"]
        check(f"library_dependencies:{filename}", resolved, "All dependencies resolve" if resolved else ldd_result["text"])
        libraries.append({"library": filename, "path": str(path), "present": present,
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if present else "",
                          "ldd_resolved": resolved, "registered_model": model})

    circuits = ROOT / "circuits/code_model_validation"

    def simulate(circuit: str, name: str, *, raw: bool = False) -> dict:
        log = output / f"{name}.log"
        log.unlink(missing_ok=True)
        environment = None
        executable = ngspice
        if raw:
            executable = str(prefix / "usr/bin/ngspice")
            environment = library_env.copy()
            environment["SPICE_SCRIPTS"] = str(prefix / "usr/share/ngspice/scripts")
        result = run([executable, "-b", "-o", str(log), str(circuits / circuit)], name, env=environment)
        result["text"] += log.read_text() if log.exists() else ""
        result["diagnostics"] = DIAGNOSTICS.findall(result["text"])
        if raw:
            result["SPICE_SCRIPTS"] = environment["SPICE_SCRIPTS"]
        return result

    # Reproduce the packaged absolute-path bug without changing the RC example.
    original = simulate("model_registry.cir", "original_path_expected_failure", raw=True)
    failed_libraries = sum(f'Library /usr/lib/{multiarch}/ngspice/{name} couldn\'t be loaded!' in original["text"]
                           for name in LIBRARIES)
    check("original_path_expected_failure", failed_libraries == 6,
          f"Expected init failure reproduced for {failed_libraries}/6 libraries; ngspice exit={original['exit_code']}")

    registry = simulate("model_registry.cir", "model_registry")
    check("registry_log_clean", registry["exit_code"] == 0 and not registry["diagnostics"],
          "No errors or warnings" if not registry["diagnostics"] else "\n".join(registry["diagnostics"]))
    for library in libraries:
        registered = bool(re.search(rf"(?m)^{re.escape(library['registered_model'])}\s+:", registry["text"]))
        library["model_registered"] = registered
        check(f"model_registration:{library['library']}", registered, library["registered_model"])
    pd.DataFrame(libraries).to_csv(output / "model_libraries.csv", index=False)

    metrics: dict[str, float | int] = {}
    analog_path = output / "analog_gain.txt"
    analog_path.unlink(missing_ok=True)
    analog = simulate("analog_gain.cir", "analog_gain")
    check("analog_log_clean", analog["exit_code"] == 0 and not analog["diagnostics"],
          "No errors or warnings" if not analog["diagnostics"] else "\n".join(analog["diagnostics"]))
    if analog_path.is_file():
        data = np.loadtxt(analog_path, skiprows=1, ndmin=2)
        expected = 2.5 * data[:, 1] + 0.125
        errors = data[:, 2] - expected
        metrics["analog_samples"] = len(data)
        metrics["analog_max_abs_error_V"] = float(np.max(np.abs(errors)))
        check("analog_gain_numerical", len(data) == 41 and np.all(np.isfinite(data)) and np.max(np.abs(errors)) < 1e-10,
              f"{len(data)} DC points; max absolute error {np.max(np.abs(errors)):.6g} V")
        pd.DataFrame({"input_V": data[:, 1], "output_V": data[:, 2], "expected_V": expected,
                      "error_V": errors}).to_csv(output / "analog_gain.csv", index=False)
        fig, axis = plt.subplots(figsize=(7, 4))
        axis.plot(data[:, 1], data[:, 2], "o", label="ngspice gain Code Model")
        axis.plot(data[:, 1], expected, label="2.5 V_in + 0.125 V")
        axis.set(xlabel="Input (V)", ylabel="Output (V)")
        axis.grid(True, alpha=0.3)
        axis.legend()
        fig.tight_layout()
        fig.savefig(output / "analog_gain.png", dpi=160)
        plt.close(fig)
    else:
        check("analog_gain_numerical", False, "ngspice did not produce current-run output")

    digital_path = output / "digital_inverter.txt"
    digital_path.unlink(missing_ok=True)
    digital = simulate("digital_inverter.cir", "digital_inverter")
    check("digital_log_clean", digital["exit_code"] == 0 and not digital["diagnostics"],
          "No errors or warnings" if not digital["diagnostics"] else "\n".join(digital["diagnostics"]))
    if digital_path.is_file():
        data = np.loadtxt(digital_path, skiprows=1, ndmin=2)
        # ADC thresholds + 10 ns gate delay + 10 ns DAC edges: validate only
        # samples >=100 ns from any input edge, and keep full waveform in CSV.
        edges = data[1:, 0][np.abs(np.diff(data[:, 1])) > 0.01]
        stable = np.min(np.abs(data[:, 0, None] - edges[None, :]), axis=1) > 100e-9
        stable &= data[:, 0] > 100e-9
        expected = np.where(data[:, 1] < 0.8, 3.3, np.where(data[:, 1] > 2, 0, np.nan))
        stable &= np.isfinite(expected)
        errors = data[:, 2] - expected
        max_error = float(np.max(np.abs(errors[stable]))) if np.any(stable) else float("inf")
        metrics["digital_samples"] = len(data)
        metrics["digital_stable_samples"] = int(np.count_nonzero(stable))
        metrics["digital_max_stable_abs_error_V"] = max_error
        both_states = np.any(expected[stable] == 3.3) and np.any(expected[stable] == 0)
        check("digital_inverter_numerical", len(data) > 1000 and np.all(np.isfinite(data)) and both_states
              and np.count_nonzero(stable) > 1000 and max_error < 1e-6,
              f"{len(data)} transient points, {np.count_nonzero(stable)} stable samples; max error {max_error:.6g} V")
        pd.DataFrame({"time_s": data[:, 0], "input_V": data[:, 1], "output_V": data[:, 2],
                      "expected_stable_V": expected, "stable_sample": stable,
                      "error_V": errors}).to_csv(output / "digital_inverter.csv", index=False)
        fig, axis = plt.subplots(figsize=(8, 4))
        axis.plot(data[:, 0] * 1e6, data[:, 1], label="ADC input")
        axis.plot(data[:, 0] * 1e6, data[:, 2], label="Inverter + DAC output")
        axis.set(xlabel="Time (µs)", ylabel="Voltage (V)")
        axis.grid(True, alpha=0.3)
        axis.legend()
        fig.tight_layout()
        fig.savefig(output / "digital_inverter.png", dpi=160)
        plt.close(fig)
    else:
        check("digital_inverter_numerical", False, "ngspice did not produce current-run output")

    passed = all(check["passed"] for check in checks)
    result = {"passed": passed, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "platform": platform.platform(), "versions": versions, "checks": checks, "metrics": metrics,
              "commands": commands, "diagnostics": {"expected_original_failure": original["diagnostics"],
              "registry": registry["diagnostics"], "analog": analog["diagnostics"], "digital": digital["diagnostics"]}}
    (output / "model_report.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    text = ["# ngspice Code Model 加载修复与验证", "", f"最终状态：{'PASS' if passed else 'FAIL'}。", "",
            "## 原因和修复", "",
            "原 RC 报告的六个加载错误来自 rootless 解包后仍使用 Debian spinit 中的 `/usr/lib/.../ngspice/*.cm`。"
            "这些绝对路径属于系统安装布局；实际库位于仓库 `.local/ngspice/usr/lib/.../ngspice/`。",
            "", "安装脚本保持包内 spinit 不变，生成 `.local/ngspice-runtime/spinit`，重定位 Code Model 路径，"
            "并让 wrapper 设置 `SPICE_SCRIPTS` 指向该目录。每次运行 setup 都重新生成配置，"
            "即使依赖已安装也可刷新旧快照中的错误 wrapper。APT 签名和哈希、pip 哈希及 TLS 验证保持启用。",
            "", "官方 [ngspice man page](https://github.com/ngspice/ngspice/blob/master/man/man1/ngspice.1)"
            "明确 `SPICE_SCRIPTS` 为 spinit 搜索目录。`codemodel` 在 44.2 中将路径双引号当作文件名字符，"
            "因此修复使用无空白的裸绝对路径；安装路径包含空白时脚本明确报错。",
            "", "## 真实执行结果", "", "| 检查 | 结果 | 证据 |", "|---|---|---|"]
    for item in checks:
        text.append(f"| {item['name']} | {'PASS' if item['passed'] else 'FAIL'} | {item['detail'].replace(chr(10), '<br>')} |")
    text.extend(["", "六库的真实 `ldd` 输出和 sha256 见日志及 `model_libraries.csv`。每个库至少一个独有模型"
                 "出现在 ngspice `devhelp` 注册表中；这是加载证据，不表示穷尽了该库所有模型的计算功能。",
                 "", "gain Code Model 实际 DC 扫描 -1…+1 V，验证 `Vout = 2.5 Vin + 0.125 V`。"
                 "数字测试实际使用 ADC bridge、d_inverter 和 DAC bridge，验证 0/3.3 V 输入反相输出；"
                 "全瞬态保存，数值断言排除输入边沿 100 ns 内的延迟/过渡样本。",
                 "", "OSDI 被 Debian spinit 默认禁用。本测试不加载、也不声称验证 OSDI 外部紧凑模型；"
                 "标准内建 BJT 与上述 XSPICE Code Model 不依赖 OSDI。", "",
                 "## 警告、失败与重复执行", "",
                 f"原始错误再现：{failed_libraries}/6 库加载失败，ngspice 返回 {original['exit_code']}；"
                 "这是有标签的预期失败，见 `original_path_expected_failure.log`。说明必须检查日志而不能仅看退出码。",
                 "", "修复后的注册表、analog 和 digital 日志中检测到的 error/warning/fatal 数量分别为 "
                 f"{len(registry['diagnostics'])}、{len(analog['diagnostics'])}、{len(digital['diagnostics'])}。"
                 "XSPICE 会显示 `Reducing trtol to 1 for xspice 'A' devices`，属仿真器正常精度调整提示。",
                 "", "开发时双引号路径导致的首次修复失败保存在 `relocation_quoted_path_failure.log`；"
                 "后续去除引号重新执行通过。安装刷新和第二次重复执行日志分别见 `setup_refresh.log`、"
                 "`setup_repeat.log`（历史执行证据，不由本测试程序覆盖）。原 RC 示例文件保持原样。", "",
                 "## 复现命令", "", "```bash", "cd /workspace/spice-lab", "bash scripts/setup_env.sh",
                 "source .local/env.sh", "python scripts/test_ngspice_models.py --output-dir results/code_models", "```", "",
                 "本次 ngspice、ldd 的确切命令、工作目录和退出码由 `model_report.json` 保存。", "",
                 "## 版本", "", "```text", versions["ngspice"], "```", ""])
    text.extend(f"- {name}: {value}" for name, value in versions.items() if name != "ngspice")
    (output / "model_report.md").write_text("\n".join(text) + "\n")
    print(json.dumps({"passed": passed, "checks": len(checks), "metrics": metrics,
                      "report": str(output / "model_report.md")}, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
