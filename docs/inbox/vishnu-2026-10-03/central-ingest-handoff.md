# Shared data ingestion handoff (2026-10-03)

This is the current receipt for the team's shared raw data. Economic uses and limitations are
in [source-audit.md](source-audit.md); operator commands and query examples are in
`src/central_ingest/README.md`. The raw landing tables are Snowflake
`VECTOR_RESEARCH.RAW.SOURCE_RECORDS` and TigerData `public.gqh_source_records`.
Each row carries source ID/URL, JSON payload, batch and row SHA-256, source time text, and a
separate availability field when the source actually provides one. Query by both `source_id`
and `batch_sha256`: upstream revisions are separate batches, not silently overwritten.

## Verified cloud loads

Each completed target load checked its count and ordered row hashes against the input batch.
Massive was fetched directly from its API; other staging files came from the public source.

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

The prior AWS GPU Spot archive remains in Snowflake
`VECTOR_RESEARCH.RAW.AWS_GPU_SPOT_PRICES` and TigerData
`public.aws_gpu_spot_prices` (1,592,024 rows each), separate from `SOURCE_RECORDS`.
Its citation and source gap are in [Snowflake path](snowflake-path.md).
TigerData database size after these loads was 731,944,639 bytes; the console previously showed
a 750 MiB free-service storage allowance. The team's credit does not itself verify that this
service has been upgraded. Check its actual plan/limit before another large TigerData load.

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
