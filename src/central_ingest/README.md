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
Use `--target snowflake` for bulky archival panels when TigerData has insufficient storage;
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
read-only API requests. The `--target` option defaults to `both`; `snowflake` or `tigerdata`
isolates a catch-up load. An unchanged rerun does not duplicate rows. If Snowflake succeeds and
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
