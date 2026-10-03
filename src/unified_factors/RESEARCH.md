# Unified exposure model: hypotheses before measurement

2026-10-03. Owner aidanq06. Proposed research direction, not a change to the strategy or frozen holdouts.

## What "unified" should mean

One identity, time, units and attribution system across model families. It does not mean a single regression
that can name every source of risk. Several observationally equivalent models can fit the same returns;
perfectly correlated causes cannot be separated by adding compute. Report unresolved equivalence classes.

Distinguish systematic from systemic: broad common return risk is not identical to propagation of distress
through counterparties, funding and collateral. Both can matter. Distinguish diversifiability from hedging:
adding independent positions can reduce concentration, while a short hedge can offset a common exposure.
Neither makes liquidity, leverage limits or basis risk disappear.

## Model ladder and the overlaps each addresses

| Layer | Starting model | What it identifies | Main overlap/failure | Promotion gate |
|---|---|---|---|---|
| Market | CAPM | broad equity beta | sector/style omitted | baseline only |
| Equity styles | FF3, Carhart4, FF5, FF5+MOM | familiar return covariation | correlated definitions; SMB differs across published sets | frozen-window incremental attribution |
| Sector/country/currency | constrained industry/country exposures plus FX | shared geographical and business sensitivity | market and full dummy sets collinear | explicit reference/constraints and valuation currency |
| Macro | rate-curve changes, credit spreads, commodity shocks | financing/input-cost sensitivity | endogenous prices; same shock appears in multiple series | predeclared channel, units, stability |
| Mechanism | pre-event contract exposure x new surprise | differential economic burden/benefit | mediator double counting, reverse causality | documents, falsifier, matched comparison |
| Statistical residual | PCA on training residuals | unmodeled common directions | rotations/signs are arbitrary; no economic name guaranteed | stable loadings, new-window risk improvement |
| Conditional dynamics | EWMA, then GARCH/GJR and DCC; rolling/Kalman beta | evolving variance/correlation/exposure | each solves a different problem | calibration and economic benefit over simple baseline |
| Nonlinear/tail | full repricing, delta/gamma/vega where appropriate, stress/copula models | convexity, jumps, joint distress | linear covariance misses tails and funding constraints | scenario consistency and tail validation |

Current code implements the first two layers, static/EWMA joint-risk accounting and optional two-stage
CCC-GARCH(1,1). GARCH forecasts component variances with fixed standardized-innovation correlations. Sector and mechanism
factors can use the generic fit API only after being explicitly constructed; there is no auto-discovery.
The full global system requires those additional layers, appropriate instruments and currencies, and evidence.

## Research hypotheses

H1: Signed contractual exposure times a newly public delay surprise explains cross-sectional differences in
subsequent outcomes beyond industry/style controls. Existing contract terms determine who absorbs costs,
whether costs pass through, and whether revenue is deferred or lost. Reject if pre-event exposure adds no
stable predictive information after costs, or matched non-exposed firms behave the same. Contractual sign
is unknown unless supported by documents; a supplier is not automatically a winner.

H2: Delays to substitutable new supply benefit available existing capacity. Test only within comparable
location/product/service specifications and with an executable instrument. Reject if fixed-composition price
changes, utilization or margins do not support the proposed effect. AWS listed instance prices are not rental
transaction prices, GPU-hour prices or tradable futures. Near-zero correlation does not establish independence.

H3: After named equity factors, correlated residual risk remains among exposed firms. Test its stability and
portfolio impact. This can justify an additional risk control without claiming alpha. Reject a proposed
economic label if residual structure does not localize to the declared channel or cannot survive new windows.

H4: A conditional risk estimator improves realized risk calibration or hedge error net of turnover relative
to sample/shrinkage/EWMA baselines. GARCH on residuals alone is not total risk. Do not use tomorrow's realized
factor returns in a forecast or interpret contemporaneous attribution as predictive success.

H5: A strategy can retain its intentional mechanism exposure while reducing incidental market/sector/style
risk. Compare predeclared hedge policies under liquidity, borrow and financing costs. Failure to improve the
chosen risk/return objective rejects the policy, not necessarily the underlying signal. No automatic all-factor
neutralization: it can remove the desired economics or produce excessive gross exposure.

