# The truth ledger: what we now know about the world

Each entry is a statement about how things work, the evidence behind it, the scope in which it holds, and what it
implies for a strategy. Nothing here is a verdict on the work. It is the state of knowledge, and it is meant to
be added to and corrected, never rewritten.

## T1. Delivery promises are revised constantly, and they are revised late

**Statement**: a promised in-service date on new generation moves more often than it holds. Across 6,407
generators tracked monthly, 69 percent saw a first revision, and 44 percent saw one of two months or more.
**Evidence**: `results/promise-survival.csv`, the survival panel; 27,069 project months, 2,190 revision months.
**Scope**: generation projects in the United States, 2015 to 2022 in the development window.
**Consequence**: the schedule is not a fact, it is an estimate with a distribution. Anything priced off a
schedule inherits that distribution.

## T2. The median revision is noise, and the tail is where information lives

**Statement**: 36 percent of first revisions are a nudge of one month or less; 27 percent are six months or more.
**Evidence**: same panel, revision size distribution.
**Scope**: same.
**Consequence**: a signal built on all revisions is dominated by noise. Any signal must be defined on the tail,
six months or more, or on cancellation. This is a design rule, not a preference.

## T3. A promise is not safer for having survived

**Statement**: the hazard of revision rises with age, from 23 percent in the first six months to 44 percent
between one and two years, then flattens. There is no seasoning effect.
**Evidence**: the hazard table in `docs/decisions.md` and the survival panel.
**Scope**: same.
**Consequence**: waiting does not de-risk a schedule. It accumulates exposure.

## T4. Between snapshots, movement accumulates in whole-year steps

**Statement**: across annual vintages, the modal revision is exactly twelve months, and 64 percent of promised
generators ran late, median two months, worst eighty-three.
**Evidence**: `results/delivery-revisions.csv`, `results/delivery-realizations.csv`.
**Scope**: nine annual vintages, 2015 to 2023.
**Consequence**: slippage is not gradual drift, it is re-planning a year at a time. A model that assumes smooth
decay is wrong.

## T5. Information about a firm's own commitments takes a month or three to become public

**Statement**: the lag from period end to public availability is a median of 33 to 94 days depending on the
field: 33 for equipment orders, 56 for remaining obligations, 94 for disputed change orders.
**Evidence**: `results/obligation-panel.csv`, joined on filing acceptance timestamps.
**Scope**: SEC filings, 2015 to 2024.
**Consequence**: this family of information cannot be a speed edge. Speed belongs to the markets with continuous
data, not to quarterly disclosure.

## T6. Most slipped capacity belongs to nobody we can hold

**Statement**: of 274,176 MW of slipped capacity across 1,070 entities, only 6.2 percent sits with an entity
whose name carries a large listed owner, and 80 percent sits in project and holding companies.
**Evidence**: `results/exposure-panel.csv`, `results/delivery-revisions.csv`.
**Scope**: EIA entity names against SEC registrant names.
**Consequence**: a project level event has no clean equity expression. Attribution must come from documents that
name parties, or the event must be expressed through something other than equity.

## T7. The crowded expression is efficient

**Statement**: the disclosing firm's own equity shows no association with its obligation revisions at horizons
of one to twenty sessions, and shuffled dates produce more nominally significant cells than real ones.
**Evidence**: `results/group-event-study.csv` against `results/group-event-placebo.csv`; 382 firms, 4,634 events.
**Scope**: US filers reporting remaining performance obligations.
**Consequence**: do not spend more time on the obvious expression. The edge, if it exists, is either in an
uncovered subset of names or in a different instrument.

## T8. Compute rental is not one market

**Statement**: across ten GPU families and 5,423 family days, the median pairwise correlation of daily price
changes is minus 0.01. Compute is ten markets with separate inventories, each moving on its own.
**Evidence**: the AWS spot archive in TigerData, queried by family and day.
**Scope**: two regions, 2022-06 to 2024-03, provider-listed spot prices per instance hour.
**Consequence**: relative value across families is conceptually available, and the obstruction is the
instrument, not the signal. It also means an aggregate compute index hides the structure that matters.

## T9. The compute price is a policy, not a clearing price

**Statement**: the archive is provider-listed spot pricing per instance hour, not executed transactions between
strangers, and it is per instance rather than per accelerator.
**Evidence**: the archive documentation and the price levels, p5 at roughly seventy dollars per instance hour
against p4d at eleven.
**Scope**: same.
**Consequence**: any compute signal is a read on provider behaviour under inventory conditions, which is
tradable only through providers, owners or contracts.

## T10. Supply chain and construction pressure do not show up in project delivery

**Statement**: with technology, size, age and calendar accounted for, construction spending, supply chain
pressure and delivery times do not move the chance that a promise is revised. Three factor sets were tested and
all three failed, with the exposure design giving interactions within a rounding error of one.
**Evidence**: `docs/plan/stage-a-report.md`, `results/delivery-model-*.csv`.
**Scope**: US generation projects, market wide factors lagged two months.
**Consequence**: delivery is close to unpredictable from public aggregates. The drivers are project, contract and
queue specific. Do not build on this link.

## T11. The gate is the queue, and it is not in our data

