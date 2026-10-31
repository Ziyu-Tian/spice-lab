# Phase 3 measurement model report — preliminary

Two observations do not establish a constant HVAC sampling current. Dividing voltage by the measured resistance gives −464.957 and −430.857 µA respectively (derived, not directly measured). Their secant dV/dR is −362.069 µA, a different quantity. Measurement uncertainty and sampling timing were not supplied.

Reference for these isolated excitation experiments: RTN = SPICE 0. This is explicitly **not** the PCB local ground. For later full reconstruction, use V_spice(node) = V_physical(node) − V_physical(system +24 V), with RTN retained as a separate node at its measured transformed potential. That potential is currently unavailable. Never shift only Sensor or only the BJT terminals.

## Complete single-port schematics

Each diagram includes the test resistor Rload between Sensor and RTN. Iprobe is a test instrument from RTN to Sensor, DC zero for nominal OP, AC 1 A normalization for linear analysis; it is not a proposed retrofit supply.

```
A: Sensor -- Rload -- RTN
   Sensor -- Rout=6158.335720 Ω -- RTN
   Sensor -- current sink 553.292819 µA --> RTN
   RTN -- Iprobe --> Sensor

B: RTN -- Vexc (supply−RTN = −3.407362933 V)
   supply -- Rs=6158.335720 Ω -- Sensor -- Rload -- RTN
   RTN -- Iprobe --> Sensor

C: Sensor -- Rload -- RTN
   Sensor -- Bexc sink I(V) --> RTN
   RTN -- Iprobe --> Sensor
   I(V)=max(0, 464.957265µA + min(0,(V+0.753658999)/10Ω))
```

A models a finite-output-resistance current sink: its load current falls to zero at −3.407 V. Beyond that voltage the simple Norton equivalent reverses current; it is only a local equivalent, not a complete rail-clamped current regulator. B is exactly equivalent at the port, at every load, within this linear model. Neither port measurement can distinguish their physical implementation. Optional voltage offset is omitted: no physical series offset has been evidenced.

C is a deliberately different finite-compliance regulator with a 10 Ω compliance-region incremental resistance. This 10 Ω is assumed, not identified. Sink current is fitted at the first observation; the knee is then fitted at the second. This provides a family of nonlinear counterexamples to unique identification. It is a phenomenological behavioral source, not a manufacturer circuit or retrofit.

| Model | predicted V at 1170 Ω | predicted V at 1750 Ω | loaded 1 Hz incremental Ω at 1170 / 1750 Ω |
|---|---:|---:|---:|
| A finite output resistance | −0.544 | −0.754 | 983.205 / 1362.750 |
| B resistive excitation | −0.544 | −0.754 | 983.205 / 1362.750 |
| C compliance knee | −0.544 | −0.754 | 1170 / 9.94318 |

Values above are rounded actual ngspice results in simulation_audit/checks.json. Fits use the same observations: they are calibration, not independent validation.

For B, V=Es R/(Rs+R). Two exact observations uniquely identify Es and Rs **conditional on this two-parameter linear model**. A has the corresponding Norton parameters, not independent supporting evidence. Nonlinear regulator law, compliance knee resistance, timing and offsets are underdetermined. Even the precision of the conditional parameters is unknown without measurement uncertainty.

Power flow: both measured resistor powers are positive (approximately 253 and 325 µW), while current flows from RTN through Rload toward negative Sensor. A and C sink conventional current while delivering energy at negative port voltage. B's negative supply provides that energy. This is physically possible for the existing HVAC excitation; these sources are not proposed additional supplies. No HVAC ADC architecture is inferred.

Best next experiment: measure the Sensor−RTN waveform with a third known resistor (e.g. 3.3 kΩ) at the same sampling phase, then measure open circuit with a suitable high-impedance instrument. The executed 3.3 kΩ and near-open predictions are in operating_points.csv. A small calibrated current perturbation near 1.75 kΩ tests the large impedance difference above. A/B remain indistinguishable as equivalent linear one-ports; internal hardware inspection is necessary to distinguish them. Confirm timing, loading, repeatability and voltage sign in every measurement.
