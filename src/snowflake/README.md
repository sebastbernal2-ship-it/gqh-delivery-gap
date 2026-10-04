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

## Additive AI-evidence layer for the backtester

Snowflake Cortex is used as a **research sidecar**, not as a source of truth or a strategy
engine. `ai_evidence.sql` creates a separate annotation table and contains a small, read-only
`AI_COMPLETE` extraction query over pre-extracted SEC context snippets. It produces candidate
evidence only. It never updates `RAW`, `NORMALIZED.OPERATIONAL_FACTS`, `FEATURES`, bars, fills,
quotes, order-book events, P&L, or strategy outputs. Candidate values/dates remain verbatim text;
there is no numeric normalization or conversion in this path. A human must verify the exact source
quote and mark any resulting record reviewed before another process may use it.

The order-book backtester can call `src/snowflake/research_sidecar.py` after a run to retrieve
related filing snippets and request a qualitative Cortex answer. Its public interface accepts a
question and an allowlisted ticker, **not** prices, order-book arrays, fills, signals, or result
metrics. The backtester must render its computed values directly from its own immutable result
artifact; the AI panel is visibly separate and must show the original SEC excerpt, accession,
document URL, filed/accepted/available timestamps, and document hash beside any generated answer.
The model is instructed not to restate numeric values or performance metrics, and a deterministic
response guard suppresses generated prose containing any digit. The separate source card remains
the evidence of record if the generated explanation is wrong.

### Wiring and operations

1. Load SEC filings/exhibits with `src/central_ingest/sec_archive.py`; it preserves originals in
   Snowflake stages and writes source metadata/context rows to `RAW.SEC_FILING_DOCUMENTS`.
2. Run `src/snowflake/cortex_search.sql` only after reviewing the account's Cortex Search serving
   and warehouse consumption. The index is separate from source tables and uses a one-day refresh
   target because archived filings are static. Check that service state is `RUNNING` before use.
3. Configure the backend—not browser JavaScript—with `SNOWFLAKE_ACCOUNT_URL`, `SNOWFLAKE_PAT`,
   and `SNOWFLAKE_CORTEX_MODEL`. Pick the model from Snowflake's `/api/v2/cortex/models` response.
   The module then calls the Cortex Search REST endpoint and Snowflake's OpenAI-compatible Cortex
   Chat Completions REST endpoint. A PAT must be restricted to an application/service identity;
   never put it in the client bundle, URL, logs, GitHub issue, or repo.
4. Add a post-run “Research evidence” panel in the backtester. Pass only user-selected ticker(s)
   and a qualitative question; do not automatically call on every run, every row, or every order.
   Include an explicit button and show the retrieved excerpts separately from the answer.
5. Keep API failures non-fatal to the run: show a research-panel error, but never change,
   recompute, suppress, or invalidate the deterministic backtest result. No Cortex output is joined
   to the strategy feature view or exported as a strategy signal.

`src/snowflake/cortex_search.sql` creates a continuously served feature and can consume credits;
it is intentionally **not** part of bootstrap and has not been applied. `ai_evidence.sql`'s
inference example is a deliberately small manual query and has not been run. The REST adapter is
implemented and unit tested, but the actual order-book backtester repository is not present in this
checkout, so the UI hook and live Snowflake service/API smoke test remain integration steps. The
appropriate user-facing value is defensible provenance and fast evidence review—not claimed alpha
or altered backtest values.
