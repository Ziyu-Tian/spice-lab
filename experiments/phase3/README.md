# Phase 3 — preliminary, hardware reconstruction blocked

The resistor measurements admit multiple excitation models. A −3.40736 V Thevenin source with 6.15834 kΩ series resistance fits both exactly; a compliance-limited current sink also fits, while predicting very different incremental impedance. No constant sampling current or ADC architecture is established.

The primary question remains unanswered: no passive retrofit can yet be recommended without the missing DS3930 schematic/reference evidence. No BJT optimisation or nine-channel simulation is claimed complete.

- [Measurement Model Report](measurement_model_report.md)
- [BJT Optimisation Report and pending comparison matrix](bjt_optimisation_report.md)
- [Simulation Audit Report](simulation_audit_report.md)
- [Executed simulation matrix](simulation_audit/matrix.json)
- [Independent checks](simulation_audit/checks.json)
- [Original observations](observations.csv)

Published main inspected via GitHub connector: f0cd19558d1f6992f9b75168fc30103be08f2cb6. Existing local research branch used as input: 6b11aaf6b5d274f477fc6962c6d2637c83a07387. Git fetch failed because the configured proxy was unreachable. Published tree contained no Phase 2 DS3930 artifacts or PCB schematic. Please supply their location to continue the dependent work.
