"""chambers — adversarial orchestration patterns, with the judge on trial too.

The premise, stated so it can be attacked: one agent mostly agrees with how
you phrased the question. A chamber separates the roles — one side generates
proposals, a dedicated refuter attacks each one, and a judge weighs the
exchange — and writes every verdict to a ledger WITH its cause of death,
because an unrecorded kill gets re-proposed a month later. Then the part most
pipelines skip: the judge itself is put on trial. The flip test re-runs the
judge on IDENTICAL material changing only its standing default instruction;
a verdict that flips with the instruction was never a verdict about the
evidence.

What this package deliberately CANNOT measure:
- any live model's judging behavior (the bundled judges are deterministic
  rules; their flip rates prove the INSTRUMENT detects instruction
  sensitivity, nothing about any AI);
- whether adversarial review improves decisions (that needs outcome data
  this harness does not collect);
- the direction of any real judge's bias (the flip test detects sensitivity;
  attributing direction needs a design this repo documents but does not run).

Those limits are printed into the report and the README. The honest product
is the role-separated orchestration, the auditable ledger, and a calibration
harness you can point at any judge you bring.
"""
from __future__ import annotations

__version__ = "1.0.0"
