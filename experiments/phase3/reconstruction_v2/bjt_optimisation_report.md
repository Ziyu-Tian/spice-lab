# Reconstruction and conditional optimisation

No hardware retrofit can yet be recommended as a robust six-mode solution. The supplied schematic now establishes the upper PCB connectivity; the previous missing-schematic blocker is resolved. Phase 2 functionality has been reconstructed minimally rather than made a prerequisite. Remaining limitations are explicit and quantified below.

[Connectivity table](connectivity.md), [equivalent circuit](equivalent.md), [complete comparison table](comparison.md), [operating points](calibration_operating_points.csv) and [six calibration plots](conditional_calibration.png) provide the review trail. Both DS3930 devices have HI and VCC on +5 V, common LO and GND on local GND (system +24 V). There are six U1 Wipers and three U10 Wipers. The PDF supplies no Veroboard transistor evidence and does not locate HVAC RTN relative to PCB local GND.

## Calibration quality

RTN=0 is an assumption, not a connection extracted from the PCB. Fitting generic reverse gain BR and IS under that assumption gives RMSE 65.68 mV for B and 40.21 mV for C. The optimizer pushes IS to its deliberately broad 1e−8 A bound: these are poor fits, not manufacturer transistor models. The full failed sweeps are retained.

Allowing the unknown RTN voltage to vary, with IS constrained to 1e−16…1e−12 A and BR=0.01…1000, yields a conditional B fit with RTN≈−1.69362 V relative to local GND, BR≈5.50877 and IS≈1e−16 A. RMSE is 6.359 mV, maximum absolute error 10.388 mV. Different starting references were tried and their fits are retained separately in reference_fits.json. The IS bound is active. Neither fitted RTN nor fitted BR/IS is a measurement or unique physical identification. Pot resistance 50 kΩ, wiper resistance 100 Ω and code/256 tap law remain assumptions awaiting datasheet verification. Temperature effects are generic-model predictions.

|Mode|Code|Measured V|Conditional simulated V|Error mV|
|---|---:|---:|---:|---:|
|1|30|−0.792|−0.781612|10.388|
|2|41|−0.726|−0.729062|−3.062|
|3|43|−0.709|−0.719163|−10.163|
|4|50|−0.681|−0.683661|−2.661|
|5|73|−0.560|−0.557147|2.853|
|6|75|−0.548|−0.545390|2.610|

All six conditional operating points have BC forward biased, VCE negative and BE weakly biased: reverse-active/BC-forward behavior, not conventional forward-active linearity. Signed collector currents are negative, approximately −426…−465 µA; base current is approximately 66…73 µA. Every voltage/current and local slope is in calibration_operating_points.csv. The conditional slopes near codes 41/43 are about 4.92/4.98 mV per code, and 73/75 about 5.85/5.91 mV per code. The former fails to reproduce the observed 8.5 mV/code secant of Mode 2/3. This is substantial model discrepancy relative to closely spaced targets, not an independently validated transfer.

Observed Mode 4/5 is 121 mV over 23 codes (5.261 mV/code secant), consistent with the broad scale of the conditional curve but not evidence of exact switching thresholds. No region change is evident in the six conditional operating points. The irregular measured secants could reflect model inadequacy, timing, noise, reference changes or hardware details; the data do not uniquely attribute them to BJT region transitions.

## Passive retrofit comparison

For each excitation candidate, 33 configurations were executed: five RB choices (22k,29.9k,33k,47k,68k) × six RE choices (0,100,220,470,1k,2.2k), plus three B–RTN shaping resistors (47k,100k,220k). The lower-error conditional B fit was then swept independently over the same 33 configurations. No per-design transistor or excitation refitting was used. All code sweeps are integer 0…255.

With RB=29.9k under the conditional fit, the original circuit's nearest six target codes are [28,42,45,51,73,75]. RE=220 Ω yields [29,43,47,52,74,76]; Mode 2/3 code separation grows 3→4, Mode 5/6 stays 2 and Mode 1/2 stays 14. RE=1 kΩ yields [35,49,53,58,80,83], giving Mode 2/3 margin 4, Mode 5/6 margin 3, Mode 1/2 margin 14. These compare reselected model targets, not observed software settings or classification intervals.

RE=1 kΩ modestly changes 0–50°C worst mode voltage span from 43.49 to 42.06 mV. Its factor-of-two BR stress span falls from 1274 to 943 mV but remains far above the 12/17 mV separations. Excitation ±5% stress span rises slightly from 154.55 to 156.49 mV. The factor-of-two BR and excitation variations are exploratory assumptions, not measured tolerance distributions. The large variations indicate model fragility, not guaranteed hardware errors.

RE=2.2 kΩ flattens the curve markedly but cannot reach Mode 6: at the nearest endpoint the error is about −9.24 mV. Reject it on reachability before considering its smaller temperature span. The complete table reports all RB/RE and shaping alternatives; a nominal code-margin gain cannot overcome unverified device limits and calibration mismatch. Shaping components use only B/RTN, with no added supply. No recommendation is based on historical-code RMSE alone.

## Nine-channel variability

Nine channels share the same code and ideal rail/reference boundary conditions; outputs are independently solved. This is equivalent to nine uncoupled nominal channels on an ideal common supply, not validation of shared supply impedance/crosstalk. Deterministic channel index spans BR factor 0.5…1.5, IS log-offset −0.3…+0.3 decades, Rpot 40…60 kΩ and Rw 50…250 Ω. These assumed correlated stress points are not a statistical Monte Carlo or manufacturer tolerance distribution.

Both first-stage excitation hypotheses and the lower-error B fit have individual channel CSVs, hypothetical mean/min/max and worst-channel summaries. The conditional original circuit has roughly 944…1025 mV channel spread at the historical six codes, with channel 1 farthest from the hypothetical mean. That overwhelms the observed closely spaced voltage separations in this stress scenario. Identical codes across all nine channels therefore cannot be established as robust from this model. The mean is explicitly hypothetical; HVAC aggregation is unknown. Per-channel calibration and measurements are needed before selecting realistic variation bounds or inferring actual rig performance.

## Device gates and conclusion

The actual DS3930 datasheet could not be retrieved (manufacturer URL HTTP 403; search tools failed). Manufacturer voltage/current limits and resistance specifications therefore remain NOT VERIFIED; no datasheet-compliance PASS is claimed. Assumed-equivalent full-code sweeps report Wiper extrema/current in optimisation JSON; endpoint Wipers can be slightly below local GND, requiring real protection-clamp/limit checks. A generic model has no validated avalanche, leakage, self-heating or 2N5320 voltage-rating coverage. These gates block a hardware-safe optimum, not the simulation work.

RE=220 Ω and 1 kΩ are conditional bench candidates, with 1 kΩ showing a nominal Mode 5/6 code gain. Neither is recommended for retrofit yet. First measure RTN, loaded Wiper/base and actual transistor connections, verify manufacturer limits, and add independent calibration observations. The current evidence supports a testable comparison, not a claim that passive degeneration solves HVAC mode recognition.
