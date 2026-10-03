# Unified factor research

Owner: aidanq06. Research branch component; no promoted strategy, production deployment or sealed test.

The objective is a common accounting system for observable exposures, shared risk, hedge coverage and
unexplained uncertainty. It is not a claim that all risk is identifiable. A precise residual is more useful
than a fabricated economic explanation. Read `RESEARCH.md` for hypotheses and the staged global design. `DESIGN.md` documents the implementation
decisions and data flow; `INTERFACE.md` describes integration contracts; `VALIDATION.md` records checks.

## Implemented

- Canonical factor identifiers and typed metadata: family, channel, role, units, source and evidence.
- CAPM, FF3, Carhart4, FF5 and FF5 plus momentum, fitted jointly by standardized OLS with an intercept.
- Date/availability filtering at each training cutoff; no silent imputation, mixed currency/horizon,
  missing factor, or renamed factor semantics. Producers must attest that availability dates are truthful.
- Duplicate-alias rejection, rank checks, standardized condition number, pair correlation and VIF.
- Full covariance of factors AND asset residuals using sample or centered EWMA estimates, with optional
  fixed diagonal shrinkage. This is not a Ledoit-Wolf estimator. An optional CCC-GARCH estimator is described below.
- Portfolio beta, signed Euler variance contributions by factor/family/residual asset, factor-residual
  cross terms, residual correlation effect, and a residual leading-eigenvalue diagnostic.
- Unconstrained hedge-span projection. It says what the proposed hedges span in caller-scaled coordinates;
  it does not authorize positions or establish an executable hedge.
- Fixed-loading evaluation on a later development panel, plus input and model artifact hashes.

## Run

Requires Python 3.11+ and NumPy. Use an isolated environment; these are optional component dependencies,
not new global repository requirements. The local verification used NumPy 2.5.3.

```sh
PYTHONPATH=src python -m unittest unified_factors.test_core -v
PYTHONPATH=src python -m unified_factors.run --synthetic --output /tmp/unified-factor-demo
PYTHONPATH=src python -m unified_factors.run --panel /tmp/development-panel.json --cutoff 2021-12-31T23:59:59Z --weights 0.4,0.3,0.2,0.1 --output /tmp/unified-factor-development
```

Output directories must be new. The demo is 420 artificial daily observations of four assets, including an
intentionally omitted shared shock. It produces `report.json`, `exposures.csv` and numerical `.npz` artifacts
for all five models. These are engineering outputs, not submission evidence or strategy returns. Numerical
artifacts use ordinary arrays and can be opened with NumPy `allow_pickle=False`; report metadata supplies
their schema, fit cutoff and interpretation. There is no production model loader in this version.

## Input contract

One complete, aligned snapshot per source version; excess returns already computed in decimal units.
`available_at` is the latest actual publication/availability time of any value in that row, including
revision vintages. A current revised history stamped with its original observation dates is invalid.
The loader cannot independently verify a producer's timestamp assertion. Preserve source receipts upstream.

```json
{
  "study_role": "development",
  "currency": "USD",
  "horizon": "daily_close_to_close",
  "source_version": "immutable-export-hash-or-manifest-id",
  "assets": ["PWR", "ETN", "EME", "DLR"],
  "factor_specs": [
    {"id":"MKT", "family":"market", "economic_channel":"broad_equity",
     "role":"return_factor", "unit":"decimal_return", "source":"pinned-factor-vintage",
     "canonical_id":"MKT", "hedge":"unverified", "evidence":"research_baseline"}
  ],
  "rows": [
    {"period_end":"2021-01-04T21:00:00Z", "available_at":"2021-02-05T12:00:00Z",
     "excess_returns":{"PWR":0.01,"ETN":0.005,"EME":-0.003,"DLR":0.002},
     "factors":{"MKT":0.004}}
  ]
}
```

This illustrates the schema only; it intentionally has too few rows to fit. Available standard factor IDs
are `MKT, SMB, HML, RMW, CMA, MOM`. FF3 and FF5 SMB constructions differ: the initial comparison requires one
declared SMB series shared across specifications. Label that comparison a nested proxy comparison, not exact
replication of both published models. For exact replication, run separately pinned FF3 and FF5 panels with
their own SMB definitions and record the construction difference. RF is subtracted once from stock returns
and the market return; published long-short factors must not have RF subtracted again.

## What the numbers mean

Exposures describe a fitted representation, not causal sensitivities. Historical evaluation uses realized
contemporaneous factors and is explicitly retrospective attribution, not a forward return forecast. The
intercept is a sample regression estimate, not an alpha forecast. A covariance estimate is a risk baseline,
not proof of future tail coverage. Horizon is per observation; no automatic square-root annualization.

