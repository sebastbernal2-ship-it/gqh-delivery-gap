# Parallel legs: the four builds that feed the six gates

One writer per path. Four legs run at the same time. Each leg owns its own output files and touches nothing else,
so no leg can collide with another, and the results all arrive in time for the gate work.

Read before starting, in this order: `docs/plan/intent.md` (reporting order and bans), `docs/plan/data-access.md`
(what is reachable and how), `docs/market/SCHEMA.md` (participant, flow, instrument, mapping), `docs/truths.md`
(what is already established, so nobody re-derives it).

**Bans that apply to every leg.** No em dashes anywhere. No process narration. No performance table as the
headline. No claim without a falsifier. No committed credentials, ever: the repository is public, and any query
that needs a credential goes through a GitHub workflow that returns the result, never the key. Do not commit: the
orchestrator commits after checking, because the git index in this checkout refuses direct writes.

**The store, briefly.** TigerData is read directly (the `tiger` command line client) and holds the 21 source
landings plus the compute archive. Snowflake holds the richer research layer and is read only through
`.github/workflows/snowflake-query.yml`, dispatched with `gh workflow run` and downloaded with `gh run download`.
The tables worth knowing: `EIA860M_GENERATOR_VINTAGES` at 3.4 million rows, `SEC_FILING_DOCUMENTS` at 11,892,
`RESEARCH_ACQUISITION_ROWS` at 433,781, `SOURCE_RECORDS` at 151,198, `AWS_GPU_SPOT_PRICES` at 1.59 million.

## Leg A: the graph inventory, from the richer store

**Question.** What do we own now, in full resolution, node by node, with its real coverage and its availability
time?

**Inputs.** Snowflake tables listed above, and the node space in `docs/scan/nodes.jsonl`.

**Deliverables.** `results/graph-inventory.csv` with one row per node: node id, family, representation, source
table, rows available, first and last observation, availability rule, and status. Plus `docs/plan/leg-a-report.md`
stating which nodes gained rows against what the earlier inventory claimed, and which declared nodes have no
backing table at all.

**Acceptance.** The CSV has at least as many rows as nodes, every row names a real source table, and the report
names the three biggest coverage gains with their row counts.

**Writes only:** `results/graph-inventory.csv`, `docs/plan/leg-a-report.md`, and any helper script under
`scripts/leg_a_*.py`.

## Leg B: the distribution of everything, including the distribution of its own volatility

**Question.** For every node we can measure, what does its distribution look like, and how stable is its scale?

**Deliverables.** `scripts/build_distributions.py` producing `results/node-distributions.csv` with one row per
node series: length, mean, standard deviation, rolling twelve month standard deviation, the ratio of the standard
deviation of that rolling value to the overall value (a scale stability measure), skew, kurtosis, minimum, maximum,
and the fraction of months in the top decile of scale. Plus `docs/plan/leg-b-report.md` naming the most and least
stable series, and any series whose scale changes by an order of magnitude.

**Acceptance.** The script runs from a clean checkout path, the CSV has at least fifteen rows, and every row states
its window so nobody mistakes a short series for a stable one.

**Writes only:** `scripts/build_distributions.py`, `results/node-distributions.csv`, `docs/plan/leg-b-report.md`.

## Leg C: the association engine, directional instead of symmetric

**Question.** Which relations survive when direction is imposed and multiplicity is controlled?

**Why.** The earlier scan measured symmetric co-movement, which is a relation and not an edge. Direction is what a
position needs: which series moves first, and how much of the other's move follows.

**Deliverables.** `scripts/run_directional_scan.py` producing `results/association-edges.csv` with one row per
ordered pair: from node, to node, months aligned, lead correlation at lags zero through three in both directions,
the better direction, the permuted null's ninety fifth percentile, a q value across the whole grid, the family
split (within one family or across), and a verdict. Plus `docs/plan/leg-c-report.md` listing survivors in order of
strength with the two strongest reported for both directions so nobody reads a direction into noise.

**Acceptance.** At least fifty rows, every row carries both directions and a q value, the report states the
survivor count against the expected count, and the development windows only are used: the holdouts are spent and
closed, so nothing in this leg may touch them.

**Writes only:** `scripts/run_directional_scan.py`, `results/association-edges.csv`,
`docs/plan/leg-c-report.md`.

## Leg D: chains, from surviving edge to economic chain

**Question.** For each relation that survives, who pays, what moves, and which instrument carries it?

**Deliverables.** `docs/market/chains.jsonl`, one record per candidate chain with fields: id, the edge it comes
from, the measured nodes involved, the forced payer, the constraint type, the transfer and its unit, the
instrument and its concentration, the barrier, the falsifier, and the data needed to test it. Plus
`docs/plan/leg-d-report.md` scoring each chain against the six gates and naming where each fails.

**Acceptance.** Every chain names a payer in one sentence and an instrument that appears in
`docs/market/map.jsonl`. Chains that cannot name a payer are recorded as failed at gate one rather than dropped.

**Writes only:** `docs/market/chains.jsonl`, `docs/plan/leg-d-report.md`.

## What the orchestrator does with the results

Merge the four legs, then run the six gate process over the chains that pass gate one, with the measured
distributions from Leg B and the directional edges from Leg C as the evidence, and the graph inventory from Leg A
as the coverage check. Nothing from a leg is accepted on the leg's own say so: numbers are re-run at merge time.
