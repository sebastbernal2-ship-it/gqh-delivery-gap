# Shared data ingestion handoff (2026-10-03)

**Read this first for current load status.** Earlier status paragraphs in
[source-audit.md](source-audit.md) and [snowflake-path.md](snowflake-path.md) predate the
2026-10-03 central load and may say a source is still local or unretained. They remain useful
for economic uses and design cautions, but this receipt supersedes their *load-status* claims.
Operator commands and query examples live in `src/central_ingest/README.md`.

The raw landing tables are Snowflake
`VECTOR_RESEARCH.RAW.SOURCE_RECORDS` and TigerData `public.gqh_source_records`.
Each row carries source ID/URL, JSON payload, batch and row SHA-256, source time text, and a
separate availability field when the source actually provides one. Query by both `source_id`
and `batch_sha256`: upstream revisions are separate batches, not silently overwritten.

## What was built and what each system does

`src/central_ingest/sync.py` is a **manual, repeatable fan-out loader**. For Massive it calls
the API directly via its own `massive.py` client: adjusted daily OHLCV uses the aggregates
endpoint; AI-tagged 8-K disclosures use `/stocks/filings/8-K/vX/disclosures` with the plural
`tickers` filter and pagination. It validates nonempty rows and required fields, serializes each
record canonically, computes row and batch SHA-256 hashes, then writes that *same batch* into
both databases. Snowflake uses staging plus `MERGE`; TigerData uses `INSERT ... ON CONFLICT`.
Both sides check row count and the complete ordered row-hash sequence before reporting success.
Rerunning an unchanged batch is idempotent. Changed upstream snapshots coexist by batch hash.

The public sources use predownloaded, gitignored local CSV/Excel/ZIP inputs; their cloud copies
are shared, but source download and refresh are **not yet automated**. No raw staging file or
credential was committed. Snowflake is the historical/provenance and future feature-panel layer;
TigerData is the shared time-series/replay layer. Snowflake is not on the order-execution path.
This is not a live replication connection between the two systems: a loader run sends one
validated batch independently to each destination, with `--target` available for catch-up.

## Verified cloud loads

Each completed target load checked its count and ordered row hashes against the input batch.
Massive was fetched directly from its API; other staging files came from the public source.
Sixteen source IDs were loaded (137,439 rows in the full listed batches) into *each* system.
TigerData and Snowflake inventory queries returned identical per-source counts. In addition,
TigerData and Snowflake each hold a separate 20-row PWR Massive canary batch, so a raw
`massive_bars` count across all batches is 13,535, not 13,515. Select the full-basket batch hash
below for analysis; never sum revisions/canaries into one panel.

| Source ID | Rows | Verified target(s) | Scope |
|---|---:|---|---|
| `massive_bars` | 13,515 | both | PWR, ETN, EME, DLR, SPY; 2016–2026 request window |
| `massive_8k` | 201 | both | Four-company tagged disclosures; 2022–2026 window |
| `sec_filings` | 776 | both | Original SEC accession/acceptance register |
| `census_c30` | 152 | both | National data-center construction spending |
| `eia860m_proposed_2024_12` | 3,404 | both | Dec 2024 planned/canceled generator slice |
| `eia930_pjm_sample` | 24 | both | One-day hourly parser test only |
| `philly_delivery_times` | 701 | both | Delivery-time survey history |
| `nyfed_gscpi` | 344 | both | Global supply-chain pressure |
| `fred_rates` | 16,893 | both | Treasury rates |
| `fred_market` | 14,521 | both | VIX/Nasdaq market controls |
| `fred_industry` | 867 | both | Rates and computer/electronics output |
| `m3_shipments` | 6,656 | both | Census manufacturing series |
| `m3_new_orders` | 6,640 | both | Census manufacturing series |
| `m3_unfilled_orders` | 6,656 | both | Census manufacturing series |
| `eia860m_full_2024_12` | 36,949 | both | Dec 2024 generator inventory |
| `eia923_pjm_2024` | 29,140 | both | PJM plant/fuel/month panel; final 2024 |

Full `massive_bars` batch SHA-256:
`bec91f7c380937d3d647ade8214968c13abd4bde032c9a7cf7741f0ee58306cd`.
`massive_8k`:
`a077dfb0f7948bb5b7de45eb6d1f6ef8f3297df7c4a1aa319fef7da60cb0ff51`.
The loader prints other batch hashes. An earlier 20-row PWR Massive canary remains as a distinct
batch; do not combine it with the full basket in a backtest.

**Massive access result:** the supplied competition key successfully returned daily bars for
five tickers and 8-K tags for four, and both datasets were stored/reconciled in both systems.
The operator asserted sponsor permission for team-shared strategy use via the loader's private
license gate. The underlying written grant was not attached to this public repo or independently
reviewed here; confirm its scope before publishing or redistributing vendor data. Teammates
query the shared tables, not the API key. The key and database passwords appeared in chat and
should be rotated and reinstalled privately after the handoff.

The prior AWS GPU Spot archive remains in Snowflake
`VECTOR_RESEARCH.RAW.AWS_GPU_SPOT_PRICES` and TigerData
`public.aws_gpu_spot_prices` (1,592,024 rows each), separate from `SOURCE_RECORDS`.
Its citation and source gap are in [Snowflake path](snowflake-path.md).
TigerData database size after these loads was 731,944,639 bytes; the console previously showed
a 750 MiB free-service storage allowance. The team's credit does not itself verify that this
service has been upgraded. Check its actual plan/limit before another large TigerData load.

