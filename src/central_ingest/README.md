# Shared source ingestion

## Architecture and current state

```text
Massive API (direct, paginated) ─┐
public downloaded CSV/Excel/ZIP ─┼─> validate + canonical JSON + batch/row SHA-256
                                 ├─> Snowflake RAW.SOURCE_RECORDS (staging + MERGE)
                                 └─> TigerData public.gqh_source_records (idempotent INSERT)
                                      └─> counts + ordered row hashes checked per target
```

This code is a **manual batch loader**, not a cloud scheduler, live stream, Snowflake↔TigerData
replicator, feature model, or trading engine. Both databases received the same 16 full-batch
source IDs on 2026-10-03. The receipt, exact counts and caveats are owned by
`docs/inbox/vishnu-2026-10-03/central-ingest-handoff.md`; consult it rather than older
load-status prose elsewhere. The AWS GPU Spot archive predates this loader and lives in separate
tables (`VECTOR_RESEARCH.RAW.AWS_GPU_SPOT_PRICES` and `public.aws_gpu_spot_prices`).

`sync.py` takes one validated source batch and writes the identical rows to
`VECTOR_RESEARCH.RAW.SOURCE_RECORDS` in Snowflake and `public.gqh_source_records` in TigerData.
Snowflake is the default target. Use `--target both` only when TigerData has verified headroom;
`--target tigerdata` can replay a verified batch into the operational store later.
The tables retain the source URL, the original row as JSON, a batch hash, a row hash, and the
source's own time fields. Neither a survey month nor a later download time is silently treated as
the time a trader could first have known the value. Repeated runs of the same batch are
idempotent. A changed source snapshot has a new batch hash and remains separately queryable.

## Operator setup and commands

On the ingestion machine, use a private virtual environment and put credentials in the ignored
repo-root `.env` or a private process environment. Do not commit `.env`, output a secret to a log,
or copy the operator's credentials to teammates. Required variables for a dual-target run are
`TIGERDATA_URL`, `TIGERDATA_PASSWORD`, `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`,
`SNOWFLAKE_WAREHOUSE`, and `SNOWFLAKE_PASSWORD` (or the documented private-key/connection-name
alternatives). Massive additionally needs `MASSIVE_API_KEY` and the operator-set
`GQH_MASSIVE_TEAM_STRATEGY_LICENSE=confirmed` gate. The gate records an assertion; it does not
prove licensing by itself.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install 'psycopg[binary]' snowflake-connector-python openpyxl certifi
.venv/bin/python src/central_ingest/sync.py --list
.venv/bin/python src/central_ingest/sync.py --source census_c30 --dry-run
.venv/bin/python src/central_ingest/sync.py --source census_c30
```

`--dry-run` parses, validates and hashes without database writes. For Massive it still makes
read-only API requests. The `--target` option defaults to `snowflake`; use `both` only after
confirming TigerData capacity, or `tigerdata` to isolate a catch-up load. An unchanged rerun does not duplicate rows. If Snowflake succeeds and
TigerData fails, fix the latter and rerun the *same source/window*—do not recompute a different
snapshot and mistake it for the missing half.
For Snowflake, `SNOWFLAKE_CONNECTION_NAME` from a private connector connections file or
`SNOWFLAKE_PRIVATE_KEY_FILE` can replace username/password authentication. The process reports
counts and batch hashes, not credentials, and stops before writing when a selected connection
is unconfigured.

For Massive, the same command obtains rows from the tested API and writes them directly to both
stores; no retained local CSV is needed:

```sh
python3 src/central_ingest/sync.py --source massive_bars --from 2016-01-01 --to 2016-01-31 --ticker PWR
python3 src/central_ingest/sync.py --source massive_8k --from 2022-01-01 --to 2022-12-31 --ticker PWR
.venv/bin/python src/central_ingest/sync.py --source sec_obligation_facts --target snowflake
.venv/bin/python src/central_ingest/sync.py --source eia923_pjm_2024 --target tigerdata
```

The full verified Massive load used `--from 2016-01-01 --to 2026-10-02` for bars and
`--from 2022-01-01 --to 2026-10-02` for 8-K tags. Both had PWR, ETN, EME and DLR;
bars additionally had SPY. The independent
`massive.py` client has no dependency on the former standalone Massive pull script
(which was removed on main). It uses the adjusted daily aggregates endpoint and the 8-K
`vX/disclosures` endpoint's `tickers` filter. It checks required bar fields, OHLC ordering,
chronology, duplicates and paginated API origin. The API key is never included in exception
details or committed output.

The key is used only by the ingestion operator. Teammates query the shared database with their
own accounts; they do not need a copy of the key.

For teammates, query by `SOURCE_ID` and select the intended `BATCH_SHA256`—multiple batches
can coexist after an upstream revision. Snowflake example:

```sql
SELECT EVENT_TIME_TEXT, TRY_PARSE_JSON(PAYLOAD_JSON) AS RECORD
FROM VECTOR_RESEARCH.RAW.SOURCE_RECORDS
WHERE SOURCE_ID = 'massive_bars' AND BATCH_SHA256 = '<verified batch hash>'
ORDER BY EVENT_TIME_TEXT;
```

To inspect available batches before choosing one:

```sql
SELECT SOURCE_ID, BATCH_SHA256, COUNT(*) AS ROWS, MIN(EVENT_TIME_TEXT) AS FIRST_EVENT,
       MAX(EVENT_TIME_TEXT) AS LAST_EVENT
