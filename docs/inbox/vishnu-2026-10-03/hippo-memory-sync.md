# Hippo unified-memory synchronization task

**Owner:** Vishnu's handoff workstream (`vshnu1`).
**Purpose:** a contributor on a machine with Hippo completes the shared-memory step that could not
run on the authoring machine. This file is a task packet, not the shared memory itself.
**Snapshot to reconcile:** repository state after `9d3b876` and this packet's commit. Re-read live
`main` before capturing anything.

## Request to the contributor

Please update this project's Hippo store from the durable project records, then publish its
filtered shared-memory view to Git. Do not merely add this whole packet or the 700-line handoff as
one giant memory. Hippo is a concise recall index; the repository remains the source of truth.

The objective is that a contributor opening a later session can promptly recall:

1. the current strategic preference and what is explicitly *not* approved;
2. the economic hypothesis and its missing evidence;
3. validated versus provisional data/warehouse state and their caveats;
4. the major revisions, negative results, and method rules that must not be forgotten;
5. the technical implementation readiness and blockers; and
6. where the canonical evidence lives so memories do not become a second mutable database.

Use dates and status labels for facts that may age. Preserve the distinction between user preference,
team decision, measured finding, and unresolved question. Do not convert discussion into a settled
decision merely because it appears repeatedly in chat.

## Required source review before writing memory

Run `make sync` from the repository root, then read the current versions of:

- `AGENTS.md`, `docs/memory.md`, `memory/SHARED.md`, `docs/CURRENT.md`, `docs/brief.md`,
  `docs/decisions.md`, and `OWNERS.md`;
- [`ultimate-handoff.md`](ultimate-handoff.md), especially its verified data inventory, caveats,
  chronology of revisions, implementation status, testing, and next actions;
- [`strategy-feature-contract.md`](strategy-feature-contract.md),
  [`central-ingest-handoff.md`](central-ingest-handoff.md),
  [`source-audit.md`](source-audit.md), and [`technical-boundaries.md`](technical-boundaries.md);
- [`thinking history`](../../thinking/vishnu-2026-10-03.md), plus any newer canonical records
  that have appeared on `main` since the handoff commit.

The packet does **not** supersede later decisions, results, or cloud receipts. Resolve every
candidate below against those live records and record only facts still true/useful. In particular,
check whether the SEC archival process has finished and whether Snowflake receipts exist before
calling raw filings available. A process reported running in the handoff is not proof of current
completion.

## Suggested concise project memories

These are candidate themes, not copy/paste requirements. Prefer a handful of durable entries over
one entry per paragraph. Each item should be its own `hippo remember` entry with the `gqh` tag.

### A. Strategic position and non-decisions

Capture that Vishnu's current preference is **equity-first** and economically grounded, studying
public delivery/capacity revisions against earlier expectations. Candidate names PWR, ETN, EME,
DLR and SPY benchmark are a feasibility basket—not an approved universe, pair, signal, horizon, or
long/short portfolio. The thesis ledger remains authoritative; until it contains an active claim,
do not say the team has approved a strategy. The team's separate delivery-revision-to-executed-
compute-rental edge is an untested candidate, not a silent switch in the equity-first direction.

Source: `docs/CURRENT.md`, `docs/decisions.md`, `docs/alignment.md`,
`docs/inbox/vishnu-2026-10-03/ultimate-handoff.md`.

### B. Economic question, measurement, and falsification

Capture the causal chain under study: a **new public revision** in physical delivery/capacity,
relative to an earlier public expectation, may alter company economics and predict subsequent
abnormal equity returns after ordinary news, market/sector exposure, and costs. It is not
established. Measure magnitude/timing/revision and company exposure—not just a binary event. Compare
against the firm's own prior public guidance first; do not represent a current consensus snapshot as
historical point-in-time expectations. Realized outcome dates are labels, never features. Cluster
reports that arise from the same underlying shock.

Source: `docs/alignment.md`, `strategy-feature-contract.md`, `docs/decisions.md`.

### C. Empirical state and negative evidence

Store only the current, checked numbers with an as-of date and a link to the artifact. At the
handoff snapshot, the company-obligation set was small and concentrated (130 facts for PWR/ETN;
28 lacked matched acceptance timestamps; EME/DLR absent), with 84 return events concentrated in
PWR. The larger project-month hazard work and factor tests do **not** establish listed-equity
alpha; tested hazard features did not improve out-of-sample prediction, and no thesis was promoted.
Before saving numeric memory, reconcile against current `results/` files and
`strategy-feature-contract.md`; do not memorize a stale chat estimate or treat row count as
independent shocks.

Source: `strategy-feature-contract.md`, `results/README.md`, the current result artifacts, and
`docs/inbox/vishnu-2026-10-03/ultimate-handoff.md`.

### D. Data state and storage roles

Capture the data boundary rather than a blanket claim that everything is ready: Snowflake is the
raw archival/research and feature-panel destination; TigerData was the operational time-series
store, but the last measured use was near its observed 750 MiB quota, so new writes are paused until
headroom is verified. The cloud loaders are manual/repeatable, not a live or scheduled pipeline.
Massive daily bars/8-K tags were loaded as identified in the central ingest receipt; product
entitlement and vendor snapshots do not themselves guarantee point-in-time completeness. AWS Spot
history is a **listed spot-price history**, not executed rental, utilization, fulfilled capacity,
or a complete compute market. Preserve provenance and vintage; do not mix canaries/batches.