**Statement**: whether a project can get an interconnection position, and how long it waits, is the binding
constraint on energising capacity, and it is not reachable from this host.
**Evidence**: the source audit in `docs/inbox/data-request-queue-2026-10-03.md`; 403 from the national lab,
scripted operator tables, no usable DOE file.
**Scope**: our access, not the world.
**Consequence**: the single highest value data acquisition available to us. Everything else on delivery is
indirect until this exists.

**Update, 2026-10-04.** The data exists and is now in hand. LBNL's Queued Up workbook is public: 36,441 U.S.
queue projects with request, agreement, withdrawal and operation dates, built into `results/queue-panel.csv`
and summarized in `results/queue-summary.json`. 57.4 percent were withdrawn and 12.2 percent reached
operation; the median wait is 664 days from request to interconnection agreement and 1,268 days from request
to operation. The statement above was true of our access on 2026-10-03 and is corrected here. The remaining
constraint is the crosswalk from queue projects to listed firms, not the queue data itself.

## T12. The mechanism has never been turned into a priced signal

**Statement**: four broad searches have produced no survivor that belongs to the mechanism: the pair scan in
two windows, the firm level event study across 382 companies, the aggregate capacity strategy, and the factor
models of delivery. Every survivor dissolved under the family correction, the specificity test or the control.
**Evidence**: `docs/variants.md`, `docs/plan/stage-a-report.md`.
**Scope**: everything tested so far, with its multiplicity accounted.
**Consequence**: the mechanism is real and the expression is unsolved. That is the standing problem, and it is a
problem of *linkage and instrument*, not of more data volume.

## T13. Speed is a licence in some markets and irrelevant in others

**Statement**: our delivery chain has a monthly clock and a month long disclosure lag, so speed cannot be its
edge. The continuous markets we can reach are the perpetual book, funding and open interest on the venue, and the
compute spot archive.
**Evidence**: T5, and the pre-registered cascade protocol with a running tape.
**Scope**: our reachable venues.
**Consequence**: put the fast engine where the data is fast, and the slow analytical engine where the data is
slow. One engine for everything will be pointed at the wrong clock half the time.

## T14. The tail and the exits are structured, and the structure is intrinsic to the project

**Statement**: with technology, size, age and start year alone, the chance of a large revision is discriminated
at 0.6345 and the chance of a suspected exit at 0.6624, against 0.6213 for a first revision of any size. So the
tail and the exits carry real structure, and the object everyone models, the first revision, carries the least.
**Evidence**: `results/delivery-model-object-{move,large,withdraw}.md`, panel `results/delivery-panel-objects.csv`,
declared in `docs/plan/object-redefinition.md`.
**Scope**: 27,708 project months, 2,190 revisions, 576 large, 639 suspected exits, mechanism window.
**Consequence**: the structure is project intrinsic, so a forecast of the tail needs project, host and contract
data, not market aggregates. Also, an exit is more predictable than a revision, so the exit is the better object
if a model of this family is ever rebuilt.

## T15. Compute family dispersion has no listed instrument

**Statement**: the ten independent compute rental families that were measured have no listed issuer whose reported
revenue isolates one family. Every candidate issuer reports by business line, geography or product type, or
reports a single operating segment. Where a compute rental line is disclosed, it is a blend across families.
**Evidence**: `results/compute-issuer-segments.csv`, from the latest annual report of each of sixteen declared
issuers, parsed from their own XBRL instance documents (`scripts/probe_compute_issuers.py`).
**Scope**: listed issuers in the rental, hosting, server, data centre and electrical supply chain, annual reports
filed to early 2026.
**Consequence**: relative value across compute families is real and has no instrument through equity. The closest
listed vehicles are whole business hosts, where the exposure is total compute demand rather than the dispersion
between families. The candidate therefore closes on evidence unless the rental market itself can be held.
**Named vehicles, for the record**: CoreWeave, whole business, 1.9bn revenue. Hut 8, roughly half its 162m from
high performance computing and colocation. Core Scientific, a disclosed rental line near five percent. IREN,
ninety eight percent mining and two percent compute. Digital Realty, ninety nine percent rental, but that is real
estate across many tenants. Server and infrastructure suppliers are diversified, Dell at 114bn, HPE at 30bn, with
HPE's server segment at 53 percent and one rental like line at 18 percent.


## T16. Ten metre imagery does not separate construction states well enough to read delivery

**Statement**: on 24 labelled sites the declared statistic, the Spearman correlation between surface texture change
and months of delivery slip, is plus 0.30 with a permutation p of 0.087, and the late group is indistinguishable
from the early group, plus 0.30 against plus 0.27. The signal that looked like plus 0.72 on eight sites did not
hold.
**Evidence**: `results/imagery-probe-40.csv` and `results/imagery-statistic.txt`, against the pre-registration in
`docs/plan/imagery-test.md`.
**Scope**: 40 declared sites, 24 of which produced a usable cloud free scene pair, ten metre Sentinel-2 pixels,
wind and solar sites.
**Consequence**: the physical progress direction ends at this resolution and this design. It also establishes a
feasibility fact: sixteen of forty sites could not produce a usable before and after pair at all, mostly for want
of a cloud free control patch inside the scene.

