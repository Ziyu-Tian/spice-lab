# Measurement model update

The original two-resistor investigation and raw evidence remain unchanged at ../measurement_model_report.md and ../simulation_audit/. The schematic fixes the **potentiometer** rails but does not identify HVAC excitation or RTN potential. Keep B (−3.407362933 V through 6158.335720 Ω) and the compliance-limited C family as separate hypotheses.

New combined-data test: this particular C model clamps the negative sensor voltage near −0.758 V. With the assumed passive interconnects and tested RTN scenarios, it cannot reproduce the Mode 1 observation −0.792 V and fails reachability in all 33 first-stage candidates. Do not discard all compliance-limited current-source models: its knee slope/compliance law were assumed from only two resistor observations. A different regulator law or sampling waveform may fit. This is rejection of a specified candidate under declared assumptions, not hardware identification.

Best additional measurements are now: (1) RTN relative to PCB local GND, simultaneously with the Wiper and Sensor; (2) loaded Wiper and base voltage/current at codes 30,41,43,73,75; (3) Sensor−RTN waveform with 3.3 kΩ and near-open circuit, including sample timing; (4) actual C/B/E continuity/pinout. These distinguish supply-reference uncertainty from reverse BJT gain and excitation-model errors. Also measure HI and LO rails to verify the schematic's nominal 5 V differential.

No temperature-to-voltage thresholds are inferred. The six BJT points remain calibration observations, not validation data. New measured points withheld from fitting are needed for validation.
