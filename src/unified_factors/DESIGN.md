# Design and implementation decisions

Owner: aidanq06. Research implementation, 2026-10-03. Read README.md for commands, RESEARCH.md for
hypotheses and references, INTERFACE.md for future integration contracts, VALIDATION.md for test status.

## Purpose and boundaries

The delivery-gap strategy needs to distinguish an intended economic exposure from incidental market,
style, sector and other shared risks. This component establishes common units, clocks, factor identity,
exposure estimation and risk accounting. It does not assert that a regression can discover every cause,
classify every risk permanently as diversifiable, or establish a profitable trading rule.

There are three different questions:

1. Representation: which measured factors describe an asset's returns, with what estimated loadings?
2. Risk: how do those exposures and their covariances contribute to this portfolio's variance?
3. Action: which exposures could available hedges span, and under what trading constraints?

The first two have numerical implementations. The third currently has only an unconstrained geometric
diagnostic. Live hedge construction, cost estimates, risk limits and execution are outside this version.

## Component map

| File | Responsibility |
|---|---|
| core.py | Factor metadata, panel validation, joint regression, overlap diagnostics, covariance, attribution, hedge span |
| garch.py | Optional two-stage CCC-GARCH fitting and frozen-origin variance forecast comparison |
| run.py | Explicit panel loading, fixed baseline grid, deterministic synthetic fixture, report and artifact export |
| test_core.py | Information-boundary and numerical accounting tests |
| test_garch.py | Forecast, estimator-failure, timing and covariance tests |
| requirements-garch.txt | Optional dependency constraints; no global repository dependency change |

## Data flow and clocks

A panel declares one asset order, currency, observation horizon and immutable source version. Each row
contains realized excess returns and contemporaneous factor observations, plus period-end and latest
availability timestamps. There is no implicit imputation, currency conversion or risk-free subtraction.
A producer must supply these consistently and preserve revision vintages; schema checks cannot prove
historical truth or licensing rights.

For training at cutoff T, ordinary regression admits a row only if both timestamps are no later than T.
GARCH requires the entire historical prefix to be available. Removing a delayed row would otherwise
pretend adjacent retained observations were consecutive volatility steps. Upstream must also verify the
session calendar: this generic schema cannot distinguish a holiday from an omitted trading session.

The evaluation panel must follow T. Ordinary factor evaluation uses subsequently realized factors and
is explicitly descriptive return attribution. GARCH comparison instead forecasts variance at T without
reading future factors or returns; future realized returns are used only to score those forecasts.
The CLI admits synthetic/development roles only. This is an accidental-use guard, not access control.

## Return representation and overlap

For each asset, excess return = intercept + factor vector times loadings + residual. Fit all requested
factors together with standardized OLS; return coefficients in original factor units. Separate univariate
fits would allocate correlated effects repeatedly. Exact rank deficiency is rejected; high condition
numbers, VIFs and pair correlations remain visible. Canonical aliases cannot be counted twice.

The fixed grid is CAPM, FF3, Carhart4, FF5 and FF5 plus momentum. One shared SMB column creates nested
specifications, not exact replication of the different published FF3/FF5 SMB definitions. Comparisons
requiring exact replication need separately defined, pinned panels. No evaluation winner is selected.

No regularization, orthogonalization or Bayesian prior is used to fabricate identification. Different
factor bases can redistribute named contributions while representing the same total portfolio risk.
Intercepts are fitted means, not evidence of tradable alpha. Residuals remain unexplained, not proven
idiosyncratic or independent. A future residual PCA layer must not assign economic names automatically.

## Covariance and reconciled attribution

Let B be factors-by-assets loadings and w signed portfolio NAV weights. Define v = [B w, w] and C as
joint covariance of [factor observations, asset residuals]. Portfolio variance is v' C v. Component j
contributes v[j] * (C v)[j]. Contributions sum to total variance and may be negative for hedging positions.
Each covariance cross term is allocated symmetrically; this is an accounting convention, not causality.

Full residual and factor/residual covariance is retained. It is particularly important with weighted
covariance: OLS residual orthogonality under unweighted estimation need not survive EWMA weighting.
Sample and centered EWMA covariance support fixed diagonal shrinkage. Shrinkage changes estimated risk,
so exact reconstruction of raw sample variance is asserted only for the unshrunk corresponding estimator.
No automatic annualization or tail-probability interpretation is made.

## GARCH design

The optional implementation uses arch 7.2 Gaussian quasi-maximum likelihood. After the training regression,
center factor observations by their training means and use each asset's training residuals. Each component
is scaled by its root mean square for numerical fitting, then omega and variance forecasts are converted
back to original squared units. Fit h[t+1] = omega + alpha e[t]^2 + beta h[t].

Require successful optimizer termination, positive omega, nonnegative alpha/beta and persistence below
one. Reject invalid/nonstationary components without a fallback; the CLI reports rejected specifications.
Near-boundary accepted fits are flagged. One hundred training observations is a numerical guard only.

Estimate R from standardized training innovations and shrink it 5% toward identity. Forecast joint
covariance as D[h] R D[h], preserving positive semidefiniteness and cross-component dependence. Means,
loadings and R remain fixed. This is a two-stage constant-conditional-correlation construction, not joint
multivariate likelihood or DCC. Gaussian QML does not justify Gaussian tail forecasts.

For horizon h > 1, expected component variance follows omega + (alpha + beta) times the previous forecast.
These are individual future-period marginal covariances, not cumulative holding-period variance. No
future realized data enters recursive forecasts. Sample/EWMA comparators keep their training estimates
fixed over the same evaluation periods. Score portfolio innovations around their training mean with
QLIKE, squared-variance-error MSE and aggregate realized/forecast variance ratio. Fixed weights are
required. Long single-origin comparisons can favor stable estimates; rolling refit evaluation remains
future work and must obey observation/publication clocks.

## Artifacts and reproducibility

The CLI creates a new directory; it never overwrites an existing run. report.json records the input hash
(or synthetic seed/version), source hashes, cutoff, factor metadata, weights, estimator settings, runtime
versions, model diagnostics and output hashes. exposures.csv contains per-asset loadings. Baseline NPZ
files contain means/loadings/covariance and identifier arrays. Optional GARCH NPZ files contain parameters,
next component variances, correlation and period-indexed portfolio forecast comparisons. No pickle needed.

Artifacts are research outputs; the repository ignores numerical NPZ files. Any eventual number quoted
in the competition note must follow the existing results/ ownership and evidence conventions. A saved
artifact is not a production model-loading API. Package constraints are not a complete environment lock;
reported runtime versions identify the tested environment.

## Acceptance and next work

Tests cover sample/EWMA reconstruction, negative contributions, retained residual correlations, future
mutation isolation, publication lag, factor alias/rank failure, schema changes, sealed-role refusal,
hedge span, GARCH library agreement, stationarity/mean reversion and optimizer failure. The synthetic
fixture deliberately has constant-variance shocks; success means correct operation, not financial edge.

Next: authorize a pinned development panel, validate calendars/vintages, compare stable exposure and
risk estimates, then introduce rolling evaluation and uncertainty intervals. Macro/mechanism factors
need explicit economic definitions and exposure evidence. DCC, asymmetric GARCH, changing betas,
nonlinear repricing and constrained hedging each need separate baselines and acceptance criteria.
No quantum, Jev, warehouse or HiPerGator dependency is needed to run this component.