## T17. Compute prices do not lead provider capex, and the aggregate points the wrong way

**Statement**: across 42 provider-quarters, the cross-family median compute price change associates
negatively with next-quarter provider capex growth (rho -0.33, permutation p 0.04), and the family-level
tests are at chance: 2 nominal survivors out of 13 tested against 0.65 expected under the null. The
declared positive mechanism, where scarcity prices invite capital, is not supported.
**Evidence**: `results/compute-lead-study.json`; `results/provider-capex-quarterly.csv`;
`results/compute-price-monthly.csv`; `scripts/build_compute_lead_study.py`.
**Scope**: 18 rental families, monthly medians 2022-05 to 2026-09; twelve listed providers, quarterly
capex from SEC XBRL; development only, both sealed windows spent.
**Consequence**: the compute index stays a phase marker and a monitoring read, never a leading feed into
the capex chain. The reversed sign is a hypothesis for a separate study, not a finding.

## T18. Exit is ordered by what the project is, not by how crowded the queue was

**Statement**: within state-year blocks, queue crowding has no effect on withdrawal: the high-low
gap in withdrawal share is +0.0003 (permutation p 0.49), and the pooled negative correlation of -0.171
is a cohort artifact because later requests are both more crowded and younger. Technology does order
exits: the spread between the highest and lowest withdrawal share among technologies with at least 200
projects is 27.9 points (p 0.018), offshore wind 72.3 percent against hydro 44.5 percent. Size has no
positive effect within blocks (rho -0.023).
**Evidence**: `results/queue-exit-study.json`; `scripts/build_queue_exit_study.py`.
**Scope**: all 36,441 queue projects, snapshot through February 2025; crowding is cumulative earlier
request MW within the state, point-in-time safe. Development only; both sealed windows are spent.
**Consequence**: the exit object is usable as a ranking through project characteristics, and the queue
crowding variable is retired as an exit predictor. Any device that leans on queue age or crowding to
order exits inherits a dead link.

## T19. The aggregate rental change does not reach provider revenue, and the family signs disagree

**Statement**: across 91 provider-quarters, the lagged aggregate compute rental change does not order
year over year provider revenue growth (rho -0.16, circular shift p 0.85), and the reverse control is
also null (rho -0.05). Family level signs disagree, p5 at +0.21 against p3 at -0.23, so the aggregate
median washes out family heterogeneity rather than the mechanism being absent.
**Evidence**: `results/provider-transmission-study.json`; `results/provider-revenue-quarterly.csv`;
`scripts/build_provider_transmission_study.py`; `scripts/fetch_provider_revenue.py`.
**Scope**: ten providers with SEC XBRL revenue, 91 usable provider-quarters from 2023 to 2026; aggregate
rental change is the cross-family median; development only.
**Consequence**: the provider family's revenue link is open at the family level, not the aggregate. The
next object is the provider to family exposure map, tested family by family. The aggregate is retired as
the transmission variable.

## T20. The cascade cost hurdle binds, and the frozen conjunction's gross clears it

**Statement**: on the recorded tape, percentile dislocation levels (top 1 percent and top 5 percent of
one minute moves, funding beyond two sigma, thin books) land between -5 and -22 basis points net of base
costs, with gross means of at most +6.1 basis points at fifteen minutes, all inside their random-time
nulls. The frozen conjunction fired six times, and its gross reversion at fifteen minutes is +17.9 basis
points: +6.9 net of base costs, -4.0 net of doubled costs, permutation p 0.068. Reversion is market
specific, SPX +20.4 against GAS -0.0 on the same level.
**Evidence**: `results/cascade-reversion-study.json`; `scripts/build_cascade_reversion_study.py`;
`data/tape`.
**Scope**: recorded window of about fourteen hours of samples across six tape files, four markets (BTC,
ETH, GAS, SPX), one venue, entry at the condition bar close with no speed advantage used; development
only.
**Consequence**: the binding constraint is the cost hurdle near ten basis points round trip, not the
presence of reversion. The conjunction is the only condition whose gross clears it, on six events, so the
family's next work is more events and cheaper entry, not wider level ladders.

## T21. The provider to family map is not supported, raw or relative

**Statement**: on raw family changes, ten mapped provider family pairs show mean rho -0.27 against thirty
two unmapped pairs at -0.02, with zero mapped shift null survivors against five unmapped. On relative
changes, the family change minus the cross-family median, mapped pairs show -0.17 against +0.04, zero
survivors against four. The strongest single association, EQIX against g5 at +0.71, sits on the provider
the map excludes from GPU families.
**Evidence**: `results/provider-family-tests.json`; `results/provider-family-tests-relative.json`;
`scripts/build_provider_family_tests.py`; `docs/scan/provider-family-map.jsonl`.
**Scope**: ten providers, 42 tested provider family pairs, 11 usable quarters per pair; development only.
**Consequence**: family price mapping is retired as the provider transmission variable. The provider
object moves to level variables, revenue per megawatt, contracted share and lease spread, which need
filing level data rather than rental prices.

## T22. Maker entry improves the paired result and fails the absolute one

