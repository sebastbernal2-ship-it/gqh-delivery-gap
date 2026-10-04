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
**Evidence**: `results/intensity-strategy.json` (base costs) and `results/intensity-strategy-doubled.json` (doubled costs); `scripts/run_intensity_strategy.py`;
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

## T42. The intensity strategy's published edge does not survive the corrected disclosure clock

**Statement**: the published panels date every quarter by the latest filing that reported it, a
ten-K comparative, with a median availability lag of 401 days. Rebuilt with the earliest filing, the
median lag is 34 days for capex and 36 for revenue, same rows and same tickers. Re-running the
declared base configuration changes +2.94 percent net, Sharpe 0.347 and drawdown -22.9 percent into
-4.89 percent net, Sharpe -0.630 and drawdown -48.0 percent; doubled costs go from +1.44 to -6.24
percent. The RPO and obligation panels are unaffected, medians 38 and 55 days.
**Evidence**: `results/intensity-clock-test.json`; `scripts/run_intensity_pit_clock_test.py`;
`scripts/build_complex_panels_pit.py`; `results/complex-capex-quarterly-pit.csv`;
`results/complex-revenue-quarterly-pit.csv`.
**Scope**: development only, both sealed windows spent, one price source. The original panels were
not modified; they belong to the intensity workstream.
**Consequence**: the note's intensity numbers stand as measured on the earlier clock, and this
discrepancy must be reported to that owner before the strategy is used again. Any further work on
the intensity signal must use the earliest-filed clock.

## T43. The strategy's own drivers carry a correctly clocked expectation gap, and its two halves point opposite ways

**Statement**: on the corrected clocks, the revenue surprise forecast covers 509 out-of-sample rows
over 55 issuers and beats prevalence on log loss, 1.5667 against 1.5868. Long-short by predicted bin
at twenty sessions: raw +9.35 percent with interval +3.19 to +18.21, month neutral +11.35 with
interval +6.59 to +17.06, and month and group neutral +4.75 with interval +1.13 to +9.28, so the
revenue surprise survives both neutralisations. The capex surprise goes the other way: month and
group neutral -4.87 percent, interval -10.51 to -1.34, which is the sign the intensity expression
already trades.
**Evidence**: `results/revenue-surprise.json`; `results/capex-surprise.json`;
`results/revenue-vintages-pit.csv`; `results/capex-vintages-pit.csv`;
`scripts/run_driver_surprise.py`; `docs/plan/driver-surprise.md`.
**Scope**: development only, 55 issuers, quarterly windows that overlap, one price source, flat
twenty basis point costs, no borrow and no capacity model.
**Consequence**: the expectation gap now covers the strategy's own universe, both halves carry the
economic sign the thesis expects, and gating the intensity cohorts by these signals is the next
test.

## T44. A revenue-surprise gate rescues the intensity expression out of sample, and the capex condition hurts

**Statement**: on the corrected clock, inside the out-of-sample window 2023-07-28 to 2026-10-02
where the surprise model never saw the rows, the ungated intensity expression returns -9.49 percent
net at Sharpe -0.904 with a -38.0 percent drawdown, 97 cohorts. Confirming each leg with the
revenue surprise, long when the expected bin is at or above expectation and short when below,
returns +10.48 percent net at Sharpe 0.971 with a -16.3 percent drawdown, and +9.96 percent at
doubled costs. The month-blocked interval for the difference is +7.75 to +35.30 percent annualised,
with 99.9 percent of 1,000 resamples positive and 40 months of blocks. Adding a capex condition on
top of the revenue gate destroys the result: -7.25 percent net, difference against the revenue gate
-17.80 percent with interval -31.71 to -2.99.
**Evidence**: `results/intensity-gate-test.json`; `scripts/run_intensity_gate_test.py`;
`docs/plan/alpha-build.md`; `scripts/run_intensity_strategy.py` gate argument.
**Scope**: development only, one out-of-sample window of about three years, 97 cohorts, a median of
five names per gated cohort, no borrow cost, no capacity expansion, one price source. Both sealed
windows are spent, so this is not a fresh holdout.
**Consequence**: the gate is the first interval-backed improvement in the programme and the
drawdown target is met in this window while the Sharpe target is not; breadth expansion and sleeves
are the next stages, and the combined gate is recorded as a rejected variant.

