# Reviewed event readiness

Owner: aidanq06. Continuation of the [cross-computer handoff](../../docs/inbox/vishnu-2026-10-03/ultimate-handoff.md),
implemented on an isolated branch from `6da2e4b`. This component reconciles SEC archive evidence
and constructs strictly comparable, reviewed **management-guidance revisions** in development data.
It does not select a trade, repeat the rejected broad RPO event study, train a model, open a holdout,
or write to Snowflake/TigerData. The existing ingestion and event-study components remain unchanged.

Read [SYSTEM_AUDIT.md](SYSTEM_AUDIT.md) for findings, history, sources and unresolved integration
issues; [INTERFACE.md](INTERFACE.md) for exact contracts; [VALIDATION.md](VALIDATION.md) for verification
and remaining work. Those are the continuation record, not a new trading thesis.

For the next acquisition and teammate handoff, read [DATA_ACQUISITION.md](DATA_ACQUISITION.md):
Massive client gaps, dataset priorities, private local setup, and the proposed Snowflake release gates.

## Run without accounts or dependencies

Python 3.11+ standard library is sufficient for local reconciliation, features and tests:

```sh
PYTHONPATH=src python3 -m unittest event_readiness.test_readiness -v
PYTHONPATH=src python3 -m event_readiness.run demo --out data/readiness/demo-v1.json
```

The demo uses fictional source documents and a fictional issuer. It emits two comparable revisions
and one exclusion for the initial statement with no prior expectation. This verifies plumbing,
not economic significance. Every output explicitly says `strategy_ready: false`.

Each output is created exclusively: choose a new path for a subsequent run. Run receipts record code
revision, hashes of the actual component files (including uncommitted changes), Python version,
input identity and generation time. Feature row hashes omit wall-clock execution time. Never publish
private raw documents, credentials, restricted market data, or machine-specific paths.

## Step A: inventory before another SEC archive run

The originating computer's authenticated connections were not available in the standard locations
on the continuation computer. **No fresh cloud receipt was obtained.** Do not report historical
handoff counts as current, launch a duplicate provider download, or infer a stopped remote process.

On a machine with its own configured Snowflake connector connection and read access, install
`snowflake-connector-python` in that machine's environment, then:

```sh
PYTHONPATH=src python3 -m event_readiness.run snapshot \
  --connection-name research_readonly \
  --register results/filings-register.csv \
  --out data/readiness/snapshot-v1.json
PYTHONPATH=src python3 -m event_readiness.run reconcile \
  --snapshot data/readiness/snapshot-v1.json \
  --register results/filings-register.csv \
  --out data/readiness/metadata-audit-v1.json
```

`research_readonly` is a placeholder for the operator's connection profile, not an included account.
No `.env` scanning or password copying occurs. SQL is fixed SELECT/LIST only. Metadata contains
no market payloads, forward labels or filing-text snippets. Archive coverage metadata can span
sealed dates; this does not authorize analyzing their content. The collector captures query IDs,
time bounds, source/batch counts and EIA manifest coverage. A missing optional inventory query is
an explicit failure, not an empty successful result. Use a read-only account with a bounded warehouse.

Metadata-only reconciliation intentionally exits **2**, because retained bytes have not been
verified. This is not an unexpected command failure. Exit 1 means malformed input/runtime error.
The current operator must confirm the prior SEC job has stopped; a database snapshot cannot prove it.

Retrieve selected package versions through the approved read-only Snowflake download workflow.
Save each original ZIP under its expected SHA256, with the `.zip` suffix, in a private directory.
This component never downloads or extracts the ZIP for you. Then:

```sh
PYTHONPATH=src python3 -m event_readiness.run reconcile \
  --snapshot data/readiness/snapshot-v1.json \
  --register results/filings-register.csv \
  --packages data/readiness/packages \
  --out data/readiness/byte-audit-v1.json
```

For every selected accession/version, reconciliation requires exactly one manifest, exact document
membership/hash/size matches, a stage object, downloaded ZIP SHA256/size, and individual document
bytes matching their hashes. Multiple package versions sharing one mutable stage path are an error.
Snowflake LIST's MD5 is **not** source SHA256; encrypted-stage MD5 may not even match local MD5.
The ZIP verifier reads members without extracting paths and caps total uncompressed bytes at 2 GB.
An `archive_ready` result covers this selected archive only; it does not approve source licensing,
release timing, analyst expectations, market data, or a strategy.

`missing_accessions` is an investigation/retry candidate list, not authorization to rerun the old
loader unchanged. The audit describes its mutable-stage-path defect. Do not delete old versions.
Reconciliation detects damage; it does not restore overwritten content or repair cloud state.

TigerData inventory must be read separately on its authenticated host. The component never connects
to TigerData. Its storage headroom and source parity remain unverified here; writes remain deferred
under the handoff. See [operations.sql](operations.sql) for read-only inventory checks.

## Step B/D: build the reviewed development input panel

Prepare a JSON package with `schema_version: 1`, `partition: "development"` and a `facts` array
matching `Fact` in [features.py](features.py). Retain each original source document in a private
folder under its SHA256 filename (no extension). The source quote is an exact UTF-8 byte span from
that document; offsets against cleaned/extracted text do not qualify as raw-document offsets.
For HTML with markup interrupting a number, use an original contiguous numeric token and a
reviewed containing span, or create a separately versioned extraction before extending this format.

```sh
PYTHONPATH=src python3 -m event_readiness.run features \
  --facts data/readiness/reviewed-development-facts.json \
  --documents data/readiness/documents \
  --min-history 5 --processing-seconds 60 \
  --out data/readiness/features-v1.json
```

These are engineering defaults, not optimized signal parameters. The source numeric token and
explicit decimal scale must equal the normalized value exactly. Facts must share issuer, security,
metric, type, unit, currency, scope, definition, comparability group and target period. Unknown
fields—including return labels—are refused. Unreviewed source/exposure, missing earlier guidance,
changed perimeter or target, stale superseded guidance and ambiguous timing produce exclusions.
An amendment gets a new ID and its own publication time; it never rewrites a prior event.

The development fence reuses the existing mechanism study boundary: 2015-07-01 inclusive through
2022-10-01 exclusive UTC. It is a containment boundary, **not a certification of the old split's
compliance with the competition rule**. No later-end or sealed override exists. Prepare the
upstream development export before this command; do not give it an entire sealed outcome file.
It cannot make a previously viewed holdout untouched again.

Historical features are **retrospective source reconstruction**: human reviews performed now may
validate past public facts, but do not establish that a model/reviewer existed at the event date.
Do not call this a historical live deployment or an OOS strategy. A reviewer identifier/status is
an attestation supplied by the data owner, not identity authentication by the software. Exposure
links, publication claims and document licensing still need real review.

Feature reports deliberately omit returns, market-state measures and fitted models. The reviewed,
pinned daily/sector panel required by handoff step C is absent; adding labels now would reopen the
same reproducibility gap. The calendar helper defines a conservative next-session-close **reference**,
not an executable fill. Actual calendars, market data/actions, cost model, labels, purged splits
and strategy gates are the next bounded component once inputs are approved.
