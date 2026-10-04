# Pricing the Buildout

A revenue-confirmed investment-intensity strategy in the AI-capex equity complex.

Gator Quant Hacks 2026, Systematic Trading track.

Capital spending is a promise; revenue is the receipt. This note prices the gap between them.

SECTION 01

SUMMARY

We test one question. Does the market price the size of a company's spending, when what determines the return on that spending is the revenue it produces?

The setting is the AI buildout: 55 issuers in six peer groups, all paid by the same capital cycle, from hyperscalers and compute hardware to data-center landlords, contractors, power, and fuel.

The signal is the year-over-year change in investment intensity, which is capital expenditure divided by revenue, ranked inside each peer group. The expression buys the names that became more capital-light and shorts the names that became more capital-heavy.

Investment intensity has no reliable sign on its own, and our own estimate says so. A company that spends more per dollar of revenue may be building capacity for demand it can already see, or it may be spending into demand that has not arrived. Both cases look identical in the announcement, and intensity alone is not priced in our sample: its controlled coefficient is +0.0061 with a t statistic of 0.65.

The revenue report separates the two cases, because it records whether the demand the spending implied actually showed up. We use it as the interpretation of the signal rather than as a filter on top of it. A long survives only when revenue met or beat its seasonal expectation; a short survives only when revenue fell short.

That separation is the whole result. Over the same window and the same cohorts, the ungated expression loses 9.49 percent a year and the confirmed expression earns 10.48 percent net. The month-blocked interval for the difference runs from +7.75 to +35.30 percentage points annualized, and it is positive in 99.9 percent of resamples.

Two findings argue against us, and they come first because they shape how the rest should be read.

The strategy does not beat holding the complex. An equal-weight long basket of the same names returns +33.77 percent a year at Sharpe 1.339 between 2021 and 2026, before costs. Our portfolio returns +10.23 percent at Sharpe 0.931 over the same window. Its case is not return: it is a third of the drawdown, a 0.21 beta to the basket, and a dollar-neutral book that does not need the theme to keep working.

Our best number is a number we threw away. A rule that holds the book only while the complex trades within five percent of its peak reports Sharpe 1.793, and the honest walk-forward chose it in all six evaluation years. It reads the same session's close as the return it scales. Lag the state by one session and its Sharpe falls to 0.655 against 0.931 unconditioned. We report it rejected in Section 06.

Every result below is net of costs and is development evidence. The gate window is out-of-sample relative to the frozen revenue-surprise model, but it is not an untouched holdout. The official forward window is armed with zero scored observations, so no fresh official holdout has been scored.

Table 1. Headline net results (development only)

| Result | Window | Return | Vol. | Sharpe | Max DD |
|---|---|---:|---:|---:|---:|
| Ungated intensity | 2023-07-28 to 2026-10-02 | -9.49% | 10.49% | -0.904 | -38.0% |
| Revenue-confirmed intensity | same | +10.48% | 10.79% | 0.971 | -16.3% |
| Revenue-confirmed, doubled costs | same | +9.96% | 10.80% | 0.922 | -16.3% |
| Preferred portfolio, rolling origin | 2019-02-01 to 2026-10-02 | +11.95% | 10.86% | 1.100 | -15.1% |

Annualized, net of costs. The preferred portfolio holds the revenue sleeve and the gated-intensity sleeve at a ten percent volatility target. Sources: results/intensity-gate-test.json, results/culmination.json.

[FIGURE 1 PLACEHOLDER: Summary of the strategy, the confirmation gate, and net development results.]

SECTION 02

ECONOMIC HYPOTHESIS

Capital spending is a claim about the future. A company that raises intensity is telling shareholders that it has demand worth building for, and the claim is credible precisely because the money is already committed. The market reads commitment as evidence, which is usually right and occasionally expensive.

The occasion for error is a buildout. When every firm in a complex is spending at once, the spending itself becomes the story, and the story is easier to price than the revenue conversion behind it. A rise in intensity can mean a company is buying capacity for demand it can already see. It can also mean capital is being consumed faster than revenue is arriving. Those two cases carry opposite signs, and they are indistinguishable at the announcement.

The revenue report resolves the ambiguity, and it arrives on its own schedule. It says whether the demand the spending implied was real. We do not predict that report; we require the signal and the report to agree before we hold a position. Where they agree, the repricing continues over the following weeks. Where they disagree, we stand aside.