## T45. Breadth is built: 11,031 RPO events across 1,168 issuers, but the per-event edge does not generalise at that breadth

**Statement**: the broad panel, built from cached XBRL frames joined to accession acceptance
timestamps with no network calls, holds 15,547 vintages and 11,031 measured relative surprises across
1,168 issuers, 2017-03 to 2024-11, with a median availability lag of 39 days and 5.8 percent above
300 days, so the clock rule passes. The model beats prevalence out of sample on 3,373 rows and 935
issuers, log loss 1.5525 against 1.6103 and accuracy 0.266 against 0.191. The per-event edge does
not follow: price coverage is 26.4 percent, and on the covered rows the twenty-session long-short
spread is +2.17 percent raw with interval -7.29 to +11.01, and +1.31 percent month neutral with
interval -7.28 to +9.19, with an information coefficient near zero or slightly negative. Compare the
AI-capex revenue driver, +11.35 percent month neutral with interval +6.59 to +17.06 on the same
construction.
**Evidence**: `results/rpo-universe-vintages.csv`; `results/rpo-universe-scores.json`;
`scripts/build_rpo_universe_panel.py`; `scripts/run_universe_surprise.py`;
`tests/test_rpo_universe_panel.py`.
**Scope**: development only, price coverage confounds the edge test because only liquid names have
cached bars, no borrow cost, no capacity model, and the label is the RPO balance rather than the
revenue flow.
**Consequence**: breadth machinery works and the scores hold up, but the RPO edge does not generalise
at breadth as measured; the edge may be specific to the complex, the size bucket, or the revenue
concept. Stage 2b must expand price coverage and repeat the test for the revenue and capex drivers
before any sleeve decision.

## T46. At breadth, the surprise is forecastable but its pricing is not: the edge is complex-specific

**Statement**: with the price panel expanded to 839 series and dirty tickers excluded, three broad
universes were measured out of sample. Revenue: 291 issuers, 1,693 test rows, 97.8 percent price
coverage, model log loss 1.4947 against prevalence 1.5563, twenty-session long-short spread -0.55
percent raw and +0.47 percent month neutral, both intervals crossing zero. Capex: 301 issuers, 1,093
rows, 98.2 percent coverage, 1.1034 against 1.1297, spread -0.52 percent raw and -0.29 percent month
neutral. RPO: 935 issuers, 84 percent coverage, spread +1.75 percent raw and +0.06 percent month
neutral. In every case the model forecasts the surprise better than the base rate and the pricing is
zero. The measured pricing edges remain the AI-capex driver ones of T43, +4.75 percent for revenue at
month and group neutral and -4.87 percent for capex, on a much smaller panel.
**Evidence**: `results/universe-revenue-scores.json`, `results/universe-capex-scores.json`,
`results/rpo-universe-scores.json`, `results/universe-*-vintages.csv`,
`scripts/fetch_universe_bars.py`, `scripts/run_driver_surprise.py`, `docs/plan/alpha-build.md`.
**Scope**: development only, both sealed windows spent, one price source, dirty series excluded, no
borrow cost, no capacity model. The complex subsets inside the broad panels are too small to measure.
**Consequence**: breadth creates information, not alpha. The Sharpe target cannot be reached by
widening the universe; it needs depth inside the complex, more sleeves inside it, and execution cost
work. A market-wide disclosure-drift claim is not supported and will not be made.

## T47. The two-sleeve complex composite buys risk, not return, and its capacity is far larger than the intensity expression