Source: `central-ingest-handoff.md`, `source-audit.md`, `ultimate-handoff.md`. Treat row counts,
batch hashes, quotas, process status, and retrieval timestamps as dated facts that must be checked
from current receipts before reuse.

### E. Point-in-time event-data gaps

Capture these as the critical readiness gaps: original SEC filing documents and publication/
acceptance clocks must be reconciled via accession/document manifests; current estimate snapshots
are not a substitute for historical vintages; company-specific delivery, customer, backlog,
guidance, MW, delay/cancellation facts need reviewed source spans and availability times; market
prices need pinned benchmark/sector controls for reproducible abnormal-return tests. EIA-860M is
physical generator planning/operations, not a data-center interconnection queue. Revised macro
series must be handled by vintage where relevant.

Source: `strategy-feature-contract.md`, `central-ingest-handoff.md`, `source-audit.md`.

### F. Research method and complexity rules

Capture the durable method: mechanism + simplest rival; identify counterparties; define the earlier
expectation; specify quantity and units; audit evidence/availability; predefine baseline, falsifier,
and costs before returns; add complexity only if development evidence justifies it. Confidence is
claim-specific and cannot skip the evidence ladder. Adequacy is independent shocks/regimes, not
calendar years alone. Keep chronological deployability separate from exploratory regime robustness
and preserve the GQH sealed holdout. No quantum, deep-learning, L2/L3, or HFT component is
load-bearing by default; each must demonstrate incremental value on an appropriate task.

Source: `docs/alignment.md`, `docs/brief.md`, `docs/decisions.md`.

### G. Systems readiness and numerical contract

Capture that kdb+/q is intended as a derived HiPerGator time-series layer, with Snowflake archival
and TigerData operational use separated; the q/HDB work remains a local scaffold until actual HPG
runtime/license/job/data checks pass. No migration authorizes deleting source rows. The exporter
uses exact scaled decimal conversion to signed 64-bit units of `1e-8 USD` only for values exactly
representable at that scale; that is not a general claim that OCaml or floating-point arithmetic is
automatically exact. Precision requires explicit units, timestamp rules, rounding/overflow behavior,
and tests.

Source: `hpc/kdb-timeseries/README.md`, its tests, `technical-boundaries.md`, `ultimate-handoff.md`.

### H. Security and memory protocol

Capture only the safety lesson: secrets were pasted in the earlier chat, so treat affected
credentials as exposed and rotate/revoke them. Never store credential values in Hippo or Git. Run
Hippo from the repository-root scoped store only. Do not use `hippo import --file memory/shared.json`;
use the repository's `make absorb` path, which deduplicates. Do not hand-edit generated
`memory/SHARED.md` or `memory/shared.json`.

Source: `docs/memory.md`, `AGENTS.md`, `ultimate-handoff.md`. This entry must not repeat the actual
secret values, account identifiers, or private local paths.

## Safe execution on the Hippo-enabled computer

1. Clone/pull the public repo, `cd` to its root, and run `make sync`. Confirm `pwd`/`git rev-parse
   --show-toplevel` are this repository. Run `make doctor` and inspect its store-scope result;
   initialize/use a **repo-root project store**, not a shared parent/global project store.
2. Read the required source review above. Compare current `memory/SHARED.md` to these candidate
   themes. Do not duplicate memories already present; update stale memory by correcting it through
   the supported memory workflow and preserve historical context where appropriate.
3. Write concise, atomic entries from inside the repo. Example command shape (replace with a
   reviewed entry, never paste secrets):

   ```sh
   make remember M="As of YYYY-MM-DD, ... Canonical source: docs/...; this is [decision/preference/result/open gap]."
   ```

   Keep `make remember` entries small enough to be useful at recall time; use several entries for
   distinct facts. Do not create a giant transcript memory. If the live repo contradicts a
   candidate above, the live repo wins and the candidate is skipped or corrected.
4. Run `make share`. Inspect `git diff -- memory/shared.json memory/SHARED.md`; these are generated
   files. If `make secrets` finds anything, stop and remove/redact it before any commit. Do not
   weaken the filter.
5. Run the relevant tests (`make test` if complete; otherwise memory filter/absorb tests) and
   `make overlaps`. Stage only the generated memory files and any specifically owned updates, then
   commit and push the same shared branch using the repo's rebase/ownership rules. The pre-commit
   hook may regenerate memory; verify the final staged diff after it runs.
6. Verify the GitHub commit contains the refreshed shared files and that the next clean checkout's
   `make sync`/`make absorb` recognizes and imports the new entries idempotently. Report which
   themes were added, which were already present, and any that were skipped because evidence had
   changed. Do not claim the Hippo store is synchronized until the generated files are pushed.

The repo's `make save` uses `git add -A`; for this task, prefer explicit `git add memory/shared.json
memory/SHARED.md` so unrelated user work can never enter the commit.

## Expected completion report

The contributor should return:

- exact commit hash and pushed branch;
- the themes refreshed/added, as short titles (no secret contents);
- `make doctor` store scope and `make share` result;
- whether SEC archive/cloud status was rechecked and any changed counts;
- tests and `make secrets` result; and
- any still-open issue or candidate fact deliberately not promoted.

Do not mark the work complete just because local `hippo remember` succeeded: publication requires
the filtered shared-memory files in Git, and ingestion on another device requires its own
`make sync`/`make absorb`.