**Statement**: resting at the dislocation extreme fills 33 percent of frozen conjunction events and 48
percent at the top one percent level. The paired result against taker entry is +5.5 to +7.8 basis points
on the same events, but the absolute maker net is at or below zero at most cells: +3.28 basis points at
the top one percent level at fifteen minutes, inside the null (p 0.2) and negative once costs are doubled
(-2.72). The filled and unfilled split shows adverse selection: at the frozen conjunction the two filled
events net -13.2 basis points under the taker convention against +17.0 for the four unfilled ones. A
stricter fill rule, standing in for queue position, removes the good fills and keeps the bad ones: at the
top one percent level the net falls from +3.28 to -0.66 to -1.27 basis points as required penetration
rises from zero to half a spread to a full spread.
**Evidence**: `results/maker-entry-study.json`; `scripts/build_maker_entry_study.py`; `data/tape`.
**Scope**: recorded window, four markets, one venue, best bid and ask snapshots at fifteen seconds, no
queue position modelled; development only.
**Consequence**: the binding constraint is fill selection. The positive maker cells are an artifact of
optimistic fills, so maker entry is a size tool rather than a source of edge on this window, and the
reversion that exists is taken immediately at the event.

## T23. Hyperscaler capex intensity is running ahead of revenue, and the aggregate gap is not yet persistent

**Statement**: on six providers with aligned panels, pooled capex intensity is 0.287 of revenue, and the
most recent quarters sit far above each mean for the hyperscalers: MSFT 0.471 against 0.136 with a trend
rho of +0.94, ORCL 2.017 against 0.212 at +0.92, GOOGL 0.404 against 0.184 at +0.35. The pooled gap,
capex growth minus revenue growth, averages -0.089 with autocorrelation -0.28, and capex growth does not
lead revenue growth at one quarter (rho -0.07, p 0.70, 122 ordered pairs). AMZN, APLD, CRWV and IREN have
no usable panel: stale concept tags, annual only capex, and short histories.
**Evidence**: `results/capex-revenue-gap.json`; `scripts/build_capex_revenue_gap.py`;
`results/provider-capex-quarterly.csv`; `results/provider-revenue-quarterly.csv`.
**Scope**: six providers, SEC XBRL quarterly facts, development only.
**Consequence**: the depreciation wall node carries evidence now, and the open object is whether the
equity market prices the intensity rise, which requires the market panel.

## T24. Cross market entry does not rescue the cascade family at size

**Statement**: every cross market entry into BTC or ETH nets negative at both dislocation levels, and the
same market cells are negative as well. The only positive cells enter the thin markets: ETH events
followed by an SPX position net +4.8 basis points on 172 events (p 0.003) at the top five percent level,
and ETH followed by GAS nets +3.7 on 35 events (p 0.002) and BTC followed by SPX +6.4 on 35 events
(p 0.083) at the top one percent level, with median depth at entry between 1,178 and 3,976 dollars. The
target is entered against the source move, so those cells say the thin targets move against the source
dislocation.
**Evidence**: `results/spillover-study.json`; `scripts/build_spillover_study.py`; `data/tape`.
**Scope**: one venue, one recorded window, four markets, fifteen second snapshots; development only.
**Consequence**: the reversion expression stays in the source market. The thin market cells are structure
with trivial capacity, useful as a monitor and not as a trade until a larger venue shows the same
behaviour.

## T25. In the provider panel, the market charges capital intensity over weeks

**Statement**: across 108 provider quarters and eight names, the year over year change in capex intensity
is negatively associated with peer excess return: rho -0.29 (two sided p 0.005) at five trading days,
-0.24 (p 0.012) at twenty, and -0.07 (p 0.49) at sixty. The tercile spread is -2.2 percentage points at
five days and -6.0 at twenty, against the name's own declared group.
**Evidence**: `results/intensity-pricing-study.json`; `scripts/build_intensity_pricing_study.py`;
`results/bar-cache/`.
**Scope**: eight providers with aligned XBRL capex and revenue, event dated at the later filing, daily
closes from a free source; development only.
**Consequence**: this is the first priced link found in the provider family. It is the lead object for
the cross-section study, which tests whether it generalises.

## T26. The intensity effect does not generalise across the complex, and the segment split is the structure

**Statement**: across 640 observations and 58 names with a within-quarter design, the mean within-quarter
correlation between intensity change and forward excess return is -0.035 against the complex benchmark at
five days (p 0.45) and -0.083 against own group (p 0.08), with no more than a weak negative reading at
twenty days. Segment signs are consistent though: hyperscalers negative at every horizon (-0.14 to
-0.28), compute and AI negative at twenty days (-0.41), buildout negative at every horizon (-0.13 to
-0.20), and data center REITs positive at five and sixty days (+0.08 to +0.19).
**Evidence**: `results/intensity-factor-study.json`; `results/complex-capex-quarterly.csv`;
`results/complex-revenue-quarterly.csv`; `scripts/build_intensity_factor_study.py`;
`scripts/fetch_complex_fundamentals.py`.
**Scope**: 58 listed names in the declared market panel groups, 29 quarters, quarterly fundamentals
against daily closes, development only.
**Consequence**: the intensity surprise is retired as a complex wide factor and kept as a segment level
hypothesis: charged where capital is owned, not charged where capacity is leased or regulated.