**Statement**: inside the complex, out of sample, the revenue sleeve returns +35.94 percent a year at
51.1 percent volatility, Sharpe 0.704 and a -65.1 percent drawdown over 797 sessions and 506 events.
The capex sleeve, which is long low capex surprises and short high, returns +1.01 percent at 49.4
percent volatility, Sharpe 0.021 and a -61.3 percent drawdown over 836 sessions and 237 events. The
equal-gross composite returns +27.53 percent at 29.4 percent volatility, **Sharpe 0.938** and a
**-20.2 percent drawdown**; volatility-targeted to ten percent it returns +11.28 percent at 16.1
percent volatility, Sharpe 0.699 and a -15.6 percent drawdown. The composite-minus-revenue interval
is -14.95 percent, -66.64 to +35.99, so no return improvement is claimed: the composite's gain is a
40 percent volatility reduction and a two-thirds drawdown reduction at a better Sharpe. Capacity at
one percent participation is a median of 56.2 million dollars for the revenue sleeve and 42.4 million
for capex, with tenth percentiles of 6.8 and 5.3 million, over 54 and 55 tickers.
**Evidence**: `results/sleeve-portfolio.json`; `scripts/run_sleeve_portfolio.py`;
`src/filing_specialist/portfolio_stats.py`.
**Scope**: development only, both sealed windows spent, complex names only, flat twenty and forty
basis point round-trip costs, capacity from 60-session median dollar volume, models frozen from the
first seventy percent of each panel, overlapping events, 633 overlapping sessions.
**Consequence**: the drawdown requirement of the target is met by the composite and the volatility
target while Sharpe 2 is not, at 0.94. The next increment is a third sleeve, the gated intensity
expression of T44 at Sharpe 0.971 and -16.3 percent on the same window, plus more names and concepts
inside the complex. The sleeves' capacity is twenty to forty times the intensity expression's, so the
binding constraint on the combined strategy is the charge signal, not the expectation gap.

## T48. Three sleeves, and the gated charge expression is the anchor

**Statement**: on the common calendar of the three sleeves, 633 sessions from 2023-08-04 to
2026-08-31, the daily correlations are revenue against capex -0.261, revenue against the gated
intensity expression +0.481, and capex against intensity -0.218. Equal gross, the three-sleeve
portfolio returns +22.27 percent at 20.5 percent volatility, Sharpe 1.087 and a -16.1 percent
drawdown. Weighted by inverse volatility, which puts a mean 67 percent on the intensity sleeve, it
returns +18.31 percent at 13.4 percent volatility, **Sharpe 1.365** and a -14.5 percent drawdown, and
volatility-targeted to ten percent +16.34 percent at 11.0 percent volatility, **Sharpe 1.491** with a
**-9.0 percent drawdown**. The three-sleeve minus best-sleeve interval is +8.46 percent with an
interval of -24.11 to +36.98, and against the two-sleeve composite -4.23 percent, -18.49 to +12.05,
so the risk-adjusted gain is not a proven return gain.
**Evidence**: `results/three-sleeve-portfolio.json`; `scripts/run_three_sleeve_portfolio.py`;
`tests/test_three_sleeve.py`; `src/filing_specialist/portfolio_stats.py`.
**Scope**: development only, both sealed windows spent, complex names only, flat costs on the driver
sleeves and the engine's volume-bucket costs on the intensity sleeve, capacity mixed and bound by the
intensity expression at 1.17 million median, one common window of 37 months.
**Consequence**: this is the best measured configuration in the programme, Sharpe 1.49 with a
drawdown under ten percent, and the intensity sleeve carries most of the weight because it is both
calmer and better on its own. The next levers are within-complex breadth for the intensity sleeve,
which is the capacity bottleneck, and the frozen forward window.

## T49. The sleeve results are window-dependent: the composite is negative in sample

**Statement**: the same construction that returns +27.53 percent out of sample, Sharpe 0.938, returns
-13.86 percent in sample over 1,445 sessions, Sharpe -0.711, and -8.30 percent volatility-targeted.
The capex sleeve is the source: -49.46 percent in sample, Sharpe -1.145 and a -98.4 percent drawdown,
against +1.01 percent out of sample. The revenue sleeve is positive in both eras but weaker in sample,
+16.50 percent at Sharpe 0.490 against +35.94 at 0.704. The intensity expression is also era
dependent: -4.89 percent over its full period ungated, Sharpe -0.630, and +10.48 percent gated inside
the out-of-sample window where the gate model never saw the rows.
**Evidence**: `results/sleeve-portfolio.json` (`splits`), `results/three-sleeve-portfolio.json`,
`results/intensity-clock-test.json`, `results/intensity-gate-test.json`,
`scripts/run_sleeve_portfolio.py`.
**Scope**: development only; the in-sample era overlaps the code's own training rows, so it is a
stability diagnostic rather than a performance number, and the out-of-sample window is the 2023 to
2026 AI-capex boom, so it is favorable by construction in a way no other window is.
**Consequence**: T47 and T48 stand as measured on their window and are not evidence of a stable
effect. No cross-era alpha is established, the composite's recent strength may be regime, and the
frozen forward window is now the only honest way to claim anything. The capex sleeve in particular
does not deserve weight on its own record; it is kept only for its negative correlation.

