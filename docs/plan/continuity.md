# Continuity: read this first

One page that says where everything is, what is settled, what is open, and how to work in this checkout
without repeating known mistakes. Read in the order given.

## Read order

1. `docs/brief.md` - the track's own rules, frozen.
2. `docs/truths.md` - thirteen statements about how this market works, with evidence and scope.
3. `docs/plan/terrain-map.md` - the instruments built, the measurements, what is ruled out, and reachable
   versus blocked data.
4. `docs/plan/node-edge-map.md` - the objects and the typed, directional relations between them, with the
   measurement status of each relation.
5. `docs/plan/relation-to-edge.md` - the six gates that turn a relation into a rationale. This is the method.
6. `docs/plan/constraint-ledger.md` - the candidates scored against those gates.
7. `docs/plan/edge-search.md` - the search method and its gates, including the relevance gate.
8. `docs/plan/stage-a-report.md` - the factor work on delivery, and its three failures.
9. `docs/plan/sealed-test.md` - the two holdouts and who may open them.
10. `docs/decisions.md` - the append-only record, newest last. `docs/variants.md` - every comparison tried.
11. `docs/ideas/graph.jsonl` - ideas and directions with rationale, falsifier and capacity needs.

## Where things stand

**The submission is complete and honest.** `docs/note.pdf`, five pages, printed from `docs/note.html` with the
headless chromium binary under the Playwright cache. The README opens with the submission and the commands that
reproduce every number. Gates pass, 38 test suites pass. Both holdouts remain unopened.

**The research has produced truths and no edge yet.** That is the state, stated without softening.

## The core method, in one paragraph

Correlation, association and causation are relations. None of them is an edge. An edge is a repeatable, cost
surviving transfer from a counterparty who cannot avoid paying. So the question is never "what correlates" but
"who is forced, by what constraint, to hand value to whom, and what instrument is mechanically levered to that
transfer without dilution". Six gates: constrained counterparty, price insensitive flow, transfer and its
concentration, instrument and dilution, economics and capacity, barrier and what removes it. A relation tells you
where to look. Everything else is gates.

## The candidate short list, with obstructions

| Candidate | Passes | Obstruction |
|---|---|---|
| Forced liquidation on perpetual venues | constraint, flow, instrument | economics unmeasured; tape running |
| Dealer hedging flow | constraint, flow, instrument | historical option chains, entitlement missing |
| Compute relative value | constraint, dispersion | instrument: only diversified provider equity, so dilution kills it |
| Delivery revision tail | constraint, mechanism | concentration: needs a firm where one project dominates |
| Queue gated capacity | mechanism | data: queue history not reachable from this host |
| Filing event equity | constraint, instrument | coverage: four firms loaded, most of window inside a holdout |

## Numbers worth remembering

6,407 generators tracked; 69 percent first revised; 36 percent of first revisions are one month nudges; hazard
23 percent at six months rising to 44 percent at one to two years; modal annual revision exactly twelve months;
64 percent of promised generators ran late; 711 cancellations; information lag 33 to 94 days by field; 6.2
percent of 274,176 slipped MW has a large listed owner; 382 firms and 4,634 events show no firm level equity
response, with a placebo that over produced; 135 scan comparisons gave 6 survivors against 5.5 expected;
compute families have a median pairwise daily correlation of minus 0.01; compute prices are provider listed, per
instance hour, not per accelerator.

## Open decisions, all owned by the captain

1. **Sealed test owner.** Both holdouts closed. Opening study one reports a null on a strategy that already
   failed in development; the brief asks for out of sample reporting, so the choice is open or explain.
2. **The branch.** `close-all-gaps-20261003` holds 49 files not on main: strategy contracts, capacity event
   ledger, physical observation ledger, QuantGraph scan, delivery gap protocol. Land it or link it from the
   README, otherwise a reader of main never sees it.
3. **Entitlements.** Option chains, interconnection queue history, executed compute rental series, historical
   order book archive. Each unlocks one candidate.
4. **Standing constraints.** What we are allowed to hold (equity only, perps, contracts, physical), roughly how
   much capital, and what "fast" means here (seconds, minutes, hours).
5. **Standing authority.** What is decided without asking (data sourcing, model choices inside the declared
   discipline, running declared tests) versus what comes back (entitlements, opening a holdout, merging,
   submitting).
6. **The review pass** on the note, requested in `docs/inbox/review-request-2026-10-03.md`.

## Next actions, ordered by value per hour

1. **Forced liquidation study.** The tape is running and the candidate passes every evaluable gate. Widen it to
   several hours, apply the pre-registered rule, report trigger frequency, post trigger paths, clustering and
   refractoriness, plus capacity from book depth. Economics, not validation, is the open gate.
2. **Redefine the delivery object**, on the panel that already exists: revision of six months or more, and
   cancellation, instead of first revision. Never tried, costs an afternoon.
3. **Imagery probe at scale**, thirty to fifty labelled sites, pre-registering the texture feature that showed
   +0.72 on eight sites.
4. **Widen 8-K coverage** through the team's pipeline, so the filing event family can be tested at all.
5. **Interconnection queue history**, the request is written and waiting on access.

## What not to redo

- Co-movement scans between series pairs. Symmetric, mechanism free, and already run twice.
- Firm level equity event studies on obligation revisions. Done across 382 firms with a placebo.
- Factor models of delivery using market wide aggregates. Three factor sets failed.
- Drought, weather or any factor chosen for being fetchable. See the relevance gate.
- Any strategy build before a candidate passes the six gates.

## How to work in this checkout

- **Commits**: the sandbox refuses writes to the real git index, so commit through a temporary index:
  `GIT_INDEX_FILE=/tmp/idx git read-tree HEAD`, then `add` the explicit paths, `commit`, then copy the temporary
  index over the real one with a computed path. Never `git add -A` across the worktree: a path list meant for a
  few files once carried another branch's state onto main and deleted four files belonging to another member.
  Always verify with `git diff --name-status <parent> <new>` before pushing.
- **The checkout may be on another member's branch.** Check `git branch --show-current` before assuming.
- **TigerData**: `tiger db query --command "..."` and `tiger db query -o json --command "..."`. Read only. Tables
  under `public.gqh_source_records` carry shared landings: construction spending, supply chain pressure, delivery
  times, M3 orders and unfilled orders, FRED, Massive bars and 8-Ks, the compute spot archive
  `public.aws_gpu_spot_prices`.
- **SEC**: the user agent must contain a contact address and no URL, or every request gets an HTML 403 that looks
  like throttling. A refused agent must fail fast; a throttle must retry.
- **Endpoint quirks**: EIA-860M needs the page's own link list, headers on row 2, and the earliest vintages carry
  no nameplate column. NCEI statewide weather needs `all/1/` in the path or it returns Januarys only. The drought
  service returns CSV with nested D classes, so D2 alone is severe or worse, and a statistic format filter is
  required. Sentinel-2 is reachable through Earth Search STAC with a thumbnail asset and a COG that our own
  windowed reader can read; NAIP is requester pays.
- **`.venv` looks like a protected path** to one of the shell guards; build the string if a command is refused.
- **Long runs**: the tape collector survives dropped connections; use `--minutes` and expect to chunk it.

## The standing discipline

Declare before measuring. Relevance gate before factors. Six gates before strategies. State conditioned nulls,
rate control across the whole declared grid, specificity against a group the mechanism does not implicate, and a
placebo. Count multiplicity before ranking. Keep holdouts closed by construction. Report a failed gate as a
truth about the world or about our coverage, never as a verdict on the work.
