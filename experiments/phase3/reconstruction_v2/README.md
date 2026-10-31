# Phase 3 reconstruction update

The supplied schematic resolves upper-PCB connectivity. New work reconstructs a loaded, integer-code DS3930 equivalent and executes calibration, 99 candidate configurations across reference/excitation hypotheses, temperature/parameter/excitation sensitivity and nine-channel stress scenarios. Old Phase 3 evidence remains unchanged.

**Outcome:** no verified retrofit optimum. A conditional RE=1 kΩ case increases Mode 5/6 code separation from 2 to 3 and Mode 2/3 from 3 to 4 at reselected targets, while retaining all six voltages. However, baseline model error, unknown RTN reference, generic reverse transistor parameters and unverified DS3930 limits prevent a hardware recommendation. RE=2.2 kΩ loses Mode 6 reachability in the lower-error B scenario.

- [Schematic connectivity extraction](connectivity.md)
- [Readable equivalent circuit](equivalent.md)
- [Measurement Model Report update](measurement_model_report.md)
- [BJT Optimisation Report](bjt_optimisation_report.md)
- [Complete conditional comparison](comparison.md)
- [Simulation Audit Report](audit_report.md)
- [Conditional calibration plots](conditional_calibration.png)
- [Operating-point table](calibration_operating_points.csv)
- [Independent KCL/DC/AC checks](independent_checks/checks.json)

The supplied PDF and page rendering are in source/. No EasyEDA project or PCB was modified. PR #2 remains the delivery PR; do not merge.
