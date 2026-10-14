#!/usr/bin/env python3
"""Execute genuine ngspice OP/AC scans; every result has archived raw evidence.

Use an existing checkout (cloud tasks are isolated; no worktree is required):
    source .local/env.sh
    python scripts/simulate_bjt_resistance.py --output-dir results/bjt

The model is educational, has no avalanche breakdown, and is not DS3930.
CSV values are ngspice observations or calculations explicitly derived from them.
"""
from __future__ import annotations

import argparse
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
import tarfile
import time
import traceback

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
from scipy.optimize import brentq

ROOT = Path(__file__).resolve().parents[1]
CIRCUITS = ROOT / "circuits/bjt_resistance"
TARGETS = [3399.0, 2641.0, 1858.0]
TEMPERATURES = [0.0, 25.0, 50.0]
CURRENTS = [-100e-6, -50e-6, -10e-6, 0.0, 10e-6, 50e-6, 100e-6]
FIXED_BIASES = [0.45, 0.50, 0.55, 0.60, 0.65, 0.70]
FREQUENCIES = [1, 1000, 100000]
AC_CURRENT_A = 1e-6
VOLTAGE_WINDOW_V = 5.0
GMIN_S = 1e-12


def read_raw(path: Path) -> dict[str, np.ndarray]:
    """Parse ngspice ASCII rawfile, including the automatic scale column."""
    content = path.read_text()
    header, values = content.split("Values:\n", 1)
    count = int(re.search(r"No\. Variables:\s*(\d+)", header).group(1))
    points = int(re.search(r"No\. Points:\s*(\d+)", header).group(1))
    names = [line.split()[1] for line in header.split("Variables:\n", 1)[1].splitlines() if line.strip()]
    if len(names) != count:
        raise ValueError(f"Invalid variable list in {path}")
    complex_values = "Flags: complex" in header
    lines = [line.strip() for line in values.splitlines() if line.strip()]
    if len(lines) != count * points:
        raise ValueError(f"Invalid value count in {path}")
    rows = []
    for point in range(points):
        row = []
        for variable in range(count):
            value = lines[point * count + variable]
            if variable == 0:
                value = value.split(maxsplit=1)[1]
            if complex_values:
                real, imaginary = value.split(",")
                row.append(complex(float(real), float(imaginary)))
            else:
                row.append(float(value))
        rows.append(row)
    array = np.asarray(rows)
    if not np.isfinite(array).all():
        raise ValueError(f"Nonfinite data in {path}")
    return {name: array[:, index] for index, name in enumerate(names)}


def scalar(raw: dict, name: str) -> float:
    return float(raw[name][0])


class Runner:
    def __init__(self, executable: str, output: Path):
        self.executable = executable
        self.output = output
        self.work = output / "raw_evidence"
        self.work.mkdir()
        self.manifest_path = output / "run_manifest.jsonl"
        self.records = []
        self.model = (CIRCUITS / "generic_npn.lib").read_text()

    def run(self, template: str, run_id: str, phase: str, **parameters) -> dict:
        directory = self.work / run_id
        directory.mkdir()
        parameters.update(run_id=run_id, model=self.model)
        parameters.setdefault("gmin_s", GMIN_S)
        deck = (CIRCUITS / template).read_text().format(**parameters)
        (directory / "circuit.cir").write_text(deck)
        command = [self.executable, "-b", "-o", "ngspice.log", "circuit.cir"]
        record = {"run_id": run_id, "phase": phase, "command": shlex.join(command),
                  "cwd": str(directory), "parameters": {key: value for key, value in parameters.items() if key != "model"},
                  "returncode": None, "status": "failed", "warnings": [], "errors": []}
        start = time.monotonic()
        try:
            process = subprocess.run(command, cwd=directory, capture_output=True,
                                     text=True, timeout=30, check=False)
            record["returncode"] = process.returncode
            console = process.stdout + process.stderr
            (directory / "console.log").write_text(console)
            log = (directory / "ngspice.log").read_text() if (directory / "ngspice.log").exists() else ""
            all_log = log + "\n" + console
            record["warnings"] = [line.strip() for line in all_log.splitlines()
                if re.search(r"warning|singular|gmin stepping|source stepping|iteration limit", line, re.I)
                and "comments and warnings go to log-file" not in line.lower()]
            record["errors"] = [line.strip() for line in all_log.splitlines()
                if re.search(r"(^|\s)error|couldn't be loaded|cannot open|doanalyses:|no convergence|failed", line, re.I)]
            if process.returncode != 0 or record["errors"]:
                raise RuntimeError("ngspice execution/log diagnostics failed")
            expected = ["op.raw"] if phase == "calibration" else ["op.raw", "plus.raw", "minus.raw"] + [f"ac_{freq}.raw" for freq in FREQUENCIES]
            raws = {name: read_raw(directory / name) for name in expected}
            record["status"] = "passed"
            return raws
        except Exception as error:
            record["exception"] = f"{type(error).__name__}: {error}"
            raise
        finally:
            record["elapsed_seconds"] = time.monotonic() - start
            record["files_sha256"] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                      for path in sorted(directory.iterdir()) if path.is_file()}
            self.records.append(record)
            with self.manifest_path.open("a") as manifest:
                manifest.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")

    def archive(self):
        with tarfile.open(self.output / "raw_evidence.tar.gz", "w:gz") as archive:
            archive.add(self.work, arcname="raw_evidence")
        shutil.rmtree(self.work)