## T50. The forward window is declared and armed; nothing in the repository is a window result

**Statement**: the forward window opens at the first trading session after 2026-10-04 and closes at
250 scored events or twelve months, whichever comes first. The protocol in
`docs/plan/forward-window.md` freezes the universe, the three sleeve recipes, the gate, the inverse
volatility weighting, the ten percent volatility target, the cost tiers and the metrics, and it names
five falsifiers before any observation exists. Snapshots are append-only and recorded with the
SHA-256 of their inputs and their fitted parameters; the evaluator refuses any event whose exit
session is not yet in the price cache; the window is scored once, at the end, and reported whether
good or bad.
**Evidence**: `docs/plan/forward-window.md`; `scripts/run_forward_snapshot.py`;
`scripts/evaluate_forward_window.py`; `tests/test_forward_window.py`;
`results/forward/snapshots/`.
**Scope**: the first snapshots carry zero events because no new complex filing had landed at their
run time; that is the expected armed state, not a result. Every development number in this repository,
including the best measured configuration at Sharpe 1.549 and a -9.0 percent drawdown, is not evidence
about this window, as T49 explains.
**Consequence**: any new performance claim must come from this window. Until it closes, the honest
statement of the programme is the development record plus an open, instrumented test.

## T51. Rolling origin: the revenue and gated-intensity sleeves survive every era, the capex sleeve does not, and dropping it raises the Sharpe

**Statement**: refitting every model at each of eight annual origins and scoring only the following
block, 2019-02 to 2026-08, 1,492 common sessions: the revenue sleeve returns +27.65 percent net at
Sharpe 0.756 and is positive in every single year from 2019 to 2026, +1.4 percent in the weakest and
+80.2 in the strongest; the gated intensity sleeve returns +6.49 percent at Sharpe 0.830 with a -10.7
percent drawdown; the capex sleeve returns -12.32 percent at Sharpe -0.263 and is negative in every
year but 2025 and 2026. The three-sleeve inverse-volatility composite returns +12.46 percent at Sharpe
1.145 with a -13.1 percent drawdown, which clears all three declared falsifiers. **Removing the capex
sleeve improves it**: two sleeves, inverse volatility with a mean 78.3 percent on intensity, return
+17.35 percent at Sharpe **1.493** with a -12.3 percent drawdown, and volatility-targeted +15.16
percent at Sharpe 1.376 with a -10.2 percent drawdown. Equal gross over the two sleeves, +24.83
percent at Sharpe 1.397.
**Evidence**: `results/walk-forward.json`; `scripts/run_walk_forward.py`;
`tests/test_walk_forward.py`.
**Scope**: development only, both sealed windows spent, complex names only, flat costs on the driver
sleeves and volume buckets on the intensity sleeve, block boundaries leaving up to twenty sessions of
overlap, weights estimated on trailing sixty sessions.
**Consequence**: the capex sleeve is retired from the portfolio, and T43's event-level sign stands as a
fact about returns that did not survive as a sleeve construction. The best supported configuration is
now the revenue and gated-intensity pair at Sharpe 1.49 across a rolling-origin record rather than a
single window, and both remaining sleeves are era-robust on this evidence.

## T52. Combined capacity is single digit millions at one percent, and an earlier capacity figure was optimistic

**Statement**: with each sleeve's daily positions gross-normalised to one unit of capital, capacity at
one percent participation is a median 0.92 million dollars for the revenue sleeve alone and 1.83
million for the gated intensity sleeve alone; the combined portfolio at equal sleeve weights gives a
median 8.15 million with a tenth percentile of 0.93 million, and at the walk-forward inverse-volatility
weights of T51, 21.7 percent revenue against 78.3 percent intensity, a median 8.14 million with a tenth
percentile of 1.55 million. The binding names are the small caps, PLUG, APLD, LEU and PRIM, not the
megacaps. At five percent participation the combined medians are forty million with tenth percentiles
near five to eight million.
**Evidence**: `results/capacity-curve.json`; `scripts/run_capacity_curve.py`;
`tests/test_capacity_curve.py`.
**Scope**: development only, volume cache covering the complex names, no borrow or shortability
constraint, participation per name measured against the 60-session median dollar volume.
**Correction**: T47's capacity figures, a median 56.2 million for revenue and 42.4 for capex, used
un-normalised conviction weights and are therefore optimistic by roughly the gross they omitted.
T52's normalised figures are the ones to quote, and any capacity number must state its weights and
its normalisation.
**Consequence**: the combined portfolio can carry single-digit millions at one percent participation,
the constraint is small-cap names rather than the charge signal's universe, and widening the strategy
means either dropping the smallest names or accepting larger participation.

