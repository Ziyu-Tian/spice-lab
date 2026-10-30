# Simulation audit report — preliminary excitation stage only

PASS: actual ngspice 44.2 execution of 63 final OP plus 63 AC analyses, three excitation models, seven load resistances and three current perturbations each. Full commands/return codes are in simulation_audit/matrix.json; executed netlists, ASCII op.raw/ac.raw and complete logs are in individual run directories. No device model libraries are required by these linear/behavioral excitation circuits. Sources of fitted parameters are only observations.csv; assumptions are documented in the measurement report.

PASS: six calibration-point checks independently recalculate resistor/source KCL, compare expected measured voltages (0.1 mV limit) and symmetric DC incremental impedance with actual 1 Hz AC impedance (0.1 Ω limit). See checks.json. The measured points are used in fitting and cannot provide independent validation. Impedances include Rload in parallel with the excitation impedance. AC amplitude is normalization, not a physical 1 A perturbation.

PASS: schematic/netlist correspondence for A (parallel sink/Rout), B (negative source/series resistor) and C (behavioral sink) as documented in measurement_model_report.md, with Rload and Iprobe explicitly included. RTN is ground only for this isolated port experiment. PCB +24 V transformation remains NOT VERIFIED.

FAIL retained: development_attempt records the first compliance-knee fit, which missed the second observation by 0.339 mV. The corrected fit accounts for the assumed finite 10 Ω knee slope. First-run raw data, failed check and logs are retained; never overwrite evidence. Solver warning/failure information is retained verbatim in each solver.log and console.log; zero return code is not the check criterion.

NOT VERIFIED: DS3930 limits/model, 2N5320 manufacturer model, PCB reconstruction, six-point BJT calibration, integer code sweeps, temperature/device sensitivity, passive optimisation and nine-channel behavior. No synthetic curves, operating points or missing observations are supplied for these stages. Convergence is not hardware validation.

Reproduce in a fresh copy (the script intentionally refuses overwriting):

```bash
source .local/env.sh
python experiments/phase3/run.py
```

Use a new experiment copy without simulation_audit/matrix.json to reproduce; preserve this audit. Python/ngspice versions and input Git commit are in versions.txt and source_commit.txt. SHA256SUMS uses paths relative to experiments/phase3; run `sha256sum -c simulation_audit/SHA256SUMS` from there. The hash list excludes itself and is refreshed after reports are written. Current delivery commit is the Git commit containing these artifacts; source_commit.txt identifies the input research branch. Prior Phase 1 evidence is unchanged.
