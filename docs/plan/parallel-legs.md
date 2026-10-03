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

**Deliverables.** `scripts/leg_b2_build_distributions.py` producing `results/leg-b-node-distributions.csv` with one row per
node series: length, mean, standard deviation, rolling twelve month standard deviation, the ratio of the standard
deviation of that rolling value to the overall value (a scale stability measure), skew, kurtosis, minimum, maximum,
and the fraction of months in the top decile of scale. Plus `docs/plan/leg-b-report-2.md` naming the most and least
stable series, and any series whose scale changes by an order of magnitude.

**Acceptance.** The script runs from a clean checkout path, the CSV has at least fifteen rows, and every row states
its window so nobody mistakes a short series for a stable one.

**Writes only:** `scripts/leg_b2_build_distributions.py`, `results/leg-b-node-distributions.csv`, `docs/plan/leg-b-report-2.md`.

## Leg C: the association engine, directional instead of symmetric

**Question.** Which relations survive when direction is imposed and multiplicity is controlled?

**Why.** The earlier scan measured symmetric co-movement, which is a relation and not an edge. Direction is what a
position needs: which series moves first, and how much of the other's move follows.

**Deliverables.** `scripts/leg_c2_directional_scan.py` producing `results/leg-c2-association-edges.csv` with one row per
ordered pair: from node, to node, months aligned, lead correlation at lags zero through three in both directions,
the better direction, the permuted null's ninety fifth percentile, a q value across the whole grid, the family
split (within one family or across), and a verdict. Plus `docs/plan/leg-c-report-2.md` listing survivors in order of
strength with the two strongest reported for both directions so nobody reads a direction into noise.

**Acceptance.** At least fifty rows, every row carries both directions and a q value, the report states the
survivor count against the expected count, and the development windows only are used: the holdouts are spent and
closed, so nothing in this leg may touch them.

**Writes only:** `scripts/leg_c2_directional_scan.py`, `results/leg-c2-association-edges.csv`,
`docs/plan/leg-c-report-2.md`.

## Leg D: chains, from surviving edge to economic chain

**Question.** For each relation that survives, who pays, what moves, and which instrument carries it?

**Deliverables.** `docs/market/leg-d-chains.jsonl`, one record per candidate chain with fields: id, the edge it comes
from, the measured nodes involved, the forced payer, the constraint type, the transfer and its unit, the
instrument and its concentration, the barrier, the falsifier, and the data needed to test it. Plus
`docs/plan/leg-d-report-2.md` scoring each chain against the six gates and naming where each fails.

**Acceptance.** Every chain names a payer in one sentence and an instrument that appears in
`docs/market/map.jsonl`. Chains that cannot name a payer are recorded as failed at gate one rather than dropped.

**Writes only:** `docs/market/leg-d-chains.jsonl`, `docs/plan/leg-d-report-2.md`.

## What the orchestrator does with the results

Merge the four legs, then run the six gate process over the chains that pass gate one, with the measured
distributions from Leg B and the directional edges from Leg C as the evidence, and the graph inventory from Leg A
as the coverage check. Nothing from a leg is accepted on the leg's own say so: numbers are re-run at merge time.

## The constraint that makes parallel legs fail, and the corrected pattern

A subagent started in this home is a **separate session**, and this home allows one live session at a time
through `state/.lock`. When four legs started together, the first held the lock and the rest read the lock,
went read-only by their own guard, and refused to write anything. One leg reported it plainly: another live
session holds the lock, so nothing was written.

**So a leg may not write into the locked home or the checkout.** The corrected pattern is:

1. Each leg works in its own scratch directory, for example `/tmp/leg-a/`, and writes its deliverables there.
2. The leg reports the scratch paths and the numbers it verified.
3. The orchestrating session, which holds the lock, copies each verified result into the repository, re-runs
   the leg's verifier itself, and commits.

That keeps the one-writer-per-path rule intact, because only the orchestrator writes inside the checkout.
When a leg genuinely needs the checkout, the alternative is a worktree with its own home so its lock is its
own, which is what `subagent_spawn_worktree` exists for.

## What actually blocks a second session, from the harness source

`bin/fm-lock.sh` refuses when another live process holds `state/.lock`, and `bin/fm-session-start.sh` reacts by
setting its own read-only mode and running the guard with `FM_GUARD_READ_ONLY=1`. So the block is not a property of
the repository path: a second session in the same home is put into read-only mode by its own startup, and it then
declines to write at all.

Three consequences, in order of cost:

1. **The reliable way to get several writers is one home per writer.** A child with its own `FM_HOME` acquires its
   own lock, is not read-only, and can write its own scratch directory. `subagent_spawn_worktree` is the supported
   form of this, since it hands the child a managed worktree and its own lifecycle record.
2. **A child without its own home should be treated as a read-only analyst.** It can read everything and report
   findings and tables, and the orchestrator, which holds the lock, writes the files. That is slower to set up but
   it cannot fail for a lock reason.
3. **A scratch directory outside the home is not proven to work**, because the read-only mode is imposed by the
   child's own startup rather than by the path it writes. Treat it as unverified until a probe child writes a file
   and reports success.

The unsettled question, stated rather than guessed: whether several children each with their own home can write at
the same time in this harness. The decisive test is two probe children with separate homes, each writing one file
and reporting. Until that test runs, the safe pattern is one writer per home, or children as analysts.

## The reframing that removes the block: collecting is not mutating fleet state

The read-only banner concerns **fleet state**. It stops a session from spawning, steering, merging, draining the
wake queue, or repairing supervision. It does not describe the work these legs do. A leg reads the store, calls
a workflow, computes, and produces a table. That is data collection and analysis, not fleet mutation.

So a leg does not need write access to the repository at all. The pattern is:

1. **The leg reads and computes.** Reading TigerData, dispatching the Snowflake query workflow and downloading its
   artifact, and running local analysis are all allowed in a session that is read-only for fleet purposes.
2. **The leg returns its result through its completion message.** A table of survivor counts, an edge list, a
   ranking, a chain scored gate by gate: all of that fits in a report.
3. **The orchestrator persists it.** The session that holds the lock writes the artefact into the repository, runs
   the leg's verifier itself, and commits.

That is also cleaner than scratch files, because nothing needs to be copied and the reported numbers are the
numbers the orchestrator checks. The only thing a leg must not do is touch fleet state, and none of these legs
does.