That is the entire edge, and it is a claim about mispricing rather than about forecasting.

Who is on the other side. The candidate counterparty is the investor who treats committed capital as sufficient evidence of future revenue, which is the natural reading during a buildout. He is not irrational. He is pricing the announcement instead of re-deriving the expectation the announcement should be judged against, and he pays the difference when revenue fails to confirm the spending. The rival reading is a risk premium: the book is small, concentrated, and short-heavy, and a holder of that risk deserves compensation. We cannot separate the two with the data we have, and we say so.

Why the gap can survive. Three frictions, all measured or directly observable, keep the comparison from being free.

The expectation a filing should be judged against is not published. The signal needs a same-quarter seasonal surprise at filing time, and the written filing history is the only place to rebuild it.

The two facts arrive together, but the baseline does not. Capex and revenue sit in the same quarterly report, so a reader cannot see the pair without having already constructed the historical seasonality.

The short leg is small and hard. A confirmed cohort holds a median of five names, capacity is single-digit millions (Section 07), and borrow is unchecked. A large fund cannot make this bet matter, and a small one pays wide spreads for it.

What we measured, and what we only infer. Measured: intensity alone is not priced, coefficient +0.0061 with a t statistic of 0.65 after sector, revenue growth, asset growth, operating margin, and the common investment factor. Measured: confirming each leg with the revenue expectation flips the expression from -9.49 percent to +10.48 percent net. Inferred: the identity and the motives of the counterparty. We have not measured a forced payer and we have not seen order-level flow. The mechanism is an interpretation of a measured return difference, not an observation of who paid it.

Falsifiers, declared before the forward window opened. A composite that nets zero or less over the window. A Sharpe at or below 0.5. A maximum drawdown beyond twenty percent. A capex hedge that turns positive and significant, which would contradict the sign story that gives the gate its meaning. A snapshot whose predictions change after the fact, which would void the window.

[FIGURE 2 PLACEHOLDER: Economic mechanism from expectation to filing to portfolio repricing.]

SECTION 03

DATA & UNIVERSE

Universe. 55 issuers in six declared peer groups: hyperscalers, compute and AI hardware, data-center REITs, buildout contractors and electrical equipment, power, and fuel and nuclear. The register is our own declaration, fixed before the tests below ran.

Fundamentals and clock. Quarterly capex and revenue come from SEC XBRL company-concept records. We date a fact from its earliest filing occurrence, a median of 34 days after period end for capex and 36 days for revenue.

The first version of this panel used the latest filing instead, usually a later comparative, with a median lag near 401 days. That clock made the strategy look better than it was: the base configuration read +2.94 percent net, Sharpe 0.347, drawdown -22.9 percent. On the corrected clock the same configuration reads -4.89 percent net, Sharpe -0.630, drawdown -48.0 percent. Every number in this note uses the corrected clock, and the correction is the reason we no longer treat standalone intensity as an edge.

Prices. Daily adjusted closes and dollar volume come from the cached yfinance panel. Corporate actions enter only through the vendor's adjustment, so a split or a dividend is handled as the vendor handled it.

Windows. The gate test runs from 2023-07-28, the point where the frozen surprise model can be scored, to 2026-10-02: 804 sessions and 97 confirmed cohorts. The rolling-origin study runs from 2019-02-01 to 2026-10-02 over 1,862 sessions and eight annual refits.

Validity and missing data. A signal expires 180 days after its filing. A name without a price on a session is skipped for that session. A missing revenue expectation never confirms a leg, so the gated book holds less exposure than the ungated one by construction rather than by choice. Costs and capacity use the prior month's dollar volume.

Survivorship. The universe is today's register. Delisted names are absent, we did not rebuild a point-in-time security universe, and we do not know the size of the bias. This limits the result to the names as they exist now.

[FIGURE 3 PLACEHOLDER: Universe composition and point-in-time information clock.]

SECTION 04

METHODOLOGY

investment_intensity = capital_expenditure / revenue

intensity_change     = log(current_intensity) - log(intensity_four_quarters_ago)

Ranking and legs. Each peer group ranks its members on intensity change, then buys the bottom third and shorts the top third at equal weight. Every group carries equal gross, so the book is dollar and group neutral and no single group can dominate the others.

Revenue confirmation. We take the expected revenue change for a quarter as the mean of the issuer's own prior same-quarter changes. A model fitted on the first seventy percent of the history assigns each filing to an expected-surprise bin. A long is kept only at or above expectation, a short only below it.

