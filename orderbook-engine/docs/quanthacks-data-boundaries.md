# Quanthacks data boundaries

Snowflake is the queryable shared research/archive store for Quanthacks. Source histories, original filing packages, point-in-time features, frozen replay fixtures, and immutable simulator reports belong there. Data arrives through the account's existing ingestion pipeline, not a share and not a second account.

Massive is the licensed market data source. Its daily equity aggregates are used for the equity event study; the current study needs no L2.

TigerData's project role is the operational time-series sink for compact, validated order-book-engine outputs: run health, book/sequence quality, latency, throughput, per-mode fills/accounting/risk summaries, and dashboard metrics/continuous aggregates. It is not a market-data archive or a Snowflake mirror. No engine output has been loaded to TigerData under this design yet.

The existing `depth_events`, `trade_events`, and `observations` content is a legacy Binance BTCUSDT capture and remains quarantined. Do not use it as strategy data or as a Hyperliquid proxy. Preserve it pending an explicit retention/deletion decision. No genuine synchronized Hyperliquid batch is currently verified.

The output-series storage contract is staged in `orderbook-engine/collector/tiger/engine_output_schema.sql`. It is a reviewed schema proposal, **not applied to the live service**: the database measured 930,707,135 bytes (~889 MiB), above the prior observed 750 MiB allowance. Apply only after checking current plan/quota and measuring retention/headroom.

## Access

Routine access uses the read-only role `GQH_MARKETDATA_RO` with `USAGE` on `VECTOR_RESEARCH` and `COMPUTE_WH` and `SELECT` on the research schemas, through the service user `QUANTHACKS_AGENT` with key-pair authentication.

The private key lives outside the repository, in the local secret store, and never in a repo file, GitHub source, or chat. `ACCOUNTADMIN` is not used for routine work.

## Raw evidence

Raw captures, vendor files, and downloaded artifacts remain immutable files with SHA-256 manifests.

Raw evidence is not rewritten in Tiger Cloud.

## Legacy normalized capture (quarantined)

The current legacy Tiger tables store validated, typed rows for Binance depth events, trades and observations.

Every normalized row keeps its source hash, source path or URI, venue, symbol when applicable, event time, and receive time.

These legacy capture tables use Timescale hypertables. They are not eligible strategy inputs.

Heterogeneous lower-rate data uses the `observations` table with a typed `data_type` and JSONB payload.

## Replay fixtures

`collector/tiger/export_fixture.py` can export a bounded, ordered legacy depth query as the existing normalized JSONL interchange format. Do not use it for project backtests until the source is explicitly validated and eligible.

The OCaml engine validates units, sequence continuity, timestamps, and book state after export.

Tiger Cloud is not the replay authority.

The replay engine must not depend on live database query order or mutable derived tables.

## Engine output data (target)

Canonical fixtures and complete reports stay in Snowflake with source/fixture/config/build hashes.
Only compact, validated engine output metrics are intended for TigerData: report/run time, run key,
source venue and instrument, engine build/config, quality counters, latency/throughput, and
per-liquidity-mode fills, fees, realized P&L and risk/accounting metrics. `engine_output_schema.sql`
defines the proposed run-report registry and numeric time series. Continuous aggregates can serve
dashboard rollups without changing simulator outputs.

TigerData output rows are views/telemetry of simulator results, not an independent numeric
authority; they must link back to the immutable Snowflake report and its hashes. They can be
recreated from that report.

Each run key derives from fixture hash, simulator build and config. Metric values preserve units;
financial results are never recomputed in SQL and LLM/AI evidence cannot alter them.

## Boundary rules

- Do not put credentials, raw license files, or vendor binaries in this repository.
- Do not let an agent write to production Tiger services through MCP.
- Export bounded fixtures before replay and keep the authoritative fixture/report in Snowflake.
- Keep replay fixtures small enough to review and hash.
- Reject rows with missing provenance or invalid sequence metadata.
