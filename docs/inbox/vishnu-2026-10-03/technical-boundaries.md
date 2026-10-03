# Proposed technical boundaries

Owner: Vishnu. Design proposal, not implemented code. Follow the existing root layout and
claim each actual component in OWNERS before creating it. Do not create empty engines merely
to make this diagram look complete.

## Responsibilities and proposed component homes

| Component | Proposed home | Owns | Must not own |
|---|---|---|---|
| Ingestion/normalization | `src/ingest/` | Provider adapters, rate limits, pagination, immutable manifests, normalization | Trading decisions or silently repaired source history |
| Disclosure extraction | `src/extraction/` | Typed operational fields, source passages, review status | Unsupported numeric guesses or execution |
| Point-in-time dataset | `src/dataset/` | Availability joins, identifiers, comparable periods, event clusters, frozen versions | Forward-filling later information backwards |
| Strategy | `src/strategy/` | Pure signal functions, eligibility and abstention | Fetching live APIs or changing the universe after returns |
| Portfolio/risk | `src/portfolio/` | Exposure, sizing, joint risk, borrow/cost assumptions | Assuming beta neutrality removes tail risk |
| Market replay | `src/replay/` | q time-series operations, event ordering and bounded book reconstruction | Treating sparse samples as a historical archive |
| Backtest/accounting | `src/backtest/` | Decision/fill clock, fees, corporate actions, P&L ledger | Same-bar future fills or implicit rounding |
| Reports | `src/reporting/` | Generated result artifacts and note figures | Hand-entered performance numbers |

Each component README should state owner, inputs/outputs, units, availability semantics,
run command, tests and limitations. Keep provider-specific code behind normalized interfaces.
Keep thesis configuration versioned outside engine logic. Tests follow component names under
`tests/`; production behavior must not depend on a developer's local paths.

## Storage and infrastructure roles

- OCI: proposed collection/orchestration host and immutable raw-object storage. Account access,
  permissions and credits are user-reported, not verified in this handoff. Use separate users,
  scoped service credentials and budgets; do not bypass security or share the owner password.
- TigerData/Postgres: disclosure/event metadata, provenance, typed operational fields, job
  manifests and queryable event panels. Use NUMERIC/BIGINT as appropriate, not float for money.
- kdb+/q: market time-series queries, windows, as-of joins, replay and derived market features.
  Its license/runtime and actual integration are not provisioned here.
- Raw objects are authoritative for provenance; normalized tables are versioned transformations;
  q stores are derived views with a declared version. Do not let two databases silently become
  conflicting sources of truth. Transfers and conversions require explicit tested adapters.
- GitHub Actions: CI and bounded scheduled jobs if appropriate. Not a continuous tick collector.
  OCI services or a scheduler require idempotence, checkpoints, retries and observable status.

## Language and arithmetic contract

User preference: q for time series; OCaml for typed strategy/risk/accounting; Rust or C++ only
where measured throughput/integration requires it. Choose one low-level engine, not redundant
implementations. Existing Python collaboration scripts can remain; no wholesale rewrite.

OCaml's strict compiler does not make floats exact. Use integer-scaled prices/amounts or
Zarith integers/rationals where exact arithmetic is required. Define overflow and rounding
behavior at every boundary. Use floating point for statistical calculations only with
documented tolerances, conditioning and reference checks. Do not promise exact statistical
estimation merely because accounting is exact.

Before code, specify price/quantity/currency scales, tick sizes, multiplication widths,
division rounding, null/missing representations and intermediate overflow checks. Preserve
source decimal text before conversion. Never silently parse decimal money through binary float.

Preserve epoch, timezone and nanosecond timestamps explicitly. Postgres timestamps have
microsecond precision; retain finer market timestamps in an integer field when required.
q timestamp epoch conversion must be explicit. Keep exchange-event, receive, public-availability,
decision and fill times separate; do not claim order-book causality from timestamps alone.

## Testing before scaling

Small synthetic/golden fixtures first: decimals, rounding ties, overflow, nulls, corporate
actions, dividends, partial fills, fees, short financing, holidays/DST and timestamp conversions.
Property tests: lossless serialization, accounting identities, deterministic replay, and no
observation available after the decision appearing in a signal. Cross-check q/OCaml/SQL adapters.
Alcotest/QCheck are candidate OCaml tools; verify versions when implementing.

Then integration tests: pagination, retries, duplicate/out-of-order events, schema drift,
interrupted runs, idempotent restarts and manifest hashes. Use tiny licensed/synthetic fixtures,
not gigabytes committed to git. Unit tests do not validate alpha or months of operating behavior.
Longer validation means replay, fault injection and shadow operation after the hackathon.

## HiPerGator: separate approaches, shared contracts

User reports a shared allocation of 250 NCUs, 5 GPUs and 2 TB Blue storage across participants.
This is not an exclusive team reservation. Verify account, scheduler/QOS, quotas and available
capacity before submitting work; do not assume five GPUs are continuously available.

Proposed homes when work actually begins:

- `hpc/batch-research/`: CPU-heavy extraction/dataset checks/development sweeps, chunked jobs.
- `hpc/extraction-training/`: optional labeled extractor evaluation/fine-tuning.
- `hpc/quantum-benchmark/`: optional simulator/optimization benchmark against classical baseline.

Keep the approaches separate; their outputs implement the same declared data/result contracts.
Every job records commit/config/input hashes, environment/modules, resource request, seed,
output location and completion state. Large data/logs/checkpoints remain outside git. Use small
CPU smoke tests before GPU scaling. Do not assume external API access from compute nodes.

Training is gated on a named real model, rights, verified labels and held-out extraction quality.
"jev/laya" remains unidentified. GPU access does not solve that. Quantum work must not become
a dependency for the reproducible core. A judge should be able to reproduce the small study
without our cloud accounts, cluster reservation or a paid data lake.