## T27. The intensity charge appears where capital is owned, and not where capacity is leased

**Statement**: in owned capital segments (hyperscaler, compute and AI, buildout), 334 observations across
33 names show a mean within-quarter correlation of -0.16 (p 0.031) at five days and -0.15 (p 0.048) at
twenty, with tercile spreads of -1.9 and -5.2 percentage points, and nothing at sixty days. In leased or
regulated segments (data center REIT, power, fuel and nuclear), 306 observations across 25 names show
-0.05, +0.006 and +0.03 at the same horizons (p 0.46, 0.94, 0.58), with tercile spreads at or above zero.
**Evidence**: `results/intensity-segment-study.json`; `scripts/build_intensity_segment_study.py`.
**Scope**: a declared second look at the 640 observation panel from T26, re cut by ownership of capital;
modest p values; development only.
**Consequence**: the working hypothesis is that the market charges capital intensity only where the
capital is owned. The next evidence must come from a different sample, which is the declared time split.
See T28 for its result, which keeps the charge and downgrades the ownership mechanism.

## T28. The intensity charge is sign stable in time, and the ownership mechanism is not

**Statement**: in the owned capital segments the early window (through 2024) shows a mean within-quarter
correlation of -0.12 (p 0.21) at five days, -0.18 (p 0.050) at twenty and -0.09 at sixty, and the late
window (2025 onward) shows -0.26 (p 0.043), -0.09 (p 0.48) and +0.14 (p 0.30). In the late window the
leased and regulated segment is also negative at five and twenty days (-0.22 and -0.19), so the charge
is not confined to capital owners, and the sixty day reading flips positive.
**Evidence**: `results/intensity-timesplit-study.json`; `scripts/build_intensity_timesplit_study.py`.
**Scope**: the same panel as T26 and T27, split by filing date at 2024-12-31; 229 early and 105 late
observations; development only.
**Consequence**: the stable object is a broad negative association between intensity surprises and
relative equity returns over five to twenty trading days, with a reversal candidate at sixty days. The
ownership mechanism is downgraded and the reversal is the next declared object.

## T29. The intensity charge is not asset growth, and asset growth is rewarded

**Statement**: on the 640 observation complex panel, the within-quarter correlation between intensity
change and asset growth is -0.006, so they are distinct predictors. Asset growth is positively associated
with forward excess return (+0.067 at five days, +0.133 at twenty, +0.092 at sixty), the opposite sign of
the classic asset growth anomaly and coherent with a buildout. Intensity is negatively associated (-0.087,
-0.072, -0.017), and the intensity reading after removing asset growth within each quarter is -0.109 at
five days (two sided p 0.018), -0.076 at twenty (p 0.10) and -0.007 at sixty.
**Evidence**: `results/intensity-vs-assetgrowth-study.json`; `results/complex-assets-quarterly.csv`;
`scripts/build_intensity_vs_assetgrowth_study.py`; `scripts/fetch_complex_assets.py`.
**Scope**: 58 names, 640 observations, within-quarter design, group excess returns, one free price
source; compared against asset growth only, other known factors untested; development only.
**Consequence**: the intensity object survives its first separation test and stays a short-horizon
candidate. The next evidence is the pre-boom window and a capacity screen with volume, before anything is
called an edge.

## T30. The intensity charge is sign consistent across three regimes and fragile in each

**Statement**: the mean within-quarter correlation between intensity change and forward group excess
return is negative at five and twenty days in all three windows: pre-boom (2018 to 2021, 142 observations,
24 names) -0.077 (p 0.54) and -0.110 (p 0.37); buildout (2022 to 2024, 87 observations) -0.164 (p 0.23)
and -0.263 (p 0.054); late (2025 onward, 105 observations) -0.261 (p 0.043) and -0.092 (p 0.48). Tercile
spreads are negative in every window at both horizons, largest in the buildout window (-8.0 and -10.2
percentage points). Sixty day readings are mixed, with the late window turning positive (+12.4 points).
**Evidence**: `results/intensity-preboom-study.json`; `scripts/build_intensity_preboom_study.py`.
**Scope**: the same panel cut by filing date across three regimes, one price source, overlapping windows,
no volume; development only.
**Consequence**: the direction of the charge is not a property of this buildout, but its significance is
fragile and its capacity is unknown. The next objects are volume and costs, not more cuts.

## T31. The intensity charge is fragile and name concentrated

**Statement**: removing the ten discovery names halves the effect and removes its significance: 498
observations across 49 names show -0.042 (p 0.44) at five days, -0.026 (p 0.63) at twenty and +0.001 at
sixty, against -0.087 (p 0.064), -0.072 (p 0.13) and -0.017 on the full panel. Per quarter, across 39
quarters, the correlation is negative in 56 percent of quarters at five days, 62 percent at twenty and 56
percent at sixty, with tercile spreads negative in 56, 67 and 56 percent.
**Evidence**: `results/intensity-robustness-study.json`; `scripts/build_intensity_robustness_study.py`.
**Scope**: the same panel, robustness pass, development only.
**Consequence**: the charge is a candidate, not an edge. Further cuts of this panel are not evidence; the
next real test is a disjoint sample with a capacity and cost check.