def calibrate(runner: Runner) -> tuple[list[dict], list[dict]]:
    calibrations, biases = [], []
    for target in TARGETS:
        count = 0
        evaluations = []
        def residual(bias):
            nonlocal count
            run_id = f"calibration_r{target:.0f}_{count:02d}"
            count += 1
            raw = runner.run("bjt_voltage_calibration.cir.in", run_id, "calibration",
                             voltage_v=target * 50e-6, bias_v=float(bias))["op.raw"]
            current = scalar(raw, "i(vcollector)")
            evaluations.append((float(bias), current))
            return current - 50e-6
        bias = float(brentq(residual, 0.35, 0.95, xtol=1e-12, rtol=1e-12))
        # Run one last explicit raw observation at the returned bias.
        final_residual = residual(bias)
        calibrations.append({"target_ohm": target, "temperature_c": 25,
            "nominal_current_a": 50e-6, "clamped_port_voltage_v": target * 50e-6,
            "calibrated_bias_v": bias, "measured_port_current_a": evaluations[-1][1],
            "residual_a": final_residual, "ngspice_evaluations": count})
        biases.append({"bias_kind": "calibrated", "bias_id": f"cal_r{target:.0f}",
                       "bias_v": bias, "target_ohm": target})
    return calibrations, biases


def analyze_point(raws: dict, metadata: dict) -> tuple[dict, list[dict]]:
    op = raws["op.raw"]
    bjt = metadata["circuit"] == "bjt"
    current = scalar(op, "i(vcollector)" if bjt else "@rreference[i]")
    voltage = scalar(op, "v(port)")
    source_current = metadata["sample_current_a"]
    delta = max(abs(source_current) * 0.001, 1e-10) if source_current == 0 else abs(source_current) * 0.001
    fd = (scalar(raws["plus.raw"], "v(port)") - scalar(raws["minus.raw"], "v(port)")) / (2 * delta)
    row = {**metadata, "port_voltage_v": voltage, "port_current_a": current,
           "apparent_resistance_ohm": voltage / current if source_current != 0 else np.nan,
           "incremental_fd_ohm": fd, "delta_current_a": delta,
           "within_voltage_window": abs(voltage) <= VOLTAGE_WINDOW_V,
           "port_power_w": voltage * current,
           "port_kcl_residual_a": current - source_current,
           "status": "passed"}
    if bjt:
        ib = scalar(op, "@q1[ib]")
        ie = scalar(op, "@q1[ie]")
        ic = scalar(op, "@q1[ic]")
        vb = scalar(op, "v(base)")
        row.update(base_voltage_v=vb, vbc_external_v=vb - voltage,
                   base_current_a=-scalar(op, "i(vbias)"), emitter_current_a=-scalar(op, "i(vemitter)"),
                   model_ie_a=ie, model_ib_a=ib,
                   bias_delivered_current_a=-scalar(op, "i(vbias)"),
                   bias_power_delivered_w=-metadata["bias_v"] * scalar(op, "i(vbias)"),
                   model_ic_a=ic, model_gm_s=scalar(op, "@q1[gm]"),
                   model_gpi_s=scalar(op, "@q1[gpi]"), model_go_s=scalar(op, "@q1[go]"),
                   device_kcl_residual_a=current - scalar(op, "i(vbias)") - scalar(op, "i(vemitter)"),
                   model_kcl_residual_a=ic + ib + ie,
                   model_kcl_gmin_adjusted_residual_a=ic + ib + ie + metadata["gmin_s"] * voltage,
                   collector_model_difference_a=current - ic)
    ac_rows = []
    for frequency in FREQUENCIES:
        raw = raws[f"ac_{frequency}.raw"]
        z = raw["v(port)"][0] / AC_CURRENT_A
        observed_freq = raw["frequency"][0].real
        if observed_freq != frequency:
            raise ValueError(f"Unexpected AC frequency {observed_freq}")
        ac_rows.append({**metadata, "frequency_hz": frequency,
                       "z_real_ohm": float(z.real), "z_imag_ohm": float(z.imag),
                       "z_magnitude_ohm": float(abs(z)), "z_phase_deg": float(np.angle(z, deg=True)),
                       "fd_relative_difference": float(abs(z.real - fd) / max(abs(fd), 1e-30)),
                       "within_voltage_window": row["within_voltage_window"]})
    return row, ac_rows


