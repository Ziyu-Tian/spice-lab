#!/usr/bin/env python3
"""Run ngspice and validate its RC transient against the analytical solution.

Run from any directory:
    .venv/bin/python scripts/test_rc.py --output-dir results/rc

No display server or external services are required. The circuit has a 1 V DC
source and an initially discharged capacitor, using UIC to represent a step at
t=0 without a finite source rise time. CSV rows are actual ngspice samples.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import traceback
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
CIRCUIT = ROOT / "circuits" / "rc_transient.cir"
RESISTANCE_OHMS = 1_000.0
CAPACITANCE_FARADS = 1e-6
FINAL_VOLTAGE_V = 1.0
TAU_SECONDS = RESISTANCE_OHMS * CAPACITANCE_FARADS
TAU_RELATIVE_TOLERANCE = 0.01
WAVEFORM_ABSOLUTE_TOLERANCE_V = 0.001


def write_report(output_dir: Path, result: dict) -> None:
    """Write machine-readable results and a report on success or failure."""
    (output_dir / "rc_report.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# RC 瞬态仿真测试报告",
        "",
        f"结果：**{'通过' if result['passed'] else '失败'}**",
        "",
        f"- 测试时间（Asia/Shanghai）：{datetime.fromisoformat(result['timestamp_utc']).astimezone(ZoneInfo('Asia/Shanghai')).isoformat()}",
        f"- Python：{result['python_version']}",
        f"- 系统：{result['platform']}",
        f"- 电路：`{CIRCUIT.name}`，R = 1 kΩ，C = 1 µF，输入 = 1 V。",
        "- 初始条件：电容电压为 0 V；使用 UIC 从 t = 0 开始施加直流电源。",
        "- 理论：τ = R × C = 1 ms；V(t) = 1 − exp(−t / τ)。",
        "",
    ]
    if result.get("ngspice_version"):
        lines += [f"ngspice：`{result['ngspice_version']}`", ""]
    if result.get("dependency_versions"):
        lines += [
            "依赖版本：" + ", ".join(
                f"{name} {version}"
                for name, version in result["dependency_versions"].items()
            ),
            "",
        ]
    if result.get("command"):
        lines += ["运行命令：", "", "```sh", result["command"], "```", ""]
    if result.get("measurements"):
        measured = result["measurements"]
        lines += [
            "| 项目 | 测量值 | 验收标准 |",
            "| --- | ---: | --- |",
            f"| 理论时间常数 | {TAU_SECONDS * 1e3:.6f} ms | R × C |",
            f"| 非线性拟合时间常数 | {measured['fitted_tau_s'] * 1e3:.9f} ms | 相对误差 ≤ 1% |",
            f"| 拟合相对误差 | {measured['fitted_tau_relative_error'] * 100:.6f}% | ≤ 1% |",
            f"| 63.2121% 电压交点 | {measured['threshold_tau_s'] * 1e3:.9f} ms | 相对误差 ≤ 1% |",
            f"| 交点相对误差 | {measured['threshold_tau_relative_error'] * 100:.6f}% | ≤ 1% |",
            f"| 波形最大绝对误差 | {measured['maximum_absolute_error_v']:.9g} V | ≤ 0.001 V |",
            f"| 波形均方根误差 | {measured['rms_error_v']:.9g} V | 记录值 |",
            f"| 样本数 | {measured['sample_count']} | ≥ 1000 |",
            f"| 最后采样时间 | {measured['last_time_s'] * 1e3:.6f} ms | ≥ 7.9 ms |",
            "",
            "拟合使用 SciPy 在 0–6τ 的真实 ngspice 样本上求解单参数 τ；最终电压固定为 1 V。",
            "63.2121% 交点通过相邻样本线性插值独立计算。波形误差按全部原始采样点计算，未补点或平滑。",
            "",
        ]
    if result.get("checks"):
        lines += ["检查：", ""]
        lines += [
            f"- {'通过' if passed else '失败'}：{name}"
            for name, passed in result["checks"].items()
        ]
        lines.append("")
    if result.get("error"):
        lines += ["失败原因：", "", "```text", result["error"], "```", ""]
    lines += [
        "输出文件（所有路径相对于本报告目录）：",
        "",
        "- `rc_transient.csv`：时间、电容电压、理论电压与误差。",
        "- `rc_waveform.png`：仿真/理论波形与误差图。",
        "- `rc_transient_ngspice.txt`：ngspice 原始数值输出。",
        "- `ngspice.log`：仿真日志。",
        "- `rc_report.json`：结构化测量值与检查结果。",
        "",
        "失败时，尚未生成的输出文件可能不存在；进程以非零状态退出。",
        "",
    ]
    (output_dir / "rc_report.md").write_text("\n".join(lines), encoding="utf-8")


def run_test(args: argparse.Namespace, output_dir: Path, result: dict) -> None:
    # Imports are inside the guarded test so missing dependencies also get a report.
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    import scipy
    from scipy.optimize import curve_fit

    result["dependency_versions"] = {
        "NumPy": np.__version__,
        "SciPy": scipy.__version__,
        "Matplotlib": matplotlib.__version__,
        "Pandas": pd.__version__,
    }
    executable = shutil.which(args.ngspice)
    if executable is None:
        raise RuntimeError(f"ngspice executable not found: {args.ngspice}")
    executable = str(Path(executable).resolve())
    version = subprocess.run(
        [executable, "--version"],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    result["ngspice_version"] = next(
        (line.strip().strip("*").strip() for line in version.stdout.splitlines()
         if "ngspice-" in line.lower()),
        version.stdout.strip().splitlines()[0] if version.stdout.strip() else "unknown",
    )
    if not CIRCUIT.is_file():
        raise RuntimeError(f"Circuit file not found: {CIRCUIT}")

    command = [executable, "-b", "-o", "ngspice.log", str(CIRCUIT)]
    result["command"] = shlex.join(command)
    process = subprocess.run(
        command,
        cwd=output_dir,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    (output_dir / "ngspice_console.log").write_text(
        process.stdout + process.stderr, encoding="utf-8"
    )
    if process.returncode != 0:
        raise RuntimeError(f"ngspice exited with {process.returncode}; see ngspice.log")
    raw_path = output_dir / "rc_transient_ngspice.txt"
    if not raw_path.is_file():
        raise RuntimeError("ngspice did not produce data; see ngspice.log")
    raw = pd.read_csv(raw_path, sep=r"\s+")
    if raw.shape[1] != 2 or list(raw.columns) != ["time", "v(out)"]:
        raise RuntimeError(f"Unexpected ngspice data columns: {list(raw.columns)}")
    time_s = raw["time"].to_numpy(dtype=float)
    voltage_v = raw["v(out)"].to_numpy(dtype=float)
    if len(time_s) < 2 or not (np.isfinite(time_s).all() and np.isfinite(voltage_v).all()):
        raise RuntimeError("ngspice produced insufficient or non-finite data")
    if not np.all(np.diff(time_s) > 0):
        raise RuntimeError("ngspice sample times are not strictly increasing")

    def theoretical(time: np.ndarray, tau: float) -> np.ndarray:
        return FINAL_VOLTAGE_V * (-np.expm1(-time / tau))

    theoretical_v = theoretical(time_s, TAU_SECONDS)
    signed_error_v = voltage_v - theoretical_v
    pd.DataFrame({
        "time_s": time_s,
        "voltage_v": voltage_v,
        "theoretical_voltage_v": theoretical_v,
        "error_v": signed_error_v,
    }).to_csv(output_dir / "rc_transient.csv", index=False, float_format="%.15g")

    fit_mask = (time_s >= 0) & (time_s <= 6 * TAU_SECONDS)
    if fit_mask.sum() < 10:
        raise RuntimeError("Too few samples in the 0–6 tau fitting interval")
    fitted, _ = curve_fit(
        theoretical,
        time_s[fit_mask],
        voltage_v[fit_mask],
        p0=[TAU_SECONDS],
        bounds=([TAU_SECONDS / 10], [TAU_SECONDS * 10]),
        xtol=1e-12,
        ftol=1e-12,
        gtol=1e-12,
    )
    fitted_tau_s = float(fitted[0])
    threshold_v = float(FINAL_VOLTAGE_V * (-np.expm1(-1.0)))
    # Locate a real rising crossing and interpolate just its two surrounding samples.
    crossing = np.flatnonzero(
        (voltage_v[:-1] <= threshold_v) & (voltage_v[1:] >= threshold_v)
    )
    if len(crossing) != 1:
        raise RuntimeError(f"Expected one 63.2121% rising crossing, found {len(crossing)}")
    index = int(crossing[0])
    threshold_tau_s = float(np.interp(
        threshold_v,
        voltage_v[index:index + 2],
        time_s[index:index + 2],
    ))
    maximum_error_v = float(np.max(np.abs(signed_error_v)))
    result["measurements"] = {
        "resistance_ohms": RESISTANCE_OHMS,
        "capacitance_farads": CAPACITANCE_FARADS,
        "theoretical_tau_s": TAU_SECONDS,
        "fitted_tau_s": fitted_tau_s,
        "fitted_tau_relative_error": abs(fitted_tau_s / TAU_SECONDS - 1),
        "threshold_voltage_v": threshold_v,
        "threshold_tau_s": threshold_tau_s,
        "threshold_tau_relative_error": abs(threshold_tau_s / TAU_SECONDS - 1),
        "maximum_absolute_error_v": maximum_error_v,
        "rms_error_v": float(np.sqrt(np.mean(np.square(signed_error_v)))),
        "sample_count": int(len(time_s)),
        "first_time_s": float(time_s[0]),
        "last_time_s": float(time_s[-1]),
    }
    result["checks"] = {
        "sample count >= 1000": bool(len(time_s) >= 1000),
        "simulation reaches >= 7.9 ms": bool(time_s[-1] >= 7.9e-3),
        "initial capacitor voltage near 0 V": bool(
            time_s[0] <= 1e-6 and abs(voltage_v[0]) <= 0.001
        ),
        "capacitor voltage rises monotonically": bool(np.all(np.diff(voltage_v) >= -1e-9)),
        "fitted tau relative error <= 1%": bool(
            result["measurements"]["fitted_tau_relative_error"] <= TAU_RELATIVE_TOLERANCE
        ),
        "63.2121% crossing relative error <= 1%": bool(
            result["measurements"]["threshold_tau_relative_error"] <= TAU_RELATIVE_TOLERANCE
        ),
        "waveform maximum absolute error <= 0.001 V": bool(
            maximum_error_v <= WAVEFORM_ABSOLUTE_TOLERANCE_V
        ),
    }

    figure, (waveform_axis, error_axis) = plt.subplots(
        2, 1, figsize=(9, 6), sharex=True, gridspec_kw={"height_ratios": [3, 1]}
    )
    waveform_axis.plot(time_s * 1e3, voltage_v, label="ngspice", linewidth=1.6)
    waveform_axis.plot(time_s * 1e3, theoretical_v, "--", label="Theory", linewidth=1.2)
    waveform_axis.axhline(threshold_v, color="gray", linestyle=":", label="63.2121%")
    waveform_axis.axvline(TAU_SECONDS * 1e3, color="gray", linestyle=":")
    waveform_axis.set_ylabel("Capacitor voltage (V)")
    waveform_axis.set_title("RC step response: R = 1 kohm, C = 1 uF, tau = 1 ms")
    waveform_axis.legend(loc="lower right")
    waveform_axis.grid(True, alpha=0.3)
    error_axis.plot(time_s * 1e3, signed_error_v * 1e6, color="tab:red")
    error_axis.set_ylabel("Error (uV)")
    error_axis.set_xlabel("Time (ms)")
    error_axis.grid(True, alpha=0.3)
    figure.tight_layout()
    figure.savefig(output_dir / "rc_waveform.png", dpi=180)
    plt.close(figure)
    result["passed"] = all(result["checks"].values())
    if not result["passed"]:
        failed_checks = [name for name, passed in result["checks"].items() if not passed]
        result["error"] = "Validation failed: " + "; ".join(failed_checks)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "results" / "rc",
        help="Directory for CSV, PNG, reports and ngspice logs (default: results/rc)",
    )
    parser.add_argument("--ngspice", default="ngspice", help="ngspice executable name or path")
    args = parser.parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    result: dict = {
        "passed": False,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
    }
    try:
        # Delete only our generated files before checking dependencies, so a failed
        # rerun cannot leave old CSV/PNG data that appears to belong to this run.
        generated_names = (
            "rc_transient_ngspice.txt", "ngspice.log", "ngspice_console.log",
            "rc_transient.csv", "rc_waveform.png", "test_error.log",
        )
        for name in generated_names:
            (output_dir / name).unlink(missing_ok=True)
        run_test(args, output_dir, result)
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        (output_dir / "test_error.log").write_text(traceback.format_exc(), encoding="utf-8")
    write_report(output_dir, result)
    print(f"RC transient validation: {'PASS' if result['passed'] else 'FAIL'}")
    if result.get("measurements"):
        measured = result["measurements"]
        print(f"Theory tau: {TAU_SECONDS * 1e3:.6f} ms")
        print(f"Fitted tau: {measured['fitted_tau_s'] * 1e3:.9f} ms")
        print(f"63.2121% crossing: {measured['threshold_tau_s'] * 1e3:.9f} ms")
        print(f"Maximum waveform error: {measured['maximum_absolute_error_v']:.9g} V")
    if result.get("error"):
        print(result["error"], file=sys.stderr)
    print(f"Report: {output_dir / 'rc_report.md'}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
