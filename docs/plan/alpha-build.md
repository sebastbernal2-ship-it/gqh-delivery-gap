# The alpha build: staged, contracted, and gated

Status: development only. Owner: sebas. Date: 2026-10-04. This document is the build order. Each
stage names its deliverable, its acceptance test and its falsifier. A stage that fails is recorded
and stops, never softened.

## 0. The evidence base, and the one thing that went wrong

| Fact | Number | Owner |
|---|---|---|
| Disclosure clocks, checked | RPO 38 days, obligations 55, capex 34, revenue 36 | T42, `docs/plan/intensity-clock-test.md` |
| The old intensity panels | 401-day median lag, so the published edge was a clock artifact | T42 |
| The published intensity expression on the corrected clock | -4.89% net, Sharpe -0.630, drawdown -48% | T42 |
| Revenue surprise, corrected clock | +4.75% per 20-session event, interval +1.13 to +9.28, 55 issuers | T43 |
| Capex surprise, corrected clock | -4.87%, interval -10.51 to -1.34, the sign the thesis expects | T43 |
| RPO surprise | +4.71% neutralised but the interval crosses zero | `results/surprise-alpha.json` |
| Council over two distinct data bundles | beats the best single by 0.055 log loss, interval 0.029 to 0.080 | T39, `results/rpo-market-council.json` |
| Selective decision | 55% accuracy at 7% coverage, break-even utility | `results/decision-layer.json` |
| Coupling layer | exact marginal matching, martingale or proved infeasible | `docs/plan/coupling.md` |
| Risk-track council | code and protocol ready, five whole UTC dates missing | `docs/plan/risk-council.md` |

The failure to avoid repeating: the strategy ran for weeks on a clock that was thirteen months late,
and nothing in the build detected it. The cause was a one-token choice in a fetch script, kept
because the output looked plausible. Detection is now a named stage gate (rule 1 below).

## 1. Rules that make the next failure detectable

1. **Clock rule.** Every dataset publishes its lag distribution (period end to availability). The
   build fails if the median lag is far from the reporting norm for that document type, or if the
   share above 300 days exceeds a declared bound. Tested, not remembered.
2. **Cutoff rule.** Every feature uses data strictly before the decision. Mutate-the-future tests
   pin it, as in the market-state specialist.
3. **Independence rule.** Every evaluation reports distinct events beside row counts, and prefers
   one row per event when labels repeat.
4. **Interval rule.** Every headline number carries an issuer-blocked bootstrap interval.
5. **Cost rule.** Every trade evaluation reports base and doubled costs.
6. **Neutralisation rule.** Every cross-sectional result is reported raw, month neutral, and month
   and group neutral, because the complex moves together.
7. **Falsifier rule.** Each stage declares what would refute it before it runs.
8. **Ownership rule.** Corrections are new files. Another workstream's artifact is never overwritten.
9. **Freshness rule.** Both sealed windows are spent. A performance claim needs a forward window.

## 2. Target arithmetic

Sharpe ≈ IC x sqrt(effective independent events per year), then diversified across sleeves.

- Today: IC 0.04 to 0.08, about 220 events a year at 55 issuers and four quarters, so Sharpe 0.6 to
  1.2 before overlap penalties. The corrected strategy measured -0.63 because its signal was the
  wrong one, not because the mechanism is absent.
- Breadth is the largest lever: 55 to 500 issuers multiplies the event count tenfold and Sharpe by
  about three. The facts are free in XBRL.
- Sleeves: revenue, capex and RPO are the same mechanism on different lines of the income statement.
  Pairwise correlation well below one multiplies effective breadth again.
- Drawdown under 20% at Sharpe 2 needs an 8 to 10% annualised volatility target, selective entry,
  and more than one sleeve. It is a sizing problem, not an alpha problem.

Low latency does not create this alpha. It protects the net: 5 to 20 basis points of entry cost are
1 to 4 points of a 4.75% gross spread, which is why the risk council belongs at the execution step.

## 3. Stages

### Stage 1, now: the gate test on the corrected clock

Deliverable: `scripts/run_intensity_gate_test.py` and `results/intensity-gate-test.json`. The engine
gains one optional argument, a signed gate per (ticker, filing). With `gate_mode="confirm"`, a long
leg keeps only names whose gate is non-negative and a short leg only non-positive names; the default
is unchanged, and an identity test pins that.