FROM VECTOR_RESEARCH.RAW.SOURCE_RECORDS
GROUP BY SOURCE_ID, BATCH_SHA256
ORDER BY SOURCE_ID, FIRST_EVENT;
```

TigerData example:

```sql
SELECT event_time_text, payload_json
FROM public.gqh_source_records
WHERE source_id = 'massive_8k' AND batch_sha256 = '<verified batch hash>'
ORDER BY event_time_text;
```

TigerData inventory query:

```sql
SELECT source_id, batch_sha256, count(*) AS rows, min(event_time_text) AS first_event,
       max(event_time_text) AS last_event
FROM public.gqh_source_records
GROUP BY source_id, batch_sha256
ORDER BY source_id, first_event;
```

`SOURCE_RECORDS` is a raw landing table, not a point-in-time feature table. Massive bars are
adjusted snapshots. Massive 8-K tags have filing dates but no guaranteed historical tag
availability; join original SEC filings using accession and conservative acceptance timing.

### Current event-study package additions

The full daily-market panel has adjusted and unadjusted Massive aggregates, split/dividend
actions, and ticker event/metadata snapshots for PWR, ETN, EME, DLR, SPY. These are separate
source IDs also include `hyperliquid_ws_capture` (data/hyperliquid/ws) and `hyperliquid_book_capture` (data/hyperliquid/book), registered 2026-10-04: the local venue captures, dry-run validated, and blocked on credentials in this checkout.

source IDs: `massive_bars`, `massive_bars_unadjusted`, `massive_splits`, `massive_dividends`,
`massive_ticker_events`, and `massive_ticker_metadata`. Query batches in the manifests; the
per-run receipt records URL, retrieval timestamp, license assertion, row count, and batch hash.
Daily bars are sufficient for the first event study; no L2/L3 data is in this initial package.

The first event study also needs market/sector controls. Massive adjusted daily bars for XLI and
XLRE were added to **Snowflake only** in batch
`2fe0dd7ac31d8ed7b990e895a4872490f24b5418b292488a83025a64361a55b9` (5,404 rows total,
2,702 per ticker, 2016-01-04–2026-10-02). Do not append this history to TigerData while its
storage allowance is unresolved. The initial SEC XBRL-derived obligation panel was added as
`sec_obligation_facts`, batch
`7beffd642ed1389829b72fb2a3cda8e0b657f6a10761a56fc0c084350c0846f2` (130 rows, Snowflake
only). It is a derived fact/event panel, not original SEC documents or analyst consensus.
Reproduce the descriptive outcome study with:

```sh
.venv/bin/python scripts/run_warehouse_revision_event_study.py \
  --event-batch-sha256 7beffd642ed1389829b72fb2a3cda8e0b657f6a10761a56fc0c084350c0846f2
