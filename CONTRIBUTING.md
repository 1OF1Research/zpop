# Contributing to zpop

zpop is developed to Zcash community standards. The Zcash ecosystem's
reference for development practice is the librustzcash style guides and
review culture; this Python project applies the same spirit: small,
reviewable changes, correctness argued from the consensus rules, and
tests that would catch the failure they name.

## Development setup

```sh
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python3 tests/test_units.py
python3 tests/test_receipts.py
```

Python 3.12. Runtime dependencies are deliberately minimal: the standard
library plus grpcio/protobuf for the lightwalletd protocol. All
cryptography is implemented in-tree and tested against published vectors;
please do not add a cryptography dependency without a discussion first.

## Ground rules

- **One computation path.** Facts are computed by the same code in the
  builder and the verifier (`zpop/window.py`, `zpop/txp.py`). A change
  that lets a receipt drift from the method that checks it will not be
  accepted.
- **Two sources or a stated limitation.** A new fact field must either be
  cross-checked against an independent public source or carry its
  limitation in the receipt and the README. Silent single-source facts
  are how verifiers become storytellers.
- **Reproducible checks only.** Comparisons must be against closed-window
  chain data or height-pinned queries — never against a source's current
  tip, index state, or any value that changes between runs.
- **Tests name their sensitivity.** Every negative test states the
  tampering or forgery it must catch (see `tests/test_receipts.py`).
  Every test outcome, pass or fail, is recorded with the condition under
  which the result would change.
- **Negatives matter as much as positives.** A change that weakens a
  rejection path (forged control proof, edited fact, spliced chain) is a
  regression even if every positive test still passes.
- **No key material, ever.** `keys/` is gitignored. Demonstration keys
  are lab-only and worthless by design; real operator keys must never
  appear in this repository, in issues, or in test fixtures.
- **Style.** PEP 8, modules kept small and single-purpose, docstrings
  that state what a function proves and what it assumes. Prefer the
  standard library. Comments explain *why*, with dates on empirical
  findings (API behaviour, source quirks), so a future reader can
  re-check them.

## Pull requests

Keep them focused, describe the claim the change makes and the check
that could prove it wrong, and include before/after test output. Changes
to consensus-derived numbers (subsidy schedule, funding streams) must
cite the ZIP they implement.