For portfolio weights w, factor loadings B and joint covariance C of [factors, residuals], v=[Bw,w]. The total
variance is v'C v and each component contributes v_j(Cv)_j. Contributions sum exactly; negative contributions
are allowed. Cross terms are allocated symmetrically, not double-counted or hidden. Family totals aggregate
components under one chosen taxonomy and must not be summed again with their children. Attribution changes
when an observationally equivalent factor basis changes; the total risk need not. Rank-deficient systems
are rejected rather than assigning arbitrary economically named betas. High but imperfect overlap is flagged,
not magically resolved by regularization.

Residual covariance is retained in full. The difference from a diagonal-residual calculation measures the
effect of residual correlation for these particular weights, not a universal diversification score. The
leading eigenvalue share diagnoses possible missing common structure; it neither identifies the cause nor
proves a new factor. Zero-variance and finite-data limitations remain visible.

The hedge helper is an unweighted least-squares diagnostic, requires caller-specified common factor scaling,
and ignores costs, bounds, margin, liquidity and hedge-specific risk. A systematic market factor can be
hedgeable; a company residual can be hard to diversify in a concentrated portfolio. Neither classification
is a boolean inferred from a regression coefficient.

## Next integration gates

1. Obtain an explicitly approved development export with genuine availability/vintage records, not the
   competition holdout. Current CLI rejects `sealed` roles but is not a data-access security boundary.
2. Run fixed baselines on that export and evaluate exposure stability and realized risk calibration.
3. Join pre-event contractual exposure through the proposed contract in `INTERFACE.md`.
4. Add conditional covariance, rolling evaluation, constrained hedge optimization and nonlinear scenarios
   only after comparing with the current transparent baseline.

DCC, Kalman betas, residual PCA factors, causal discovery, global currency conversion, options Greeks,
tail/copula models, event extraction, automatic database access and quantum methods are NOT implemented.
No historical Stage A result is rerun or repaired by this component. The known audit issues are recorded in
`RESEARCH.md` and must not become assumptions that an economic mechanism is impossible.

## Optional GARCH risk layer

The factor model explains *which exposures* are present. GARCH estimates *how their variance changes*.
`garch.py` uses the standard `arch` package, with Gaussian quasi-maximum likelihood GARCH(1,1):

    h[t+1] = omega + alpha * innovation[t]^2 + beta * h[t]

Fit one process to each centered factor and each asset residual, then estimate a constant correlation
matrix from standardized training innovations. Preserve the entire joint matrix, including residual and
factor/residual correlations. Shrink correlation 5% toward identity; this is a fixed declared setting, not
estimated optimal shrinkage. Conditional covariance is D[t] R D[t], so the existing risk accounting applies.
This two-stage CCC construction is neither DCC nor a joint maximum-likelihood multivariate fit.

```sh
python -m pip install -r src/unified_factors/requirements-garch.txt
PYTHONPATH=src python -m unittest unified_factors.test_core unified_factors.test_garch -v
PYTHONPATH=src python -m unified_factors.run --synthetic --garch --output /tmp/unified-garch-demo
```

All five factor specifications are attempted. Failed optimization or nonstationary fits are recorded as
rejected, never silently replaced by another estimator. Accepted near-boundary estimates are flagged.
Parameters, correlation and next-period component variances are saved in each `*_garch.npz` artifact.
The baseline beta/intercept artifact belongs to the same training regression. Package versions and code
hashes are recorded in the report. The pandas upper bound avoids an arch 7.2 API incompatibility.

The comparison is a **single frozen forecast origin**: all parameters, loadings and means use training
observations only. GARCH forecasts each future period's marginal variance recursively; sample and EWMA
comparators keep their last training estimates fixed. No evaluation observations update any forecast.
QLIKE (log variance + squared innovation / variance), variance MSE and realized/forecast variance ratio
are reported for fixed portfolio weights. Innovations subtract the training portfolio mean, not future
factor realizations. Squared returns are noisy variance proxies. No statistical superiority is claimed.
This is not a rolling live-trading evaluation and horizons are not cumulative holding-period variance.

The complete pre-cutoff prefix must be available; publication holes fail instead of compressing the
volatility clock. Producers must supply consecutive observation sessions and attest there are no omitted
sessions: calendar weekends/holidays cannot be inferred from this generic panel. One hundred observations
is only a numerical floor, not evidence of adequate estimation. Revision-vintage rules still apply.

GARCH does not identify new economic causes, forecast directional alpha, change betas or prove Gaussian
tails. Leverage asymmetry (GJR/EGARCH), changing correlations (DCC), refitted rolling evaluation and trading
cost-aware sizing remain later comparisons. The existing synthetic fixture has constant-variance shocks;
it is an engineering/control case where GARCH need not outperform simpler estimates.

Reference: [arch GARCH and forecasting documentation](https://arch.readthedocs.io/en/latest/univariate/forecasting.html).

## Verified warehouse inventory

See [the Snowflake audit](audit/README.md) for live coverage, availability and reconciliation checks,
read-only SQL and workflow receipts. Raw ingestion is not yet a validated factor input panel.
