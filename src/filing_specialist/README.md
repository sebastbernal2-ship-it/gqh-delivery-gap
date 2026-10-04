# src/filing_specialist

The filing specialist v0: a point-in-time join from a filing to the next obligation revision,
plus the classical baseline the text model must beat.

- `panel.py` owns the join, the label rule and the clock discipline. One row is one obligation
  revision; the decision is the latest filing strictly before that revision's availability; every
  feature is known strictly before the decision; an unknown feature stays null with a flag.
- `model.py` owns the multinomial baseline, the training-only scaler and the proper scores, and
  always reports the prevalence reference beside the fit.

Protocol: `docs/plan/filing-specialist.md`. Runners: `scripts/build_filing_specialist_panel.py`
and `scripts/run_filing_specialist.py`. It does not fetch documents, size positions, or open a
sealed window.