## Accounting overlap without claiming causality

Jointly fit exposures instead of adding separate univariate betas. Preserve full factor covariance and
residual covariance. Standardized condition number and VIF disclose unstable attribution. Exact duplicate
representations fail validation. Ridge can stabilize predictions but cannot uniquely identify economic causes.

Euler variance allocation splits cross terms symmetrically and reconciles totals. It is an allocation rule,
not a unique decomposition of causal responsibility. Incremental family tests remove the entire family,
including its interactions; use fixed baseline controls. If factors mediate one another, predeclare whether
the estimand is a total or direct effect. Mechanical orthogonalization is order-dependent and must not quietly
rename the residualized series as the original factor. Shapley attribution is a possible sensitivity view,
not identification and not part of this implementation.

Residual PCA remains unlabeled until corroborated. Omitted common factors are not idiosyncratic simply because
the first regression missed them. Model uncertainty, bad identity matches, stale observations and unobserved
events remain explicit limitations rather than invented additive factors.

## Data and validation

Begin with an authorized daily equity development panel and compatible published factor vintages. Long-run
standard-factor histories validate the risk layer, not a 20-year compute strategy. No OOS window is selected
or opened here. Compare all five baselines; no silent model selection on their evaluation results. Next add
rolling origin evaluation, blocked uncertainty intervals, predeclared model variants and a final untouched
test under the team's existing ownership rules.

No automatic currency conversion: later adapters must convert asset P&L and FX translation consistently
before adding FX hedges. No universal common factor set across equities, rates, compute products and perps.
Perps add underlying beta, basis, funding and liquidation/liquidity exposures; options add nonlinear repricing.
Factors need not be investable, but a theoretical factor portfolio is not automatically an available hedge.

Use project/firm/time or shock-aware inference as warranted. More daily rows do not create more independent
monthly shocks. Sparse project histories require interval-censoring and competing-risk treatment; no-observation
months must not automatically become confirmed survival months. Generator queues do not measure data-center
load interconnection; geography alone does not prove contractual or electrical exposure.

## Current repo audit boundaries

Reviewed main through 1abd6bc; the subsequent sync added two planning maps. The Stage A negative results are
provisional for this branch because calendar shifting returns the wrong month, imputation precedes the split,
controls retain exposure interactions, row bootstrap ignores dependence and within-month permutation cannot
shuffle nationally constant factors. GSCPI was introduced in 2022; reconstructed earlier values are explanatory
history, not demonstrated historical availability. Fixing these issues does not guarantee positive results.
The parent's truth ledger is not silently rewritten by this work; corrections belong with its owner.

## Primary research and documentation

- [French factor definitions](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_5_factors_2x3.html)
  and [data vintages](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html): benchmark construction,
  availability and the 2025 CRSP format change. Published SMB differs across FF3 and FF5 constructions.
- [Chamberlain and Rothschild](https://www.nber.org/papers/w0996): approximate factor structure and diversification.
- [Ledoit and Wolf](https://ledoit.net/honey_abstract.htm): covariance estimation error and shrinkage.
- [Engle DCC](https://archivefda.dlib.nyu.edu/handle/2451/26879): conditional correlations distinct from univariate variance.
- [Cohen and Frazzini](https://pages.stern.nyu.edu/~afrazzin/pdf/Economic%20Links%20and%20Predictable%20Returns%20-%20Cohen%20and%20Frazzini.pdf):
  economic links motivate an information-transmission hypothesis, not a guaranteed modern edge.
- [Petersen](https://www.nber.org/papers/w11280): dependence in finance panels.
- [Borusyak, Hull and Jaravel](https://www.nber.org/papers/w24997): shared shocks and differential exposures require
  shock-aware identification and inference; exposure interactions are not automatically causal instruments.
- [NY Fed GSCPI launch](https://www.newyorkfed.org/newsevents/news/research/2022/20220518): first introduced January 2022.
- [Berkeley Lab queue scope](https://eta.lbl.gov/publications/queued-2026-edition-characteristics): generation queues
  exclude load-interconnection requests.

These sources motivate a model ladder. They do not validate this strategy, live access or the synthetic demo.
