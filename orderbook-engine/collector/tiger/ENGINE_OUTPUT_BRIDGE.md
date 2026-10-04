# TigerData engine-output bridge

## Purpose and boundaries

`ingest_engine_report.py` is a one-way adapter from the OCaml `fixture_report`
JSON contract to the small operational output tables in TigerData. It does not
modify the engine, capture data, ingest raw order-book events, or produce trades.
The full immutable report and canonical fixture belong in Snowflake; the Tiger
run row stores their hashes and a Snowflake artifact URI, and the hypertable
stores numeric report metrics for SQL dashboards/continuous aggregates.

Daily equity/research inputs stay in Snowflake. Raw Hyperliquid acquisition
rows must first pass source, synchronization, ordering, and replay-quality
validation before they are eligible to be used by the engine. Binance-derived
venues are explicitly rejected by this bridge. Do not convert daily bars into
synthetic depth.

## Tables

The target TigerData service currently contains empty `public.engine_run_reports`
and `public.engine_metric_points` tables, an empty `public.engine_metrics_1h`
continuous aggregate, and `engine_metric_points` is a Timescale hypertable. The
matching DDL proposal is `engine_output_schema.sql`. The writer intentionally
does not apply DDL or auto-create a schema; it fails if the tables are absent.

- `engine_run_reports`: deterministic external run key, fixture/config/build
  identity, report checksum and immutable report URI, source hashes, venue,
  symbol, quality status and basic replay counters.
- `engine_metric_points`: flattened numeric scalar metrics, tagged by metric
  family, liquidity mode/regime, unit, timestamp and report checksum. All
  metrics from the current report contract are timestamped at manifest
  `created_at`; event-time series are not claimed because the report does not
  currently emit per-event metrics.
- `engine_metrics_1h`: precomputed dashboard rollup. It does not alter engine
  values or accounting.

Money and quantity metrics retain the engine's integer fixed-point values and
are labeled `money_units_1e-8` or `quantity_units_1e-6`. Prices remain
`price_ticks_1e-4`; the bridge never converts them to floating-point display
values. Numeric telemetry is observational and is not a second accounting
implementation.

## Run identity and retry behavior

`run_key = SHA256(canonical JSON(fixture_sha256, config_sha256, simulator_build))`.
The exact report bytes have their own `report_sha256`. Re-running identical
input/report bytes is idempotent: report insertion is `ON CONFLICT DO NOTHING`,
metric inserts use the hypertable primary key, and stored row count is checked.
If the same run key is presented with changed report bytes or metadata, the
writer fails closed rather than overwriting the first result. If nondeterministic
timing changes the report bytes, use the engine's deterministic report mode or
record a new simulator build/config identity rather than silently replacing it.

**Current contract caveat:** `fixture_report` carries separate `depth_fixture`
and `trades_fixture` paths, while its current manifest exposes one
`fixture_sha256` (the sample value matches the depth JSONL bytes) and no separate
trade-fixture digest. The bridge preserves the engine's declared identity, but
do not treat a real multi-file replay as fully content-addressed until its
manifest includes a combined input hash or hashes both fixture files. This is a
lineage gap to close before production data runs, not a reason to alter the
engine's accounting.

The metadata row is inserted before its metrics inside one database transaction;
the foreign key and transaction ensure no orphan metric rows. Metric row counts
are reconciled before commit.

## Execution-config provenance

If `manifest.config_sha256` is absent, supply the actual simulator execution
configuration, not the upstream capture/normalization configuration. The bridge
accepts either a precomputed 64-character SHA-256 or a JSON object file. For
JSON, keys are sorted and compactly serialized before hashing; the resulting
SHA-256 is stored in `engine_run_reports.config_sha256` and participates in the
run key. The metadata records whether the config hash came from the report
manifest or an explicit override.

```sh
# Use an exact execution-config hash supplied by the harness
--execution-config-sha256 '<64-hex-execution-config-sha256>'

# Or provide the engine execution config itself; it is canonicalized and hashed
--execution-config-json path/to/execution-config.json
```

These flags are mutually exclusive. Without either override, legacy reports
continue to use `manifest.config_sha256`; a report lacking that field is rejected
with a request for an explicit execution config. A singular
`manifest.source_sha256` is accepted as a one-item source provenance list, as
well as the older `manifest.source_hashes` array.

## Use

First store the exact report artifact in Snowflake and note its immutable URI.
Then validate the bridge without a database write:

```sh
python3 orderbook-engine/collector/tiger/ingest_engine_report.py \
  orderbook-engine/examples/io-contract/report-sample.json \
  --simulator-build '<immutable-build-id>' \
  --venue '<validated-venue>' --symbol '<validated-symbol>' \
  --report-uri 'snowflake://VECTOR_RESEARCH.RAW.RESEARCH_ARTIFACTS/<artifact>' \
  --execution-config-json path/to/execution-config.json \
  --dry-run
```

For a real validated run, omit `--dry-run`. The script reads `TIGERDATA_URL`
and optional `TIGERDATA_PASSWORD` from the repo's gitignored `.env` using the
existing local environment loader. It never prints connection material. Unit
tests also use the checked-in `report-sample.json` from the actual engine output
contract and synthetic venue labels, solely in memory. A real bounded
Hyperliquid BTC capture was subsequently replayed through the OCaml engine and
its archived deterministic report was written to TigerData. See
`docs/inbox/vishnu-2026-10-04/orderbook-flow-status.md` for its lineage and the
distinction between structural replay completion and trading validation.

## Current live-service verification (2026-10-04)

Read-only queries found database `tsdb`, Postgres 18.6, total database size
931,043,007 bytes (~888.1 MiB). The three output objects exist and were empty
at the time checked; `engine_metric_points` is a hypertable, and
`engine_metrics_1h` is registered as a continuous aggregate. The largest
current tables are `aws_gpu_spot_prices` (~567.3 MiB), `gqh_source_records`
(~132.7 MiB), and `gqh_eia860m_state_vintage` (~41.2 MiB).

The authenticated Tiger Cloud console now shows service `db-60704` on the
Performance trial, Ready, with `$1,000` promotional credit remaining. That is
not the Free plan's 750 MiB cap: Tiger's current Performance pricing lists up to
16 TB disk per service and meters storage by actual use. The console showed 917
MiB rowstore, 192 MiB WAL, and 353 MiB other; a direct SQL size query returned
888 MB. Thus the old 750 MiB warning is superseded, but credits are a spending
balance rather than a storage quota. Monitor service usage in the console.

One bounded pipeline-validation report has been inserted. The specific run is
structurally complete (1,877 events; zero parse errors, chain gaps, or book
mismatch), while its manifest caveat `healthy_capture_suspect_for_fifo` is
preserved in Tiger metadata. It produced 156 scalar metric rows and zero market
event rows. It is not a strategy result: the capture is short, book updates are
snapshots without order-level FIFO, and instrument-specific fee/contract
assumptions still need confirmation before interpreting P&L. The writer has
been rerun and verified idempotent.
