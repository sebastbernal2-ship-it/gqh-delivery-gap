# Snowflake research workspace

Owner: vshnu1. This is the historical research layer, not the live execution path.

`bootstrap.sql` is mirrored into the Snowflake personal workspace as
`VECTOR_snowflake_bootstrap.sql`. On 2026-10-03 the signed-in Snowflake account successfully
ran the bootstrap and loaded the AWS Spot archive into `RAW.AWS_GPU_SPOT_PRICES`; Snowflake
reported 1,592,024 inserted rows. The final query is the post-load QA check. No warehouse was
created by the bootstrap (the account's existing X-Small `COMPUTE_WH` was used for the import).

The intended boundary is:

```text
TigerData/q -> curated exports -> Snowflake research panels -> Parquet/q -> C++/OCaml backtest
```

Do not query Snowflake per tick or per order. Keep raw source files immutable and preserve
`event_time`, `available_at`, `ingested_at`, source version and checksum. A feature may only use
rows available by the decision timestamp. Start with a small AWS compute + equity + Massive filing
panel and compare the output with the TigerData/q-only baseline before adding ML services.

Current AWS table provenance: Eric Pauley, *AWS Spot Price History*, 2026-09 version, Zenodo
[10.5281/zenodo.23082767](https://doi.org/10.5281/zenodo.23082767), CC BY 4.0. The loaded
snapshot spans 2022-05-31 18:50:49 UTC to 2026-09-30 23:00:00 UTC across 31 files. March–June
2026 are absent and explicitly recorded in `RAW.AWS_GPU_SPOT_SOURCE_GAPS`; do not interpolate.
Snowflake post-load QA confirmed 1,592,024 rows, 31 source files, UTC-decoded min/max timestamps,
zero null load timestamps and zero rows in the gap. The source has event timestamps but no proven
historical publication/collector-availability timestamps, so the daily view is descriptive until
that caveat is resolved. TigerData already has the same table from a separate load; there is no
scheduled/automated bridge today. Current verification and the phased data-onboarding plan are
recorded in the shared Snowflake path handoff.

## Equity event feature contract

`bootstrap.sql` now defines an additive contract for three layers:

- `NORMALIZED.OPERATIONAL_FACTS`: accession-linked, reviewed company facts with distinct
  publication/acceptance/availability clocks, original source span/hash, explicit units, and
  point-in-time expectation/exposure fields.
- `FEATURES.EQUITY_EVENT_FEATURES`: past-only decision-time features and source batch hashes.
- `FEATURES.EQUITY_EVENT_LABELS`: forward return/cost outcomes keyed by event and horizon. Labels
  must never be joined into the strategy input view.

The earlier generic `FEATURES.POINT_IN_TIME_PANEL` is retained for compatibility; it is not the
new event-study schema. These DDLs have **not** been applied to Snowflake, and the new tables are
not populated. Wait for reviewed event facts, pinned benchmark bars, and a loader with
reconciliation tests before creating/populating them. Current coverage and hard readiness gates
are in the [feature contract](../inbox/vishnu-2026-10-03/strategy-feature-contract.md). The
existence of DDL does not mean populated or validated features.

No Snowflake credentials belong in this repository.