def execute_scan(runner: Runner, biases: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    points, impedances = [], []
    cases = [{"circuit": "bjt", **bias} for bias in biases]
    cases += [{"circuit": "reference", "bias_kind": "reference", "bias_id": f"ref_r{target:.0f}",
               "bias_v": np.nan, "target_ohm": target} for target in TARGETS]
    for case in cases:
        for temperature in TEMPERATURES:
            for current in CURRENTS:
                signed_id = f"{'p' if current >= 0 else 'm'}{abs(current) * 1e6:.0f}u"
                run_id = f"{case['bias_id']}_t{temperature:.0f}_{signed_id}"
                metadata = {**case, "run_id": run_id, "temperature_c": temperature,
                            "sample_current_a": current, "gmin_s": GMIN_S}
                delta = abs(current) * 0.001 if current != 0 else 1e-10
                parameters = dict(current_a=current, plus_current_a=current + delta,
                                  minus_current_a=current - delta, temperature_c=temperature)
                template = "bjt_current_probe.cir.in" if case["circuit"] == "bjt" else "resistor_reference.cir.in"
                if case["circuit"] == "bjt":
                    parameters["bias_v"] = case["bias_v"]
                else:
                    parameters["target_ohm"] = case["target_ohm"]
                try:
                    raws = runner.run(template, run_id, "scan", **parameters)
                    row, ac_rows = analyze_point(raws, metadata)
                    points.append(row)
                    impedances.extend(ac_rows)
                except Exception as error:
                    points.append({**metadata, "status": "failed", "failure": str(error)})
    return pd.DataFrame(points), pd.DataFrame(impedances)


def make_comparisons(points: pd.DataFrame, impedance: pd.DataFrame) -> pd.DataFrame:
    rows = []
    low = impedance[impedance.frequency_hz == 1].set_index("run_id")
    for _, point in points[(points.sample_current_a != 0) & (points.status == "passed")].iterrows():
        targets = TARGETS if point.bias_kind == "fixed" else [point.target_ohm]
        for target in targets:
            row = point.to_dict()
            row["comparison_target_ohm"] = target
            row["static_error_percent"] = 100 * (point.apparent_resistance_ohm / target - 1)
            row["incremental_error_percent"] = 100 * (point.incremental_fd_ohm / target - 1)
            row["low_frequency_z_real_ohm"] = float(low.loc[point.run_id, "z_real_ohm"])
            row["low_frequency_error_percent"] = 100 * (row["low_frequency_z_real_ohm"] / target - 1)
            rows.append(row)
    return pd.DataFrame(rows)


def gmin_sensitivity(runner: Runner, points: pd.DataFrame) -> pd.DataFrame:
    bjt = points[(points.circuit == "bjt") & (points.status == "passed")]
    extreme = bjt.loc[bjt.port_voltage_v.abs().idxmax()]
    nominal = bjt[(bjt.bias_id == "cal_r2641") & (bjt.temperature_c == 25) & (bjt.sample_current_a == 50e-6)].iloc[0]
    rows = []
    for point in (extreme, nominal):
        baseline = point.to_dict()
        baseline["source_run_id"] = point.run_id
        baseline["comparison"] = "extreme_out_of_scope" if point.run_id == extreme.run_id else "calibrated_nominal"
        baseline["voltage_ratio_to_baseline"] = 1.0
        rows.append(baseline)
        delta = abs(point.sample_current_a) * 0.001
        run_id = f"gmin14_{point.run_id}"
        metadata = {key: point[key] for key in ("circuit", "bias_kind", "bias_id", "target_ohm", "bias_v", "temperature_c", "sample_current_a")}
        metadata.update(run_id=run_id, gmin_s=1e-14)
        try:
            raws = runner.run("bjt_current_probe.cir.in", run_id, "gmin_sensitivity", current_a=point.sample_current_a,
                             plus_current_a=point.sample_current_a + delta, minus_current_a=point.sample_current_a - delta,
                             bias_v=point.bias_v, temperature_c=point.temperature_c, gmin_s=1e-14)
            row, _ = analyze_point(raws, metadata)
            row.update(source_run_id=point.run_id, comparison=baseline["comparison"],
                       voltage_ratio_to_baseline=row["port_voltage_v"] / point.port_voltage_v)
            rows.append(row)
        except Exception as error:
            rows.append({**metadata, "source_run_id": point.run_id, "comparison": baseline["comparison"], "status": "failed", "failure": str(error)})
    return pd.DataFrame(rows)


def plot_results(output: Path, points: pd.DataFrame, comparisons: pd.DataFrame, impedance: pd.DataFrame):
    bjt = points[(points.circuit == "bjt") & (points.status == "passed")]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharey=True)
    for ax, temperature in zip(axes, TEMPERATURES):
        for bias_id, group in bjt[bjt.temperature_c == temperature].groupby("bias_id", sort=False):
            group = group.sort_values("sample_current_a")
            label = f"{group.bias_v.iloc[0]:.6f} V ({bias_id})"
            ax.plot(group.sample_current_a * 1e6, group.port_voltage_v, "o-", ms=3, label=label)
        for target in TARGETS:
            ax.plot(np.array(CURRENTS) * 1e6, np.array(CURRENTS) * target, "k--", alpha=0.25)
        ax.axhline(5, color="grey", ls=":", lw=0.7)
        ax.axhline(-5, color="grey", ls=":", lw=0.7)
        ax.set_yscale("symlog", linthresh=0.5)
        ax.set_title(f"{temperature:g} C")
        ax.set_xlabel("Signed port current (uA)")
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("Port voltage (V), symlog; every marker is an OP")
    axes[-1].legend(fontsize=6, bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.suptitle("Generic NPN current-driven operating points; dashed lines = ideal resistors")
    fig.tight_layout()
    fig.savefig(output / "bjt_operating_points.png", dpi=170)
    plt.close(fig)

    cal = comparisons[comparisons.bias_kind == "calibrated"]
    fig, axes = plt.subplots(2, 3, figsize=(14, 8), sharex=True)
    for column, target in enumerate(TARGETS):
        data = cal[cal.comparison_target_ohm == target]
        for temperature in TEMPERATURES:
            group = data[data.temperature_c == temperature].sort_values("sample_current_a")
            axes[0, column].plot(group.sample_current_a * 1e6, group.static_error_percent, "o-", label=f"{temperature:g} C")
            axes[1, column].plot(group.sample_current_a * 1e6, group.incremental_error_percent, "o-")
        for row in range(2):
            axes[row, column].axhline(0, color="black", lw=0.5)
            axes[row, column].axhspan(-1, 1, alpha=0.15, color="green")
            axes[row, column].set_yscale("symlog", linthresh=1)
            axes[row, column].grid(alpha=0.25)
        axes[0, column].set_title(f"Target {target:g} ohm, frozen nominal bias")
        axes[1, column].set_xlabel("Signed port current (uA)")
    axes[0, 0].set_ylabel("Static V/I error (%)")
    axes[1, 0].set_ylabel("Incremental dV/dI error (%)")
    axes[0, -1].legend()
    fig.suptitle("Calibration only at +50 uA, 25 C; shaded +/-1% is experiment criterion")
    fig.tight_layout()
    fig.savefig(output / "bjt_resistance_errors.png", dpi=170)
    plt.close(fig)

    nominal = points[(points.bias_kind == "calibrated") & (points.temperature_c == 25) & (points.sample_current_a == 50e-6)]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for _, point in nominal.iterrows():
        group = impedance[impedance.run_id == point.run_id].sort_values("frequency_hz")
        axes[0].semilogx(group.frequency_hz, group.z_real_ohm, "o-", label=f"target {point.target_ohm:g} ohm")
        axes[1].semilogx(group.frequency_hz, group.z_imag_ohm, "o-")
    axes[0].set_ylabel("Re(Z) (ohm)")
    axes[1].set_ylabel("Im(Z) (ohm)")
    for ax in axes:
        ax.set_xlabel("AC frequency (Hz), linearized at OP")
        ax.grid(alpha=0.25)
    axes[0].legend()
    fig.tight_layout()
    fig.savefig(output / "bjt_incremental_impedance.png", dpi=170)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/bjt")
    parser.add_argument("--ngspice", default="ngspice")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if (output / "run_manifest.jsonl").exists() or (output / "raw_evidence").exists():
        parser.error("choose a fresh output directory; existing execution evidence will not be overwritten")
    executable = shutil.which(args.ngspice)
    if not executable:
        parser.error(f"ngspice executable not found: {args.ngspice}")
    executable = str(Path(executable).absolute())  # retain wrapper; do not resolve through it
    version = subprocess.run([executable, "--version"], capture_output=True, text=True, check=True)
    (output / "ngspice_version.txt").write_text(version.stdout + version.stderr)
    summary = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "passed": False,
        "command": shlex.join([sys.executable, str(Path(__file__).resolve()), "--output-dir", str(output), "--ngspice", args.ngspice]),
        "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in [Path(__file__).resolve()] + sorted(CIRCUITS.glob("*.cir.in")) + [CIRCUITS / "generic_npn.lib"]},
        "versions": {"python": platform.python_version(), "platform": platform.platform(),
                     "numpy": np.__version__, "scipy": scipy.__version__, "matplotlib": matplotlib.__version__, "pandas": pd.__version__,
                     "ngspice": next((line.strip("* ") for line in version.stdout.splitlines() if "ngspice-" in line), "unknown")},
        "parameters": {"target_ohm": TARGETS, "temperature_c": TEMPERATURES, "sample_current_a": CURRENTS,
                       "fixed_bias_v": FIXED_BIASES, "ac_frequency_hz": FREQUENCIES, "ac_current_a": AC_CURRENT_A,
                       "voltage_window_v": VOLTAGE_WINDOW_V, "gmin_s": GMIN_S,
                       "finite_difference_fraction": 0.001, "zero_current_delta_a": 1e-10}}
    runner = Runner(executable, output)
    try:
        calibrations, calibrated = calibrate(runner)
        pd.DataFrame(calibrations).to_csv(output / "calibration.csv", index=False, float_format="%.16g")
        fixed = [{"bias_kind": "fixed", "bias_id": f"fixed_{bias * 100:.0f}", "bias_v": bias, "target_ohm": np.nan} for bias in FIXED_BIASES]
        points, impedance = execute_scan(runner, fixed + calibrated)
        points.to_csv(output / "operating_points.csv", index=False, float_format="%.16g")
        impedance.to_csv(output / "impedance.csv", index=False, float_format="%.16g")
        points[points.sample_current_a == 0].to_csv(output / "offset.csv", index=False, float_format="%.16g")
        comparisons = make_comparisons(points, impedance)
        comparisons.to_csv(output / "resistance_comparisons.csv", index=False, float_format="%.16g")
        sensitivity = gmin_sensitivity(runner, points)
        sensitivity.to_csv(output / "gmin_sensitivity.csv", index=False, float_format="%.16g")
        plot_results(output, points, comparisons, impedance)
        reference = comparisons[comparisons.circuit == "reference"]
        reference_ac = impedance[impedance.circuit == "reference"]
        valid_ac = impedance[(impedance.frequency_hz == 1) & (impedance.within_voltage_window == True)]
        successful = points[points.status == "passed"]
        nominal = comparisons[(comparisons.bias_kind == "calibrated") & (comparisons.temperature_c == 25) & (comparisons.sample_current_a == 50e-6)]
        checks = {"all_scan_conditions_computed": len(successful) == 252,
                  "all_ac_observations_computed": len(impedance) == 756,
                  "reference_static_error_below_1e-6_percent": bool(reference.static_error_percent.abs().max() < 1e-6),
                  "reference_ac_relative_error_below_1e-8": bool((reference_ac.z_real_ohm / reference_ac.target_ohm - 1).abs().max() < 1e-8),
                  "nominal_calibration_error_below_1e-4_percent": bool(len(nominal) == 3 and nominal.static_error_percent.abs().max() < 1e-4),
                  "port_kcl_residual_below_1e-12_a": bool(successful.port_kcl_residual_a.abs().max() < 1e-12),
                  "in_window_device_kcl_residual_below_1e-12_a": bool(successful[successful.within_voltage_window].device_kcl_residual_a.dropna().abs().max() < 1e-12),
                  "model_kcl_gmin_adjusted_residual_below_1e-12_a": bool(successful.model_kcl_gmin_adjusted_residual_a.dropna().abs().max() < 1e-12),
                  "in_window_low_frequency_ac_matches_fd_within_1_percent": bool(valid_ac.fd_relative_difference.max() < 0.01),
                  "no_ngspice_execution_errors": all(record["status"] == "passed" for record in runner.records)}
        summary.update(checks=checks, passed=all(checks.values()), calibrations=calibrations,
            counts={"scan_conditions": len(points), "successful_scan_conditions": len(successful),
                    "bjt_conditions": int((points.circuit == "bjt").sum()), "reference_conditions": int((points.circuit == "reference").sum()),
                    "ac_observations": len(impedance), "comparison_rows": len(comparisons), "zero_current_points": int((points.sample_current_a == 0).sum()),
                    "out_of_window_bjt_points": int(((successful.circuit == "bjt") & (~successful.within_voltage_window)).sum()),
                    "ngspice_processes": len(runner.records), "warning_runs": sum(bool(record["warnings"]) for record in runner.records),
                    "failed_runs": sum(record["status"] != "passed" for record in runner.records)},
            measurements={"max_reference_static_error_percent": float(reference.static_error_percent.abs().max()),
                          "max_nominal_static_error_percent": float(nominal.static_error_percent.abs().max()),
                          "max_in_window_lowfreq_fd_relative_difference": float(valid_ac.fd_relative_difference.max()),
                          "max_port_kcl_residual_a": float(successful.port_kcl_residual_a.abs().max()),
                          "max_device_kcl_residual_a": float(successful.device_kcl_residual_a.dropna().abs().max()),
                          "max_in_window_device_kcl_residual_a": float(successful[successful.within_voltage_window].device_kcl_residual_a.dropna().abs().max()),
                          "max_model_kcl_gmin_adjusted_residual_a": float(successful.model_kcl_gmin_adjusted_residual_a.dropna().abs().max())},
            nominal_points=nominal[["comparison_target_ohm", "bias_v", "port_voltage_v", "port_current_a", "apparent_resistance_ohm", "incremental_fd_ohm", "static_error_percent", "incremental_error_percent"]].to_dict("records"))
    except Exception as error:
        summary["error"] = f"{type(error).__name__}: {error}"
        (output / "failure_traceback.log").write_text(traceback.format_exc())
    finally:
        summary["failures"] = [record for record in runner.records if record["status"] != "passed"]
        summary["warnings"] = [{"run_id": record["run_id"], "warnings": record["warnings"]} for record in runner.records if record["warnings"]]
        runner.archive()
        (output / "simulation_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({"passed": summary["passed"], "counts": summary.get("counts"), "checks": summary.get("checks"), "error": summary.get("error")}, ensure_ascii=False, indent=2))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