## T53. On the complex revenue panel the council beats every single block and concatenation, with intervals excluding zero

**Statement**: 1,706 rows, 59 issuers, two data bundles, the disclosure history and the market state
into the disclosure with a declared peer map. Prevalence scores 1.6078 log loss, the issuer facts
block 1.7935, the market state block 1.6942 and naive concatenation 1.9878, all weak because the five
partition design trains each specialist on about seven hundred rows. The **council scores 1.5378**,
better than prevalence and every single block, and the paired differences clear zero: council minus
the best single block +0.1564 with interval 0.0863 to 0.2316 and 100 percent of issuer-blocked
resamples favouring the council, council minus concatenation +0.4607 with interval 0.2052 to 0.7659.
Redundancy is low, a total-variation distance of 0.345, top-probability correlation 0.057 and argmax
agreement 21 percent, so the bundles really are different views. Leave-one-out costs 0.062 log loss
for the issuer facts and 0.030 for the market state, so both earn their place. The ordinal decision
view acts on 15.9 percent of cases at 33.8 percent exact hits, and on 2.6 percent at 66.7 percent.
**Evidence**: `results/complex-council.json`; `scripts/run_complex_council.py`;
`tests/test_complex_council.py`; `hpc/probabilistic-council/panel_council.py`.
**Scope**: development only, complex names, one split from the council's own partition design, the
peer map declared in the runner and not part of any frozen recipe, flat costs irrelevant because the
target is a distribution and not a trade.
**Consequence**: fusion beats both singles and concatenation on the surviving sleeve's panel, which is
the second independent council win after the RPO breadth panel (T46's sibling comparison), and it is
the first with both intervals excluding zero. The council belongs in the pipeline for the complex, and
the specialists themselves remain weak enough that the gain is relative rather than absolute.

## T55. Composition is not the driver of the recent record, and the same names still fail one era

**Statement**: the matched-universe test runs one name set, the 32 complex companies whose prices reach
back before 2017, across extended annual origins from 2011. In the recent era the matched names give
+30.15 percent net at Sharpe 0.683 against +27.65 percent at Sharpe 0.756 for the full complex, a
difference of -12.87 percent whose interval spans -184.8 to +138.3, so **the recent record is not a
composition artefact**: the same names deliver it. Across eras on those same names: 2011-2014 +27.96
percent at Sharpe 0.535 with a -32.4 percent drawdown, **2015-2018 -16.70 percent at Sharpe -0.738 with
a -51.0 percent drawdown**, 2019-2022 +38.68 percent at 0.806, 2023-2026 +20.81 percent at 0.527. The
stitched extended record is +17.90 percent at Sharpe 0.438 over 2,056 sessions, dragged by the middle
era.
**Evidence**: `results/matched-universe.json`; `scripts/run_matched_universe.py`;
`tests/test_matched_universe.py`.
**Scope**: development only, revenue sleeve only because the intensity sleeve's signals begin in 2017,
flat twenty basis point costs because volume does not exist before 2017, and the matched set is still
compositionally different from the recent one even though the names are constant.
**Consequence**: a naive backward extension would have been improper, and this test shows why the
honest extension looks as it does: the effect is regime-dependent, appearing when the complex is an
active buildout theme and failing in 2015-2018 when it was not, and it is not an artefact of which
names exist today. The fixed-era record stays primary; the matched extended record is the declared
secondary, never merged with it.

## T56. Recalibrating the gate does not help, because the miscalibration is era specific

**Statement**: a single temperature fitted on the earlier sixty percent of walk-forward
out-of-sample revenue predictions chooses T = 3.75 and improves the negative log likelihood from 1.6757
to 1.5724, confirming the overconfidence T54 found. On the held-out later forty percent it makes
calibration **worse**: expected calibration error 0.0572 raw against 0.1279 recalibrated. The engine
agrees: on the T44 window, the raw gate returns +11.29 percent net at Sharpe 1.043 with a -16.3
percent drawdown, the recalibrated gate +11.00 percent at 1.021 with -16.7 percent, a difference of
-0.31 percent with interval -1.95 to +1.28. Doubled costs keep the same order. The ungated run stays
at -9.49 percent.
**Evidence**: `results/gate-recalibration.json`; `scripts/run_gate_recalibration.py`;
`tests/test_temperature_scaling.py`.
**Scope**: development only, one scalar temperature cannot fix class-specific overconfidence, and the
fitted period and the evaluated period are both out of sample with respect to the classifier but not
with respect to each other.
**Consequence**: the gate keeps its raw probabilities, and the declared falsifier of the recalibration
stage fired. The deeper finding is that the model's miscalibration is not stable across periods, so
calibration fixes must be fitted and validated inside the same era, and the forward window is where
that will be tested.

## T57. Margins do not price and assets cannot be scored under the declared bins, and both were caught by clocks and label geometry

**Statement**: the margins panel (`OperatingIncomeLoss`, `NetIncomeLoss`, `GrossProfit`, 6,544 rows,
59 tickers) carries the **same 403-day latest-filed clock defect** as the original capex and revenue
panels. Rebuilt from the same raw cache with the earliest filing it keeps an identical 6,544 rows and
its median lag falls to 36 days, which is the fix, not a finding about returns. On the corrected clock
the operating-income expectation gap has 2,267 measured events and **does not price**: twenty-session
long-short by predicted bin is -0.98 percent month neutral with interval -3.58 to +0.75 and -0.45
percent month and group neutral with interval -2.68 to +1.29, with information coefficients near
-0.03. It is declined as a sleeve. The assets panel is clean at a 37-day median lag with 3,009
measured events, but under the declared bin edges its surprises are degenerate: most quarterly asset
changes fall inside the middle bin, the model predicts one class, and **the long-short spread cannot
be formed at all**. That is a label-geometry mismatch, not a clock or data problem.
**Evidence**: `results/complex-margins-quarterly-pit.csv`; `results/margins-vintages.csv`;
`results/assets-vintages.csv`; `results/margins-surprise.json`; `results/assets-surprise.json`;
`scripts/build_driver_vintages.py` `--level`; `tests/test_driver_vintages.py`.
**Scope**: development only; margins measured on 625 test rows after the split; assets scored on none
because no side exists; both are complex names with the same price and cost conventions as T43.
**Consequence**: neither candidate is added as a sleeve. Assets and margins get one more fair test
only through a **concept-agnostic surprise scaling**, a declared z-score of the change against its own
trailing volatility before binning, which is the next declared variant and must be tested on the
surviving revenue sleeve as well before it is adopted anywhere.

## T54. The surviving sleeve's model is honest in the tails and overconfident in its confident calls

**Statement**: out-of-sample predictions from the revenue model, pooled across eight rolling origins,
1,144 rows, five classes. The reliability table is close in the bulk, gaps of +0.040 at a mean
confidence of 0.268, -0.064 at 0.339 and -0.082 at 0.437, and clearly **overconfident when it is
confident**: -0.200 at 0.547, -0.321 at 0.738 and -0.188 at 0.855. Pooled ECE 0.0683 with a
resampled interval of 0.0440 to 0.0971, maximum bin error 0.321, sharpness 0.354. The extreme classes
are honest: the lowest class is predicted at 0.135 and realised at 0.144, the highest at 0.231 and
0.248, so the marginal tails of the distribution are slightly under-confident. Return tails, walk
forward: the revenue sleeve has a five percent value at risk of -3.09 percent, expected shortfall
-5.15, a worst day of -27.7 and a worst twenty-session window of -31.2 percent. The gated intensity
sleeve is -0.70, -1.11, -3.5 and -7.5. The combined inverse-volatility portfolio is -0.90, -1.49,
-5.74 and -8.4 percent, and volatility-targeted -0.99, -1.50, -4.70 and -8.7.
**Evidence**: `results/calibration-report.json`; `scripts/run_calibration_report.py`;
`src/filing_specialist/calibration_diagnostics.py`; `tests/test_calibration_diagnostics.py`;
`docs/plan/variant-registry.jsonl`.
**Scope**: development only, pooled origins are not independent, five classes make bins coarse.
**Consequence**: any confidence gate must be calibrated, because the rows a gate would act on are
exactly the overconfident ones; the extreme-bin honesty is what makes the tail-focused decision rule
defensible. T56 later tested the calibration fix and found the miscalibration era-specific, so the gate
keeps its raw probabilities. The variant registry records every tried variant from 38 entries onward
and states plainly that the historic count before it is not fully reconstructible.
**Restored 2026-10-04**: this entry was dropped by another session's rewrite of this shared file and
re-added from its artifact. Check the ledger's numbering after any shared-file rewrite.

## T58. The standardized surprise ranks better and trades worse, so the sleeve keeps raw labels

**Statement**: scaling each surprise by its own ticker's trailing volatility of quarterly changes,
with declared edges at -1.5, -0.5, +0.5 and +1.5 and a clip at five, is a declared variant tested on
identical rows. At the driver level it **improves** the revenue ranking: on the same 1,706 measured
events, the twenty-session long-short spread moves from +0.0317 month neutral with interval -0.0952 to
+0.1490 and +0.0262 month and group neutral with interval -0.0197 to +0.0642, to **+0.2447** and
**+0.1275** respectively, roughly a five-fold gain in the neutral arm. At the sleeve level it
**loses**: the walk-forward revenue sleeve returns +18.39 percent at Sharpe 0.405 with a -57.5 percent
drawdown against the raw sleeve's +27.65 percent at 0.756, with two negative years (2020 and 2021)
where the raw sleeve is positive every year, and the composite without capex falls from Sharpe 1.493
to 1.176. The mechanism is visible in the counts: the raw labels put 635 events in the two extreme
bins and the standardized labels 250, so the sleeve harvests fewer, better-ranked trades and the
position sizing cannot make up the difference. Assets and margins remain unusable: the standardized
labels are well distributed at last (assets 218, 407, 1,346, 544 and 430 across the five bins) but the
fitted model still does not separate them, so no long or short side can be formed at all.
**Evidence**: `results/revenue-z-on-pit.csv`; `results/assets-vintages-z.csv`;
`results/margins-vintages-z.csv`; `results/revenue-surprise-z.json`; `results/walk-forward-z.json`;
`results/assets-surprise-z.json`; `results/margins-surprise-z.json`;
`scripts/build_driver_vintages.py --scale zscore`; `tests/test_driver_vintages.py`;
`tests/test_rpo_specialist.py`.
**Scope**: development only; the A/B shares rows, prices, costs and the decision rule, so the
difference is the target definition alone. The driver gain is measured on the same 1,706 events.
**Consequence**: the revenue sleeve keeps raw bins, and the standardized surprise is kept only as an
input for **sizing and selection decoupling**, a declared untried variant in which raw extremes select
the trade and the standardized value sizes it. A concept-agnostic target alone does not rescue assets
or margins, so their decline stands.

## T59. Decoupled sizing lifts the revenue sleeve and its Sharpe, worsens the drawdown, and does not separate from zero at the composite

**Statement**: the declared T58 follow-up keeps the raw model's selection and sign and caps each
position's size by the standardized surprise, `min(1, |z| / 2)`. On the same walk-forward window the
revenue sleeve moves from **+27.65 percent at Sharpe 0.756** to **+37.56 percent at Sharpe 0.942**, its
2020 loss improves from -23.6 percent under the pure z-variant to -5.8 percent, and 2021 turns positive
at +2.2 percent, but one year of eight is now negative where the raw sleeve is positive in all eight.
The two-sleeve composite without capex moves from +17.35 percent at Sharpe 1.493 with a -12.3 percent
drawdown to +17.90 percent at **1.525** with a **-14.6** percent drawdown, and volatility-targeted from
1.376 at -10.2 to 1.408 at -12.3. The month-blocked difference of the composite's daily series has a
point of +0.68 percent with interval -2.62 to +3.83 and 66.4 percent of ninety months positive, so it
**spans zero**: the Sharpe gain is not separable from noise at the portfolio level, while the
drawdown cost is measured directly.
**Evidence**: `results/walk-forward-decoupled.json`; `results/walk-forward-baseline.json`;
`scripts/run_walk_forward.py --size-panel`; `scripts/run_walk_forward.py` `scaled_conviction` and
`load_size_lookup`.
**Scope**: development only; both arms share rows, prices, costs, origins and the intensity sleeve, so
the difference is the sizing rule alone. The interval is blocked by month, ninety blocks.
**Consequence**: the raw-conviction sleeve stays the headline and the decoupled rule is a declared
candidate that the forward window must separate. It is the first variant in this series that improves
the sleeve's Sharpe without improving its drawdown, so the next honest test of it is the forward
window's own falsifiers, not another development pass.

## T60. The fusion wins on the score and loses on the positions: the single specialist keeps the sleeve

**Statement**: the council was run as a sleeve, three declared blocks fused by a simplex-weighted
linear opinion pool whose weights are fitted on the last fifth of each fold's training rows, with the
fused expected class as the position's conviction on the same annual origins, prices and costs as the
surviving sleeve. The council sleeve returns **+21.11 percent at Sharpe 0.528 with a -74.0 percent
drawdown** against the single-specialist sleeve's **+27.65 percent at 0.756 with -58.1 percent**, and
its two-sleeve composite falls from Sharpe 1.493 to **0.980**, with the month-blocked difference of the
daily composite series at -5.35 basis points and interval -12.06 to +1.11, positive in only **5.3
percent** of ninety months. Equal-weighting the council's signals is worse still, +15.85 percent at
0.456, so the loss is not a sizing artefact. The mechanism is measured: on the 449 rows whose realised
label is extreme, the council's log loss is better than the single specialist's, **1.6102 against
1.8288**, while its directional hit rate is slightly **worse**, 61.7 percent against 62.6 percent. The
fusion improves the distribution and smooths the expected class, and the sleeve earns its return from
the direction of the extremes.
**Evidence**: `results/council-sleeve.json`; `results/council-sleeve-sign.json`;
`scripts/run_council_sleeve.py`; `tests/test_council_sleeve.py`; the per-fold pool weights in the
artifact; `results/walk-forward-baseline.json` for the baseline arm.
**Scope**: development only; the pool grid is coarse at eighths and is allowed to collapse onto a
single specialist, so the fusion is not handicapped; the peer map and the peer-momentum block are
declared in this runner and are not a frozen recipe.
**Consequence**: the acceptance criterion of the fusion stage is **not met** and the single-specialist
sleeve stays the headline. The council keeps its demonstrated role where calibration is what matters,
the decision layer, and the declared follow-up is a split rule: the single specialist sets direction,
the council's better-calibrated distribution sets size. That is a variant, not a claim, and the forward
window remains the only place a claim can be earned.

## T61. Every fusion variant loses to the single specialist, so the fusion family as a sleeve driver is closed

**Statement**: the declared T60 follow-up, the specialist's direction with the fused distribution's
magnitude, was measured on the same folds, prices, costs and window as the other arms. It recovers the
net return but not the quality: **+27.96 percent at Sharpe 0.702 with a -65.7 percent drawdown** against
the single specialist's **+27.65 at 0.756 with -58.1**, and its two-sleeve composite reaches Sharpe
**1.100** against the baseline 1.493 with the month-blocked difference positive in only 11.0 percent of
ninety months. The full family, all on the same window: council conviction +21.11 at 0.528 with
composite 0.980, council sign +15.85 at 0.456 with composite 0.926, split +27.96 at 0.702 with
composite 1.100, and the single specialist +27.65 at 0.756 with composite 1.493. Every fused variant
loses, and the split rule improves on both of the others, which confirms the mechanism T60 measured
rather than contradicting it.
**Evidence**: `results/council-sleeve-split.json`; `results/council-sleeve.json`;
`results/council-sleeve-sign.json`; `results/walk-forward-baseline.json`;
`scripts/run_council_sleeve.py` `split_conviction`; `tests/test_council_sleeve.py`.
**Scope**: development only; one sizing formula per variant, no search over the split's clip, and the
pool grid is coarse at eighths.
**Consequence**: no further fusion-for-positions variant is worth a development run: the score-optimal
fusion does not produce the directional exposure the sleeve needs, and the measurement has been made
three ways. The council keeps its role in the decision layer and in the calibration of size, where it
is scored rather than traded. Development levers on this line are now exhausted, and what remains is
the forward window, the risk-track execution work on its five dates, and the vision gaps.
