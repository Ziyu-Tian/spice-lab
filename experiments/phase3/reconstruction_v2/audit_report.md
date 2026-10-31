# Additional simulation audit — append-only reconstruction v2

Original experiments/phase3/simulation_audit and development_attempt are unchanged. New directories contain the reconstructed sweeps. Process counts: {'simulation_audit': 618, 'reference_audit': 443, 'calibrated_audit': 267}; independent_checks adds 15 OP + 15 AC runs. A code sweep has 256 actual ngspice solutions, not interpolated points. Sensitivities and all numerical curves derive from executed SPICE outputs; no invented observations are appended.

PASS: connectivity extraction from PDF and explicit reference transformation; explicit C/B/E order preserved. Schematic/netlist correspondence: both pot segments at HI=+5 and LO=0, Rw→RB→B, collector Sensor, emitter via RE to RTN, shaping B→RTN. The external circuit remains assumed from notes. PDF covers only upper PCB.

PASS: representative independent_checks/checks.json compares external collector/base/Wiper and intrinsic transistor KCL (1e−8 A tolerance) and independent symmetric DC current perturbation with actual 1 Hz AC impedance (max 0.1 Ω or 0.1% tolerance). It uses codes 30,41,43,73,75 under the best conditional B fit. ngspice implicit gmin can leave sub-pA residuals. Solver convergence is not hardware validation.

FAIL: RTN=0 models fit poorly, IS reaches the allowed upper bound; they are retained as failed calibration hypotheses. FAIL: the particular compliance-knee C family fails combined six-point calibration and reachability under the examined assumptions. Its two-resistor fit is still valid. Alternative compliance laws are not excluded.

NOT VERIFIED: manufacturer DS3930 and 2N5320 electrical limits, actual resistance values, physical Veroboard pinout, measured RTN offset, board rail waveform, model uniqueness, nine-channel aggregation, precise mode thresholds and hardware validation. Thus every hardware-compatibility gate is NOT VERIFIED and no global passive optimum is approved.

Raw evidence is losslessly stored in raw_evidence.tar.gz inside each sweep audit directory, preserving run-directory names, executed netlists, raw files, logs and CSV. Extract there with `tar -xzf raw_evidence.tar.gz` before detailed inspection. Independent checks remain unpacked. Matrix JSON includes all commands, parameters and return codes. Inspect solver.log/console.log for warnings; diagnostics.json inventories warnings/errors, rather than hiding them. Source models and assumptions are in equivalent.md. SHA256SUMS is relative to reconstruction_v2; old hashes remain untouched. input_commit.txt records the input commit; the delivery Git commit records these new artifacts.

Reproduce in a fresh reconstruction_v2 copy (scripts refuse overwriting completed matrices): source .local/env.sh, run run.py, reference_analysis.py, calibrated_analysis.py, audit_checks.py, then report.py. Scripts use existing scripts/simulate_bjt_resistance.py only for parsing ngspice ASCII raw. Reproduction paths are rooted in the existing repository. Save generated directories separately before rerunning. Scripts and source PDF are hashed.

## Retained startup errors and independent replay

Every initial sweep logged failed attempts to load relocated XSPICE code-model libraries from /usr/lib. These errors are retained in diagnostics.json and raw logs. The executed circuits use built-in resistors, B sources and Gummel–Poon Q devices, with no XSPICE A devices. A representative complete baseline sweep was independently replayed with `ngspice -n -b -o solver.log run.cir`, bypassing startup files. It produces **identical values in every saved vector** (maximum difference zero); see startup_replay/check.json. This resolves the effect on that representative circuit, not a claim that the installed XSPICE libraries are configured correctly. All required rawfiles contain 256 finite code points; independent_checks additionally verifies meaningful OP/AC results. No missing model is silently substituted.

Correction to scope: limits checking remains NOT VERIFIED because datasheet retrieval failed. The present work completes a conditional simulation comparison, not all manufacturer compliance gates requested for a validated optimum.