Cohorts and timing. A cohort opens on the first session strictly after a new filing and holds for twenty sessions. The signal is therefore always older than the fill, which is what a reader of filings could actually have done.

Costs. The driver sleeves pay twenty basis points round trip. The intensity engine pays 5, 10, 20, or 40 basis points per side according to the name's prior-month volume bucket. The doubled-cost run doubles both and is reported beside the base case in Table 1 and Table 2.

What is frozen. The portfolio recipe, the horizon, and the gate are fixed. Model parameters are refitted only on data available before each origin, and their digests are recorded in the artifacts.

What we rejected, and why it stays in the record. The declared intensity grid varies horizon, quantile, weighting, neutrality, and cost multiplier. We report the frozen base specification, the revenue-confirmation gate, the doubled-cost run, the capex-confirmation variant, and the vol-targeted variant. The capex condition returns -7.25 percent net with an interval of -31.71 to -2.99 points annualized and is rejected, not deleted. A rejected line with a number attached is worth more than a silent shelf.

Known gap. We have not stored a normalized annual turnover series. We know the cohort count, the twenty-session hold, and a median gated entry cost of 2.08 basis points, but an honest turnover figure is still owed.

[FIGURE 4 PLACEHOLDER: Filing timestamp to signal, first eligible fill, holding period, and exit.]

SECTION 05

RESULTS

All returns are net of the costs in Section 04. We sort the evidence by how much the models knew when they produced it, because that is the only distinction that matters for a claim.

In-sample training evidence. The revenue sleeve earns +16.50 percent at Sharpe 0.490 on the 1,197 training events, with a -57.0 percent drawdown. We treat this as a stability diagnostic. It is not a portfolio result and it is not evidence of anything out of sample.

Model-OOS development evidence. On the thirty percent of the driver history the revenue model never saw, the gate changes the intensity expression from -9.49 percent net at Sharpe -0.904 to +10.48 percent at Sharpe 0.971, and +9.96 percent at doubled costs (Table 1). The difference between gated and ungated is +21.44 points annualized, with a month-blocked interval of +7.75 to +35.30 and positive mass in 99.9 percent of resamples over forty month-blocks. The capex condition added to the same gate returns -7.25 percent and is rejected.

Rolling-origin development evidence. Models are refitted at each of eight annual origins and scored only on the following block, at base costs. The preferred portfolio earns +11.95 percent at Sharpe 1.100 with a -15.1 percent drawdown over 1,862 sessions. Its Sharpe is 0.847 across 2019 to 2022 and 1.345 across 2023 to 2026, so the recent era carries more of the result than we would like, and we would rather say that than let a reader find it. On the shorter 1,492-session calendar shared with the retired capex sleeve, and without the volatility target, the same pair reports Sharpe 1.493.

Fresh official forward evidence. None exists. The window opened with zero scored observations, it closes when 250 scored events accumulate or twelve months elapse, whichever comes first, and it is scored once at the end. It is the only instrument in this project that can produce a new claim.

The naive rival, stated plainly. An equal-weight long basket of the complex returns +33.77 percent a year at Sharpe 1.339 with a -27.8 percent drawdown from 2021-01-05 to 2026-10-02, before costs. The preferred portfolio returns +10.23 percent at Sharpe 0.931 with a -15.1 percent drawdown over the same window. Our portfolio does not beat owning the complex on return, and it does not beat it on Sharpe. Its defense is lower volatility, a smaller drawdown, and a 0.21 beta to the basket, which is what a dollar-neutral book should deliver and all we claim it delivers.

Table 2. Net results by evidence class (development only)

| Evidence class and portfolio | Sample | Return | Vol. | Sharpe | Max DD |
|---|---|---:|---:|---:|---:|
| In-sample: revenue sleeve* | 1,197 events | +16.50% | 33.66% | 0.490 | -57.0% |
| Model-OOS: revenue sleeve* | 506 events | +35.94% | 51.08% | 0.704 | -65.1% |
| Rolling origin: revenue sleeve | 1,869 sessions | +27.65% | 36.56% | 0.756 | -58.1% |
| Rolling origin: gated intensity | 1,946 sessions | +6.49% | 7.82% | 0.830 | -10.7% |
| Rolling origin: preferred | 1,862 sessions | +11.95% | 10.86% | 1.100 | -15.1% |