## Requested event-study package (2026-10-03 follow-up)

The Massive daily panel is extended beyond the original adjusted-bars load. Adjusted and
unadjusted OHLCV for PWR, ETN, EME, DLR and SPY cover 2016-01-01 through 2026-10-02 (13,515
rows per version in the verified batches). Separate corporate-action and metadata batches are
also in both stores: 204 dividends, five explicit split interval receipts (no split rows in the
requested interval), five ticker-event receipts, and ten start/end ticker metadata snapshots.
The loader/manifests retain request URL, retrieval time, hash, count, and the project lead's
sponsor-permission assertion. These are current Massive snapshots, not point-in-time adjusted
prices. Do not infer that no ticker-history changes exist outside the specific endpoint coverage
tested.

The EIA-860M vintage archive was ingested by `src/central_ingest/eia860m.py`: original monthly
XLSX plus all three-sheet generator rows are in Snowflake, with vintage month-end availability,
entity/plant/generator identifiers, owner, state, capacity, planned/actual month, status, source
URL, retrieval time and source-file SHA-256. Available vintages cover 2016-01 through 2026-08
in Snowflake. The archive index lists 2026-09 but that file was not served (three download
attempts failed); 2026-08 is the newest verified release. TigerData has compact state/technology
summaries through 2022-12 only. Its database reached 786,011,839 bytes against the previously
observed 750 MiB allowance, so **do not write more TigerData rows until the service storage
allowance is confirmed/expanded**. Snowflake is the complete query layer for the raw EIA panel.
Resume idempotently with `--target snowflake` (or `--target both` only after confirming
TigerData capacity).

The existing `sec_filings` load is only the accession register (776 rows, 2015–2026), not raw
filing/exhibit content. A real SEC request User-Agent using the project lead's contact was
verified against a public filing (HTTP 200). The batch archive downloader and raw document stage
upload are running, but completion has not been reconciled at this handoff. Do not report the raw
SEC archive as complete until all selected accession packages, stage files and document hashes
are reconciled against the input register. Historical PIT estimates are also not loaded; no entitlement to
true estimate revision vintages has been verified. Current consensus data is not a substitute for
historical as-of estimates.

## Teammate access and immediate next action

1. Pull commit `91ed86f` or later on `main`; read `src/central_ingest/README.md` for the
   exact environment variables, loader commands, table names, and SQL examples.
2. Use your **own** Snowflake/TigerData login with query grants. Verify access by querying the
   `massive_bars` full-basket hash above in each database. A GitHub invite alone does not grant
   database access; pending Snowflake invitations must be accepted, and TigerData access/grants
   must be provisioned separately. Do not copy the operator's `.env` or paste passwords in chat.
3. Start a typed, timestamp-safe panel from the raw batches: join SEC acceptance/availability
   to Massive 8-K enrichment by accession, keep source vintage/hash, define company/plant
   exposures before using EIA, and run an equity-only baseline before adding compute context.
   This ingestion commit did **not** build features, a backtest, a scheduler, or an OOS result.
   Current feature inventory and explicit readiness gates are maintained in the
   [strategy feature contract](strategy-feature-contract.md); it supersedes older shorthand that
   could be read as saying the stock-strategy inputs were already complete.

## Provenance of new workbooks

M3 downloads came from the [Census historical time-series page](https://www.census.gov/manufacturing/m3/historical/timeseries.html):
`naicsvsp.xlsx` (SHA-256 `b0a3472969678ba700cea9aa6e8d0c498edd0d2bb4572a1ae664b8195f950861`),
`naicsnop.xlsx` (`24e77f0edb4bb5980da90c99ee7a860d7ea0e5ba2b6d9a1cec9d904ce46483f8`),
and `naicsuop.xlsx` (`ba727db24522b9a33aab7da11a92df5fd2c0d3c1ee78a194e800cbdc32971f61`).
The [EIA-923 archive](https://www.eia.gov/electricity/data/eia923/) ZIP is `f923_2024.zip`
(SHA-256 `272055f2d748f6486fc3076abd5a40ec736db4c895761278c50f2b`).
The 2024 workbook is final data published later; observation month is not first availability.

## Remaining work and caveats

This is a shared **raw** ingestion layer, not a scheduled cloud worker or live TigerData↔Snowflake
connector. The operator runs the loader and checks each receipt. Current Census/M3/FRED/NY Fed/EIA
workbooks can contain revisions; historical observation periods must not be mistaken for their
publication times. Massive 8-K categories are vendor enrichment, not canonical SEC acceptance
timing. Massive adjusted bars are a current snapshot, not corporate-action point-in-time history.
The EIA-930 and EIA-923 loads are coverage tests, not long-history signals.

Next: add immutable fetch manifests, source-release vintages, a predeclared company/plant
exposure map, typed Snowflake features, then scheduled cloud refresh after unattended QA passes.
Census trade and EPA CAMPD remain candidates, not claimed loads; choose commodity codes and
facilities tied to a falsifiable mechanism before fetching bulk data. Team members need their
own Snowflake/TigerData accounts and grants, not the operator's API key or database password.
