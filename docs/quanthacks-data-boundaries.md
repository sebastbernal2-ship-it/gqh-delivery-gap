# Quanthacks data boundaries

Snowflake is the queryable research store for Quanthacks, in the account the captain directed: database `VECTOR_RESEARCH`, warehouse `COMPUTE_WH`, organization `shrsalh`, locator `RE54719`. Data arrives through the account's existing ingestion pipeline, not a share and not a second account.

Massive is the licensed market data source (`api.massive.com`, Polygon-compatible). The license covers US equity aggregates, tick trades with participant timestamps, tick NBBO quotes, snapshots, options, crypto, and reference data.

Tiger Cloud remains the store for our own Binance depth and trade captures, and it keeps working. It is no longer the only research store.

## Access

Routine access uses the read-only role `GQH_MARKETDATA_RO` with `USAGE` on `VECTOR_RESEARCH` and `COMPUTE_WH` and `SELECT` on the research schemas, through the service user `QUANTHACKS_AGENT` with key-pair authentication.

The private key lives outside the repository, in the local secret store, and never in a repo file, GitHub source, or chat. `ACCOUNTADMIN` is not used for routine work.

## Raw evidence

Raw captures, vendor files, and downloaded artifacts remain immutable files with SHA-256 manifests.

Raw evidence is not rewritten in Tiger Cloud.

## Normalized data

Tiger Cloud stores validated, typed rows for depth events, trades, funding, and other observations.

Every normalized row keeps its source hash, source path or URI, venue, symbol when applicable, event time, and receive time.

High-rate time-series tables use Timescale hypertables.

Heterogeneous lower-rate data uses the `observations` table with a typed `data_type` and JSONB payload.

## Replay fixtures

`collector/tiger/export_fixture.py` exports a bounded, ordered depth query as the existing normalized JSONL interchange format.

The OCaml engine validates units, sequence continuity, timestamps, and book state after export.

Tiger Cloud is not the replay authority.

The replay engine must not depend on live database query order or mutable derived tables.

## Derived data

Spreads, depth metrics, volatility, trade flow, fills, P&L, and strategy reports are derived data.

Derived data can be rebuilt from raw evidence and normalized rows.

It must carry the input range, query version, source hashes, and engine version.

## Boundary rules

- Do not put credentials, raw license files, or vendor binaries in this repository.
- Do not let an agent write to production Tiger services through MCP.
- Export bounded fixtures before replay.
- Keep replay fixtures small enough to review and hash.
- Reject rows with missing provenance or invalid sequence metadata.