Window: the out-of-sample thirty percent only, because the surprise model is frozen from the first
seventy. Acceptance: the gate improves net return at both cost tiers, or it is reported as no
improvement with its interval. Falsifier: the gated net is worse than the ungated net, which ends
the sign-confirmation idea.

### Stage 2: breadth

Deliverable: XBRL facts for at least 300 issuers reporting RPO, backlog or revenue, vintages, panels
and scores. Acceptance: at least 1,000 measured events, at least 200 issuers, median lag inside the
clock rule, and scores beating prevalence out of sample. Falsifier: the larger universe degrades the
per-event edge beyond its interval.

**Stage 3 decision, recorded after the rolling-origin run (T51).** The capex sleeve is
retired from the portfolio: it lost in every era in the walk-forward record, and removing it raised
the composite Sharpe from 1.145 to 1.493. Its event-level sign remains a measured fact (T43) and it is
kept only in the reproduction scripts, never with portfolio weight.

### Stage 3: the multi-sleeve portfolio

Deliverable: one portfolio over the revenue, capex and RPO sleeves with a declared volatility
target, group neutrality, base and doubled costs, and capacity from an expanded volume panel.
Acceptance: net Sharpe and maximum drawdown reported with intervals, plus capacity at one and five
percent participation. Falsifier: the portfolio does not beat the best single sleeve net of costs.

### Stage 4: the fresh window

Deliverable: a frozen protocol, an instrumented daily runner, and one evaluation at the end.
Nothing here can be backfilled; the clock starts when it is declared.

### Stage 5: execution and the JEV layer

Deliverable: the risk cache with five whole dates, the declared council comparison, the coupling
over its twelve marginals, and a measured entry-cost saving on the equity side. Falsifier: the
coupling or the risk council does not beat its classical comparator at matched budget.

### Stage 2b: price coverage, driver breadth, and the scope of the edge

Stage 2 left two gaps: price coverage of 26 percent, and a per-event edge measured only on the RPO
balance. Stage 2b closes both.

1. **Price coverage.** `scripts/fetch_universe_bars.py` fills the daily close and volume cache for
   every broad-universe ticker that lacks one. Acceptance: coverage above 60 percent on the test
   rows, or the shortfall reported with its cause.
2. **Driver breadth.** Revenue and capex for the broad universe, built with the earliest-filed rule
   from `companyconcept`. Acceptance: a panel per concept with at least several hundred issuers, a
   median availability lag inside the clock rule, and scores beating prevalence out of sample.
3. **Scope of the edge.** Every breadth result is reported for complex members and for everyone else
   separately, because the edge may be a complex effect and a market-wide claim would then be false.

Declared falsifier: if the per-event edge on the broad universe is no better than zero once the
complex is removed, then the edge is a complex effect and must be stated as a concentrated strategy
with a capacity limit, not a general one.

A clock finding from this stage, recorded before the results: **XBRL duration frames cannot carry a
point-in-time clock.** The accession attached to a duration frame is frequently a later comparative,
so a frame-built revenue panel has a 403-day median lag and fails the clock rule. Instantaneous
frames (the RPO balance) behaved correctly at 39 days. Any duration concept must therefore be built
from `companyconcept`, which lists every occurrence with its own filing date, and take the earliest.

**Stage 2b outcome, 2026-10-04.** The clock finding was confirmed: duration frames fail the
clock rule and `companyconcept` with the earliest occurrence passes at 36 to 38 days. Price coverage
rose from 26 to 84 percent on the broad RPO panel and 98 percent on the driver panels, and the price
sanity rule (rule 10) flagged 204 split-contaminated series, which were refetched adjusted. The
declared falsifier fired: outside the complex the per-event edge is indistinguishable from zero on
revenue, capex and RPO, while the model's scores beat prevalence on all three. The edge is
complex-specific as measured, so the next stages target depth inside the complex, not breadth.

## 4. What we will not do

1. No quantum claim without an equal-budget classical win, and no QPU dependency.
2. No architecture sweep before breadth; architecture is the second axis.
3. No claim from a panel whose rows repeat the same event.
4. No single-sleeve, unvolumetargeted number presented as a strategy.
5. No borrowed mathematics as decoration. Coupling and optimal transport are in because they were
   needed and tested; number-theoretic structures are not in and will not be.
