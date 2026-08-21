# Contributing

Thanks for looking. This repo is small on purpose; contributions that keep it
small, deterministic, and honest are welcome.

## Setup and tests

Runtime is stdlib-only; the dev extra is pytest.

```
git clone https://github.com/LZBiala/adversarial-chambers
cd adversarial-chambers
pip install -e ".[dev]"
```

Before opening a PR, run the same sequence CI runs (Windows + Linux, Python
3.12 pinned, zero secrets):

```
pytest -q
python tools/blocklist_check.py
python -m chambers demo --quiet
git diff --exit-code
```

All four must pass. The last step is the drift gate: the committed artifacts
ARE the claims, and the build fails if a fresh run disagrees with them.

## What PRs are welcome

- **New fixture proposals** - especially ambiguous ones (evidence margin
  under the clear threshold); that zone is where the flip test earns its
  keep. Keep counts in sync with the README prose (tests pin them).
- **New scripted judges or refuters** with a distinct, honestly stated
  decision rule - each one is a probe of the instrument, not a benchmark
  entry.
- **New structural contracts** in the orchestrator or ledger, with tests
  that show the raised exception, not just the happy path.
- **Flip-test extensions** - e.g. multi-judge disagreement metrics - so long
  as they stay deterministic and keyless.

Doc fixes are welcome too; measured numbers are not hand-editable (see below).

## House law

> Every published number must regenerate in CI - the build fails if a claim
> drifts. Live-model results never enter drift-gated sections. The hygiene
> gate must pass.

Practically: never edit text between the `AUTOGEN` markers in README.md
(report.py regenerates it), never type a measured number by hand, and never
add live-model results to the README - the bring-your-own-judge seam exists
so you can run those yourself, elsewhere.