## T32. The intensity expression nets a thin return under repaired accounting, with small capacity

**Statement**: after the 2026-10-04 accounting repair, the declared specification (twenty day horizon,
terciles, equal weight, group neutral, ten million dollar volume floor, filing clock, base costs) returns
2.9 percent annualised net against 4.5 gross across 267 cohorts from 2017-02-14 to 2026-10-02, with annual
volatility 8.5 percent, Sharpe 0.347, profit factor 1.081 and a maximum drawdown of -22.9 percent. Early
(through 2024) it is 2.6 percent at Sharpe 0.33; late (2025 onward) 4.5 percent at 0.435. Doubled costs
leave 1.4 percent at Sharpe 0.170. Capacity at one percent participation of the binding name is 1.17
million dollars median and 71 thousand at the tenth percentile; at five percent, 5.83 million. The
pre-repair numbers (13.1 percent net, 34.3 percent volatility, Sharpe 0.381, -65.8 percent drawdown, 3.87
million capacity) were an artifact of summing overlapping full-gross cohorts and are superseded; the five
defects are listed in the thesis record and pinned by `tests/test_intensity_accounting.py`. A trailing
volatility overlay moves the Sharpe from 0.347 to 0.348 and deepens the drawdown to -28.6 percent; it is
recorded as rejected.
**Evidence**: `results/intensity-strategy.json`; `scripts/run_intensity_strategy.py`;
`tests/test_intensity_accounting.py`; `docs/theses/t-intensity-charge.md`;
`docs/chains/t-intensity-charge.jsonl`.
**Scope**: 58 names, development only, both sealed windows spent, one price source, borrow cost unmeasured;
the fragility result (T31) remains the main threat.
**Consequence**: the strategy keeps its measured P&L role, but the corrected margin over doubled costs is
0.8 percentage points of annual return and the capacity is small, so it is not a demonstrated edge. The
next declared iterations are a disjoint name test, borrow data, and a cluster capped risk overlay.
Attribution is unresolved: the controlled test (T33) does not support the intensity association, so the
strategy's P&L is not yet explained by the tested mechanism.

## T33. Intensity does not survive controls, and the realised-conversion split does not rescue it

**Statement**: on 637 observations across 58 names and 127 quarters, the Fama-MacBeth cross sectional
regressions give an intensity coefficient of -0.0068 (t -0.98) univariate, and +0.0061 (t 0.65) once peer
group, revenue growth, asset growth and operating margin are controlled; adding the common investment
factor changes nothing. The revenue conversion split is the opposite of the declared expectation
(failure group +0.0105, t 1.05; passing group -0.0076, t -0.54), and the backlog conversion split has too
few quarters to test (192 observations over fewer than four usable quarters, reported as insufficient).
**Evidence**: `results/intensity-controls-study.json`; `scripts/build_intensity_controls_study.py`;
`docs/plan/intensity-controls-study.md`.
**Scope**: 59 name universe, forward twenty day group excess returns, quarterly cross sections with group
demeaning, one price source, development only.
**Consequence**: capex intensity is investment intensity, not a proven expectation surprise. The
association is retired as a priced charge and kept as a falsifiable hypothesis about the expectation
channel, to be tested with filing based surprise measures (8-K items, guidance, RPO conversion).

## T34. Compute rental levels lead queue withdrawals by about two quarters

**Statement**: on 28 overlapping months, the cross family median rental price against its trailing twelve
month mean is negatively associated with the queue withdrawal hazard six months later: pooled rho -0.60
with the observed beyond every one of the 19 circular shifts, solar -0.57, wind -0.42, battery -0.61, gas
-0.21. The three month change reading is positive at one and three month lags and negative at six, so only
the level reading is kept. Speculative technologies carry a mean hazard of 0.00156 against 0.0001 for firm
ones, fifteen times the risk.
**Evidence**: `results/compute-queue-study.json`; `scripts/build_compute_queue_study.py`;
`docs/plan/compute-queue-study.md`.
**Scope**: one queue snapshot with recalled dates, 2022-05 to 2024-12, compute prices that are policy
prices in ten separate markets, thirty cells tested across lags, groups and readings, shift test with 19
shifts so the attainable share is 0.05. Development only.
**Consequence**: the compute rental level is the demand side sensor for thesis C, with a two quarter lead
on the withdrawal hazard, and it is the first measured link from compute markets to the physical queue.
It stays a phase marker, never a required link.

## T35. The dated regime state, version 1, reads buildout from 2022 with an overbuild reading in 2024

