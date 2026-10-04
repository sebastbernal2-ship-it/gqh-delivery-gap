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
one minute moves, funding beyond two sigma, thin books) land between -8 and -22 basis points net of base
costs, with gross means of at most +3.9 basis points at fifteen minutes, all inside their random-time
nulls. The frozen conjunction fired six times, and its gross reversion at fifteen minutes is +17.9 basis
points: +6.9 net of base costs, -4.0 net of doubled costs, permutation p 0.085. Reversion is market
specific, SPX +14.7 against GAS -4.0 on the same level.
**Evidence**: `results/cascade-reversion-study.json`; `scripts/build_cascade_reversion_study.py`;
`data/tape`.
**Scope**: one recorded window, four markets (BTC, ETH, GAS, SPX), one venue, 7.3 nominal hours, entry at
the condition bar close with no speed advantage used; development only.
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

**Statement**: resting at the dislocation extreme fills 33 percent of frozen conjunction events, 47
percent at the top one percent level, and 42 percent at the top five percent and thin book levels. The
paired result against taker entry is +4.6 to +17.3 basis points on the same events, but the absolute
maker net is at or below zero everywhere except +0.83 and +2.64 basis points at fifteen minutes on two
levels, both inside their nulls. The filled and unfilled split shows adverse selection: at the frozen
conjunction the two filled events net -13.2 basis points under the taker convention against +17.0 for the
four unfilled ones, and filled events are worse than unfilled at every level and horizon. A stricter fill
rule, standing in for queue position, removes the good fills and keeps the bad ones: at the top one
percent level the net falls from +0.83 to -1.84 to -3.02 basis points as required penetration rises from
zero to half a spread to a full spread.
**Evidence**: `results/maker-entry-study.json`; `scripts/build_maker_entry_study.py`; `data/tape`.
**Scope**: recorded window, four markets, one venue, best bid and ask snapshots at fifteen seconds, no
queue position modelled; development only.
**Consequence**: the binding constraint is fill selection. The positive maker cells are an artifact of
optimistic fills, so maker entry is a size tool rather than a source of edge on this window, and the
reversion that exists is taken immediately at the event.

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
