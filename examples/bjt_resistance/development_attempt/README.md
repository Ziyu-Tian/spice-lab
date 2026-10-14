# Retained development attempts

These are the actual earlier executions, preserved without replacing their outputs.
Both computed 252 OP conditions, 756 AC observations and two gmin diagnostics.
Neither had a failed ngspice process or a Code Model loading failure. They exited
nonzero because the Python verification criteria needed the following diagnoses.

1. `first_run`: the initial intrinsic `@q1` three-current KCL assertion ignored the
   numerical gmin contribution. The zero-current finite difference used +/-10 nA;
   for the 0 C, 0.45 V bias point the resulting voltage excursion was not small
   enough, producing 4.33% disagreement with the real AC derivative. Its warning
   detector also mistakenly counted ngspice's informational console line
   `Comments and warnings go to log-file` as a warning in all 298 executions;
   the raw logs are retained and show it is not an actual circuit warning.
2. `second_run`: added a zero-volt emitter terminal current sensor, retained
   both intrinsic and external residuals, removed the informational-line false
   warning, and reduced the zero-current finite difference to +/-0.1 nA.
   The finite-difference verification passed; external terminal-current KCL still
   differed at the extreme out-of-scope voltage points because of numerical gmin
   current accounting. All points inside the declared +/-5 V example evaluation
   window had KCL residual <1 pA. The remaining verification failure applied the
   in-window KCL tolerance incorrectly to unphysical, no-breakdown high-voltage
   extrapolations. The final suite restricts that criterion to the declared
   window, keeps all-domain residuals, and additionally verifies the observed
   intrinsic residual after accounting for gmin*Vport. No high-voltage observation
   is presented as a usable physical resistance implementation.

Later explicit-substrate simulations confirm that the three-terminal Q syntax
defaults its substrate to ground. The observed gmin current in that branch was
omitted from the collector/base/emitter sum; the imbalance is not a violation of
charge conservation. See the supplemental `../substrate_diagnostic/` results.

The archived netlists show the exact current perturbation, model, options and
current sensors used in each attempt. Each manifest records all process return
codes, log diagnostics and file hashes. Earlier data were not fabricated or
silently overwritten; final results use a fresh output directory.