```

The script reads only pinned Snowflake batches: operating equities/SPY
`bec91f7c380937d3d647ade8214968c13abd4bde032c9a7cf7741f0ee58306cd`, controls above, and the
SEC obligation batch above. It writes a CSV of event/horizon outcomes and a JSON receipt. The
study is development-only; the 84 eligible rows span 52 accessions, only PWR and ETN have this
obligation-panel coverage, and no analyst expectation/surprise or strategy P&L is inferred.
The exact CSV and JSON outputs are also stored in `VECTOR_RESEARCH.RAW.RESEARCH_ARTIFACTS` with
artifact SHA-256 identity and input-batch lineage. This keeps gathered analytical results
centrally retrievable rather than dependent on one developer's local `results/` directory.

### AWS compute second-deliverable inputs

The raw AWS price history is in `VECTOR_RESEARCH.RAW.AWS_GPU_SPOT_PRICES`. Its study uses two
additional pinned source batches in `RAW.SOURCE_RECORDS`, loaded Snowflake-only (not TigerData):

- `aws_compute_monthly_family`: 566 monthly family summaries,
  batch `044a082fe24c9afd3410a974f7fa471ce3b5dc12a6f4cf2a651b6accc9d331bb`. Derived from AWS Spot
  Price History v2026-09, DOI `10.5281/zenodo.23082767`, CC BY 4.0.
- `sec_provider_capex_quarterly`: 192 SEC XBRL-derived quarterly capex observations,
  batch `48534d7bf98d785d2e1f738eaa867882dca57056e634b9deaa453e7844e0ee6e`. This current
  extract may contain restatements and is not a point-in-time filing-vintage feature table.

Reproduce the unique-quarter diagnostic with `.venv/bin/python
scripts/audit_compute_lead_dependence.py`; it reads only those exact hashes from Snowflake and
stores the exact CSV/JSON outputs in `RAW.RESEARCH_ARTIFACTS`. This is retrospective descriptive
analysis, not a trading signal.

`eia860m.py` is the monthly 860M vintages loader. It retains the official original XLSX and
parsed generator rows in Snowflake `VECTOR_RESEARCH.RAW.EIA860M_ARCHIVE` and
`VECTOR_RESEARCH.RAW.EIA860M_GENERATOR_VINTAGES`; compact state/technology summaries and a
manifest are mirrored to TigerData `public.gqh_eia860m_state_vintage`. The raw row table carries
the vintage and conservative month-end `AVAILABLE_AT`, IDs, owner/entity name and ID, plant,
state, technology, capacity, planned/actual month, status, source URL, original-file SHA-256,
and retrieval time. Example:

```sh
.venv/bin/python src/central_ingest/eia860m.py --from-month 2016-01
```

The default endpoint is the last completed month. `--to-month YYYY-MM` and `--limit N` are
available for a smoke test. The default target is Snowflake to avoid growing TigerData while its
observed storage allowance is at/over quota; set `--target both` only after confirming available
capacity. The public index can list a future/unpublished month: on 2026-10-03,
2026-09 was indexed but unavailable, so the newest verified release was 2026-08. TigerData is
near its known 750 MiB allowance; use `--target snowflake` for further EIA history unless the
service capacity is verified/expanded. Full generator rows and original XLSX are in Snowflake;
TigerData's loaded state/technology history ends 2022-12. EIA is public; observe its attribution.
An inventory vintage is not a promise of future delivery nor proof of actual MW until a later
operating-status observation is seen.

The existing SEC `results/filings-register.csv`/`sec_filings` batch is an accession register,
not the filing text package. `sec_archive.py` fetches each official accession index and every
document/exhibit, packages original bytes to a Snowflake internal stage, and records per-document
SHA-256, URLs, timestamps, metadata and matched text snippets in
`RAW.SEC_FILING_PACKAGE_MANIFESTS` and `RAW.SEC_FILING_DOCUMENTS`. Use a real contact in its
User-Agent; SEC is public and requires no API key:

```sh
EDGAR_USER_AGENT='project research real-contact@school.edu' \
  .venv/bin/python src/central_ingest/sec_archive.py --from-date 2016-01-01 --to-date 2026-10-03
```

Raw SEC packages stay in Snowflake to avoid consuming TigerData's nearly exhausted storage
allowance. The snippet extractor is a review aid, not a normalized entity/metric model. Historical
point-in-time analyst consensus is not loaded: current estimates are not revision-vintage data.
Only ingest FMP or Massive estimates if the account entitlement explicitly includes historical
as-of snapshots.

The current CSV inputs are the validated local extracts documented in
`docs/inbox/vishnu-2026-10-03/source-audit.md`. They are staging inputs for the first cloud
load, not the shared team interface. Once loaded, other machines use Snowflake or TigerData.
The M3 commands read official Census Excel workbooks (shipments, new orders, unfilled orders)
downloaded from the linked NAICS historical series page. They select eight relevant industry
series codes and retain both adjusted and unadjusted observations where provided. Install
`openpyxl` for these commands. M3 values are millions of USD and the current workbook is a
revised history; the observation month does not establish its original release time.
`eia923_pjm_2024` reads the EIA's 2024 final ZIP and extracts PJM plant/fuel/month generation
and heat input. It is a one-year parser and coverage test, not a ten-year regional panel.
`--dry-run` verifies their schema, hashes, and record counts without database credentials.
The Census, Philadelphia Fed, NY Fed, FRED, and EIA files are current downloaded snapshots;
several contain revisions. They are research context until release vintages and `available_at`
are established. The EIA-930 file is only a 24-hour smoke test.

The two targets are not transactionally coupled. The command reports selected-target counts
and fails on count or hash mismatch. A matching raw batch is not yet a usable trading feature:
time semantics and economic exposure must be checked separately.
