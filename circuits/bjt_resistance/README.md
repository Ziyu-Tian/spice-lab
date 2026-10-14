# BJT resistance experiment circuits

`generic_npn.lib` is an explicitly specified educational model of ngspice's built-in
Gummel-Poon NPN, not a DS3930 model or a manufacturer's transistor model.
It does not include avalanche breakdown, tolerances, or self-heating. Its numerical
solutions outside the example evaluation window `|Vport| <= 5 V` are retained but
flagged as unsuitable for physical resistance-emulation claims. This window is an
experiment assumption, not a specification of an HVAC controller.

The `.cir.in` files are Python `str.format` templates used by
`scripts/simulate_bjt_resistance.py`. Every invocation creates fully expanded SPICE
netlists. All generated netlists and ngspice logs/raw files are kept in the run's
`raw_evidence.tar.gz`, and `run_manifest.jsonl` records the exact execution command,
return code, diagnostics, and SHA-256 hashes.

## Current-driven three-terminal test

`Isample 0 port` injects a signed DC current into the collector port. Zero-volt
sources sense the actual collector and emitter terminal currents. The emitter is grounded; an independent voltage
source drives the base through 10 kOhm. Positive current enters the port and
negative current leaves it. This is an active circuit with a separate base supply;
that supply can exchange current and energy with the measured port.

The static apparent resistance is `Vport / Iport`. The incremental impedance comes
from a real AC analysis at 1 Hz, 1 kHz and 100 kHz, with a 1 uA phasor current
source. Ngspice AC analysis is the linearized derivative at the operating point;
its source amplitude does not represent a finite-amplitude time-domain stimulus.
A second independent derivative estimate uses OP runs at `I +/- 0.1% * |I|`.

Six fixed base supply voltages, 0.45 through 0.70 V in 0.05 V steps, reveal the
bias dependence. For each target, one further bias is determined at 25 C and
+50 uA: a voltage-clamped OP is solved until the collector draws 50 uA at
`Vport = 50 uA * target_R`. The resulting bias is then frozen across all current
and temperature conditions. Calibration is independently checked with the
current-driven circuit. No per-condition tuning is performed.

## Ideal reference

`resistor_reference.cir.in` places the target physical ideal resistor directly
between port and ground. It has no temperature coefficients. It is simulated at
the same signed currents, temperatures and AC frequencies; its expected static
resistance and incremental impedance are both the stated resistor value.

At zero DC current the independent OP derivative check uses +/-0.1 nA.
The standard ngspice numerical junction conductance is `gmin=1e-12 S`; an
extra two-point diagnostic repeats a nominal and an extreme high-voltage point
with `gmin=1e-14 S`. This three-terminal syntax also has a default grounded
substrate: reading only collector/base/emitter currents omits its numerical gmin
branch. Supplementary explicit-substrate simulations identify that branch; the
three-current imbalance is not a violation of charge conservation. The strict
three-terminal residual check is limited to the declared evaluation window, and
both all-domain intrinsic/external residuals and the gmin-adjusted diagnostic are
retained. These quantities are not physical leakage measurements.