**Statement**: under the declared two sensor rules (demand economics from the rental level against a
trailing twelve month mean, supply stress from the trailing three month withdrawal hazard, fixed bands,
two month confirmation), the machine labels 132 months from 2014 to 2024 as buildout 79, overbuild 39,
shakeout 8, shortage 6, with 15 transitions. Buildout runs from 2022 with an overbuild reading appearing in
2024 as rental levels fell below trend and the withdrawal hazard rose, then wobbling between the two labels
in late 2024 as the rental reading crossed its trend.
**Evidence**: `results/regime-state-daily.csv`; `results/regime-state-summary.json`;
`scripts/build_regime_state.py`; `docs/plan/regime-state-machine.md`.
**Scope**: judgment thresholds, version 1; the rental sensor exists only from 2022-05 and earlier rows run
on spend and hazard alone; one queue snapshot; development only.
**Consequence**: the sizing layers of theses A and C have a dated state to read, and the 2024 overbuild
reading is the first place the machine says something the queue alone would not, because the rental sensor
leads the hazard the queue measures.

---

# What these truths are pointing at

Reading the ledger together, three strategy shapes are consistent with what is true, and each has a named
obstruction:

1. **Relative value across compute inventories.** Ten independent markets with meaningful dispersion. Obstruction:
   no holdable instrument, so it must be expressed through providers, owners or contracts, which means the
   question becomes which listed entity's economics are levered to a specific family's scarcity.
2. **The tail of delivery revisions, cross sectionally, in an uncovered subset.** Obstruction: the covered
   expression is efficient (T7), so this requires a name set and an attribution path that is not already
   arbitraged, and the queue factor that would order it (T11).
3. **Forced flow on continuous venues.** Obstruction: none conceptually, and the tape is running. It is the only
   place where the engine, the speed and the instrument all exist today.

Everything else we have tried is blocked either by an instrument, by attribution, or by a data source we do not
hold. That is not a list of failures, it is a map of where the doors are.

## State of the three doors, 2026-10-04

Two doors have since been tested and closed on evidence. The compute lead is dead: family price changes
do not lead provider capex, and the aggregate points the wrong way (T17). Queue crowding is dead as an
exit predictor: within state and cohort it orders nothing, while technology orders a lot (T18). The
delivery tail remains real but intrinsic to projects (T10, T14), so it needs a name set and an
attribution path before it is anything, and no listed instrument isolates the queue units (T6).

That leaves one door with a full stack behind it: **forced flow on continuous venues**. The mechanism
has external evidence, the instrument exists, the tape is running, and the engine now exists in this
repository. What is missing is a live protocol under the frozen-protocol rule and a measurement of the
dislocation net of costs at zero latency advantage, which is the clause every edge here must satisfy.

No edge is established tonight. What is established is where the edge has to be, and that is worth
more than a story about the last five years going up.

## T36. The RPO expectation gap is partly predictable from an issuer's own history

**Statement**: with point-in-time vintages for 2,803 measured RPO disclosures across 236 issuers, a
multinomial logistic regression on 17 features that are strictly earlier than the decision beats the
training prevalence on the later rows of a chronological split: log loss 1.473 against 1.609, Brier
0.751 against 0.800, and accuracy 0.293 against 0.197 over 833 test rows from 2023-10-25 onward. The
signal is weak in absolute terms, about 29 percent accuracy over five balanced classes, so this is a
measured partial forecast and not a strong one. The declared falsifier was "the fitted model does not
beat the training prevalence on the later rows"; it did beat it. This forecasts the expectation gap,
not a return, and no cost or trading claim follows.
**Evidence**: `results/rpo-specialist-scores.json`; `results/rpo-vintages.csv`;
`scripts/run_rpo_specialist.py`; `docs/plan/rpo-specialist.md`.
**Scope**: 236 issuers, 2,782 usable rows, end-of-day availability clocks for most disclosures,
current-ticker identity, development only, both sealed windows spent.
**Consequence**: the expectation channel has a point-in-time, large-sample foundation. The next steps
are the filing-joined version for the four candidate firms, the text specialist on the same rows, and
carrying the forecast into the council as one specialist rather than a standalone claim.

## T37. Filing metadata adds a little to the disclosure history for RPO surprises

**Statement**: on 2,782 RPO decisions from 210 issuers, split chronologically 1,949/833, adding the
latest filing's metadata features, meaning form, item flags, filing cadence and days since filing,
to the disclosure-history model improves every metric over the history-only model: log loss 1.461
against 1.473, Brier 0.744 against 0.751, and accuracy 0.325 against 0.293. Training prevalence
stands at 1.609, 0.800 and 0.197. The lift is small, twelve thousandths of log loss and three points
of accuracy, on a model whose absolute accuracy is a third of a five-class problem. The declared
falsifier was that the filing features do not improve the proper scores; they improve them slightly,
so the filing route into the expectation gap is not decoration, but this is far from a mechanism
claim.
**Evidence**: `results/rpo-filing-panel-scores.json`; `results/filings-register-rpo.csv`;
`scripts/run_rpo_filing_panel.py`; `docs/plan/rpo-filing-join.md`.
**Scope**: 197 issuers with filings, 27,673 filings, metadata only, one filing per decision, no
document text, no returns, development only, both sealed windows spent.
**Consequence**: the equity bridge has a small measured lift from filing metadata. The next tests are
whether document text adds beyond metadata on the four-firm corpus where text exists, and whether the
forecast carries useful weight inside the council.

## T38. Frozen document text carries information that filing metadata does not