* Driver diagnostic, not the preferred portfolio. Sources: results/sleeve-portfolio.json, results/walk-forward.json, results/culmination.json.

[FIGURE 5 PLACEHOLDER: Cumulative net equity curve for the preferred rolling-origin portfolio, with origin boundaries.]

SECTION 06

RISK MANAGEMENT

Construction. Each sleeve is normalized to one unit of gross with equal-weight legs, dollar neutrality, and group neutrality, then the sleeves are blended by inverse volatility to a ten percent target.

Entry controls. A leg needs revenue confirmation. Stale signals and names without a price are dropped. Volume sets the cost bucket. Borrow is not checked, which is a defect we name here and carry into Section 07.

De-risking. There is no price stop. A stop would add a tuned parameter to a strategy whose whole claim is that the signal and the report must agree, and a fitting win would replace a stated mechanism with a searched one. The portfolio rule is the declared falsifier instead: a forward drawdown beyond twenty percent ends the claim.

Factor exposure. The portfolio's beta to the equal-weight complex basket is 0.21 with a correlation of 0.52. We have not measured betas to the broad market or to style factors, and the Section 02 regression controls only the common investment factor. A reader should treat the factor story as partially open rather than as settled.

Correlation and tails. Daily sleeve correlations are +0.481 between revenue and gated intensity, -0.218 between capex and gated intensity, and -0.261 between revenue and capex. Diversification between the retained sleeves is therefore partial, and a complex-wide shock can hit both legs at once. A confirmed cohort holds a median of five names, so single-name risk inside a cohort is concentrated.

Regime risk, and the rule we killed. No regime rule is in the headline strategy, and the reason is a test rather than a taste. We swept six point-in-time definitions of the complex state (basket volatility, basket trend, basket drawdown, VIX, term spread, and the infrastructure phase) across 156 exposure maps, each map assigning a multiplier to a low, mid, or high state.

One rule won consistently. The honest walk-forward, refitting on earlier data only, chose the same definition and the same map in every one of the six evaluation years: full exposure while the complex trades within five percent of its running peak, zero otherwise. It reports Sharpe 1.793 with a -5.3 percent drawdown, and it is the only candidate in this programme to beat the naive basket on both Sharpe and drawdown.

Then we tested the timing convention, and the rule died. Its state is read from the same session's close as the return it scales. That is look-ahead, and it flatters the rule by exactly the amount a fast drawdown signal would. Lag the state by one session and recompute from the committed daily ledgers, and the Sharpe falls from 1.793 to 0.655 against 0.931 unconditioned. The conditioned-minus-unconditioned difference is +0.028 with an interval of -0.028 to +0.084, positive in 82.8 percent of resamples, so the return gain was never established either.

Table 3. The regime rule under two timing conventions (development only)

| Rule | Sharpe | Max DD |
|---|---:|---:|
| Conditioned, as committed (same-session state) | 1.793 | -5.3% |
| Conditioned, state lagged one session | 0.655 | -10.6% |
| Unconditioned headline | 0.931 | -15.1% |

Addendum. Version 1 of the phase machine uses full-history thresholds, so it describes history rather than dating states in real time, and we do not use it for sizing. As an overlay it also lowered second-half Sharpe from 1.698 to 1.563, an annualized difference of -2.55 points with an interval of -5.48 to -0.22.

[FIGURE 6 PLACEHOLDER: Factor exposure budget, and the regime rule before and after the timing correction.]

SECTION 07

LIQUIDITY & CAPACITY

Costs. Driver sleeves pay twenty basis points round trip. The intensity engine pays 5, 10, 20, or 40 basis points per side by volume bucket, and the doubled-cost runs in Table 1 show the gate surviving at twice those charges.

Capacity. We compute capacity from 60-session median dollar volume and a participation limit applied to absolute position weight. Table 4 reports the two-sleeve portfolio at one and five percent of ADV.

Table 4. Capacity of the two-sleeve portfolio (results/capacity-curve.json)

| Portfolio construction | Participation | Median capacity | Tenth percentile |
|---|---:|---:|---:|
| Equal gross two-sleeve | 1% of ADV | $8.15M | $0.93M |
| Inverse-volatility two-sleeve | 1% of ADV | $8.14M | $1.55M |
| Equal gross two-sleeve | 5% of ADV | $40.74M | $4.63M |
| Inverse-volatility two-sleeve | 5% of ADV | $40.71M | $7.77M |

