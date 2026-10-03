# Validation status

2026-10-03, branch `research/unified-factor-model`, based on `09b6385`.
Research implementation; feature-branch delivery authorized by the user. No production data, strategy trades or sealed holdout opened.

- Fourteen module tests pass: covariance reconstruction, signed risk allocation, cross terms,
  correlated residuals, factor permutation, overlap detection, aliases, collinearity, publication
  lag, future-data isolation, schema boundaries and hedge span.
- The synthetic CLI completes all five fixed baseline specifications, with 300 training and
  120 subsequent evaluation observations. Synthetic outcomes validate plumbing, not market performance.
- Reports record input, source-code and output hashes, Python/NumPy versions, factor definitions,
  cutoff, weights and estimator settings. The synthetic source is identified by seed and version.
- Repository-wide `make check` stops on existing structure problems: tracked `.vscode` is not
  an allowed root area; `src/factors/` and `src/models/` lack README files.
- Repository-wide `make test` passes its initial suites but stops because the Makefile references
  missing the absent `test_strategy_contracts.py` test. Remaining repository suites were not run by that command.
- `git diff --check` passes. Shared repository failures were left unchanged in this isolated workstream.

Run the module checks using the commands in README.md. NumPy is required; no download or account is needed.
The next empirical gate is an explicitly authorized, point-in-time development panel with fixed currency,
horizon, factor constructions and portfolio weights. DCC, latent-factor extraction, nonlinear
repricing and execution-constrained hedging remain planned, not tested implementations.

## GARCH extension

Updated after sync to `e417d0d`. No overlapping pushed branches were reported. Twenty-two combined
core/GARCH tests pass with arch 7.2.0, pandas 2.3.3, NumPy 2.5.3 and SciPy 1.18.1. Tests cover
library forecast agreement, stationarity/mean reversion, positive-semidefinite covariance, exact risk
reconciliation, unchanged forecasts after future-data mutation, publication-gap refusal, insufficient
history, optimizer failure and direct QLIKE calculation. All five synthetic CCC-GARCH fits succeed.
EWMA has lower QLIKE in this constant-volatility fixture; no model is promoted from synthetic scores.
The first dependency attempt exposed arch 7.2 incompatibility with pandas 3; requirements now bound
pandas below 3 and the full run passes. Existing repository-wide check failures above remain outside scope.

## Delivery verification

Revalidated after syncing main through `9d3b876`: all 22 component tests and all five synthetic GARCH
fits pass. The credential scan is clean and ownership validation passes. Global structure checks still
fail on the inherited items above. The path checker also finds missing test/script references in the
existing Makefile and another workstream's handoff. No production data or generated model artifacts
are included in this feature commit. Detailed design decisions are in DESIGN.md.

Final pre-commit rebase incorporated `6da2e4b`, which changes delivery-hazard outcomes and planning,
not this component. Its new empirical claims were not rerun by this risk-model delivery. The earlier
Stage A audit in RESEARCH.md is explicitly version-scoped, not an audit of every later study.