**Statement**: on the 81-label four-firm filing panel, split 58/23 chronologically, a softmax on
eight training-only principal components of frozen MiniLM document embeddings, text alone, beats
both the training prevalence and the metadata-only model on the proper scores: log loss 1.508
against 1.599 and 1.679, and Brier 0.741 against 0.782 and 0.750. Its accuracy is lower, 0.391
against 0.435 and 0.478, so the gain is in probability quality rather than in the top-class pick.
The naive concatenation of metadata and text is the worst model on log loss at 1.746, which says
the two evidence blocks need stacking or gating rather than one linear head. The declared question
was whether document text adds beyond filing metadata; on this sample it does, and the combined
linear model fails to capture it.
**Evidence**: `results/filing-text-ab.json`; `results/filing-specialist-events.csv`;
`results/filing-text-manifest.json`; `hpc/probabilistic-council/run_filing_text_ab.py`;
`src/filing_specialist/text_ab.py`; `docs/plan/filing-specialist.md`.
**Scope**: 81 labels, PWR dominated, one frozen encoder, eight components, metadata and text both
from the same four firms, development only, both sealed windows spent.
**Consequence**: the text side of the equity bridge has a measured sign. The next work is a
stacking or gating layer over the two evidence blocks, and the same test on a larger label set,
not more linear features.

## T39. The council as a combiner beats every single evidence block on the four-firm panel

**Statement**: on the 81-label four-firm filing panel with chronological blocks of 34 training,
9 calibration, 9 gate, 9 pool and 20 evaluation rows, the council over the metadata specialist
and the text specialist wins on both proper scores: log loss 1.705 against 3.130 for metadata
alone, 2.044 for text alone and 2.828 for the naive concatenation; Brier 0.821 against 0.988,
0.914 and 0.978. Training prevalence reaches 1.728 log loss with zero accuracy on the evaluation
block because its argmax class is absent there. The gate weights are nearly equal, 0.485 and
0.515, so the visible gain comes from temperature calibration and pooling rather than from
reliability reweighting. Accuracy is not the council's win: 0.300 against 0.350 for the
concatenation, so the gain is in probability quality, which is the quantity a council is for.
**Evidence**: `results/filing-council-ab.json`; `results/filing-specialist-events.csv`;
`results/filing-text-ab.json`; `hpc/probabilistic-council/filing_council.py`;
`scripts/run_filing_council.py`; `docs/plan/filing-council.md`.
**Scope**: 81 labels, PWR dominated, three council partitions of nine rows each, block specialists
trained on 34 rows, development only, both sealed windows spent.
**Consequence**: the council layer earns its place on measurable evidence for the first time, but
the sample is far too thin to promote. The next step is the same experiment on a larger label set
and then on the risk track's dates, where the partitions can be properly sized.

## T40. Filing metadata beats prevalence on point-in-time obligation labels for the four firms

**Statement**: on the 87 deciding filings that precede a measured obligation vintage for PWR and
ETN, about 50 distinct disclosure periods, a softmax on ten filing and prior-obligation features
beats the training prevalence on the later rows of a chronological split: log loss 1.238 against
1.558, while accuracy is slightly lower, 0.538 against 0.577. The every-filing view, 8,185 rows
that reuse each label many times, shows 1.196 against 1.284 and is a robustness row only. The
declared falsifier was that the fitted model does not beat prevalence; it beats it on log loss in
both views, and the deciding view counts because its rows map to distinct disclosure periods.
**Evidence**: `results/filing-obligation-scores.json`; `results/filing-obligation-decisions.csv`;
`results/obligation-vintages.csv`; `scripts/run_filing_obligation_panel.py`;
`docs/plan/filing-obligation-panel.md`.
**Scope**: PWR and ETN only, 87 deciding rows over about 50 periods, metadata only, no document
text, development only, both sealed windows spent.
**Consequence**: the four-firm label set is now point-in-time and covers more disclosure periods
than the 81-label revision panel, and the metadata model predicts it better than prevalence. The
next step is the text comparison on the same rows using the cached 8-K corpus.

## T41. On the obligation panel, metadata dominates and text adds only a little

**Statement**: on the 87 deciding filings labelled by point-in-time obligation surprises, 61
train and 26 evaluation rows, metadata reaches log loss 1.238 and Brier 0.650, text alone 1.290
and 0.659, and the combination 1.214 and 0.658, against prevalence at 1.558 and 0.763. The
every-filing robustness view shows the same order: metadata 1.196, text 1.290, combined 1.192,
prevalence 1.287. Text adds about two hundredths of log loss on the deciding view and four
thousandths on the every-filing view, so the obligation surprise is mostly a function of the
firm's own disclosure history and the filing text adds little. This tempers T38, where text alone
beat metadata on the revision panel: the value of text is panel-dependent.
**Evidence**: `results/filing-obligation-text.json`; `results/filing-obligation-decisions.csv`;
`hpc/probabilistic-council/run_filing_obligation_text.py`; `docs/plan/filing-obligation-panel.md`.
**Scope**: PWR and ETN only, 26 evaluation rows over about 50 distinct disclosure periods, one
frozen encoder, development only, both sealed windows spent.
**Consequence**: further text work should target the panel where text carried information, the
revision panel, or a larger label set. On this panel metadata is enough.