The binding names are small caps: PLUG, APLD, LEU, AGX, PRIM. On a median day the book supports roughly $8M at one percent participation, and between $0.9M and $1.6M on the worst tenth of days. Single-digit millions is the ceiling before the edge erodes.

What this table is not. It is a liquidity screen, not an impact model. We fixed costs per side by volume bucket, and we did not measure spread, nonlinear impact, or borrow. The short leg may be partly unavailable or expensive to hold. Every capacity figure here is an upper bound, and the true figure is lower by an amount we have not estimated.

[FIGURE 7 PLACEHOLDER: Capacity curve at one and five percent of ADV participation.]

SECTION 08

LIMITATIONS & NEXT STEPS

What did not work, and what it cost us. The latest-filed comparative clock, which flattered the strategy until we corrected it. Standalone capex intensity, which does not survive controls. A capex condition stacked on the revenue gate, which loses money. Both regime rules, including the one that looked best, killed by a one-session lag. A reversed capex hedge, which lowered same-window Sharpe from 0.931 to 0.778 and is why the inverse-volatility blend gives that leg little weight. Still missing: normalized turnover, borrow fees, nonlinear impact, and a complete point-in-time security universe.

What could break the strategy. A complex-specific growth regime, including the favorable recent period for AI infrastructure names. A change in filing practice that moves the availability clock. Small-cap spreads and borrow recalls. Revenue and intensity becoming more correlated as the theme matures, which would shrink the disagreement the gate trades. Slower expectation updates, or faster revenue conversion without repricing.

What we would test next. Score the frozen forward window once. Rebuild a point-in-time universe with delisted names and estimate the survivorship bias. Add borrow data, event-level turnover, execution prices, and spread and impact estimates. Test the gate on a disjoint complex and on a matched non-complex universe. Rebuild the regime machine with prefix-invariant thresholds, lag every state by one session, and run same-state null tests. Complete the separate Massive study, which supports nothing in this note.

The evidence statement we are willing to defend. In the declared AI-capex complex, a revenue expectation gate improves the historical development performance of an investment-intensity expression after the disclosure clock is corrected. The evidence does not establish causality, a fresh out-of-sample edge, a market-wide effect, complete short availability, or scalable production capacity.

[FIGURE 8 PLACEHOLDER: Limitations and next-steps map.]

REFERENCES

Outside the five-page body.

Data sources

1. U.S. Securities and Exchange Commission. EDGAR APIs and XBRL Company Facts. https://www.sec.gov/search-filings/edgar-application-programming-interfaces

2. U.S. Securities and Exchange Commission. XBRL company-concept records (/api/xbrl/companyconcept/), used for the earliest-filed availability clock.

3. Yahoo Finance daily closes and volume through yfinance, as cached in the repository (results/bar-cache/, results/universe-adv-monthly.csv).

Repository documents

4. docs/brief.md. Track brief, frozen 2026-10-02.

5. docs/plan/alpha-build.md. Staged build order, rules, and gate-test protocol.

6. docs/plan/forward-window.md. Frozen forward-window protocol and falsifiers.

7. docs/plan/regime-factor-program.md. Factor register and regime acceptance gates.

8. docs/plan/regimes.md. Phase model.

9. docs/truths.md, entries T42 to T53 and T70. Measured findings and their scope.

Result artifacts

10. results/intensity-gate-test.json. Gate test, Table 1 and Section 05.

11. results/walk-forward.json. Rolling-origin sleeves, Table 2, and the 1,492-session figure.

12. results/three-sleeve-portfolio.json. Sleeve correlations in Section 06 (T48).

13. results/sleeve-portfolio.json. Driver diagnostic rows, Table 2.

14. results/capacity-curve.json. Capacity, Table 4.

15. results/regime-overlay.json. Regime seam test, Section 06.

16. results/culmination.json. Preferred portfolio on its full calendar, naive rival, basket beta, hedge and regime sweep.

17. results/culmination-ledgers/. Daily ledgers used for the one-session lag check in Section 06.

APPENDIX A (OPTIONAL): SEPARATE WORK NOT USED IN THIS NOTE

Outside the five-page body. Nothing here supports the equity strategy.

Massive bonus study. A separate study of Massive 8-K event tags and option chains is in progress. It is not complete, and no result from it is reported here.

Model engineering. The JevLike and related training experiments are separate development engineering research. They are not part of this strategy, and no quantum advantage has been measured.
