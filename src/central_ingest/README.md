# Shared source ingestion

`sync.py` takes one validated source batch and writes the identical rows to
`VECTOR_RESEARCH.RAW.SOURCE_RECORDS` in Snowflake and `public.gqh_source_records` in TigerData.
Use `--target snowflake` for bulky archival panels when TigerData has insufficient storage;
`--target tigerdata` can replay a verified batch into the operational store later.
The tables retain the source URL, the original row as JSON, a batch hash, a row hash, and the
source's own time fields. Neither a survey month nor a later download time is silently treated as
the time a trader could first have known the value. Repeated runs of the same batch are
idempotent. A changed source snapshot has a new batch hash and remains separately queryable.

The starter command is:

```sh
python3 src/central_ingest/sync.py --list
python3 src/central_ingest/sync.py --source census_c30 --dry-run
python3 src/central_ingest/sync.py --source census_c30
```

The last command requires `TIGERDATA_URL` plus `TIGERDATA_PASSWORD` (or a URL that already
contains it), and either `SNOWFLAKE_CONNECTION_NAME` (from the
Snowflake connector's private connections file) or `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`,
`SNOWFLAKE_WAREHOUSE`, and either `SNOWFLAKE_PASSWORD` or `SNOWFLAKE_PRIVATE_KEY_FILE`.
These may live in the ignored repo-root `.env` file or in the process environment.
Install `psycopg[binary]` and
`snowflake-connector-python` in a private project environment. No credential belongs in this
public repository. The process reports counts and batch hashes, never credentials. It stops
before writing unless the selected connections are configured.

For Massive, the same command obtains rows from the tested API and writes them directly to both
stores; no retained local CSV is needed:

```sh
python3 src/central_ingest/sync.py --source massive_bars --from 2016-01-01 --to 2016-01-31 --ticker PWR
python3 src/central_ingest/sync.py --source massive_8k --from 2022-01-01 --to 2022-12-31 --ticker PWR
python3 src/central_ingest/sync.py --source eia923_pjm_2024 --target snowflake
```

Set `MASSIVE_API_KEY` and `GQH_MASSIVE_TEAM_STRATEGY_LICENSE=confirmed` in the private runtime.
The latter records the team's sponsor confirmation; it is not a substitute for a usable key.
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

TigerData example:

```sql
SELECT event_time_text, payload_json
FROM public.gqh_source_records
WHERE source_id = 'massive_8k' AND batch_sha256 = '<verified batch hash>'
ORDER BY event_time_text;
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

The two targets are not transactionally coupled. If one write fails, rerun the exact batch;
idempotent keys allow the missing target to catch up. The command reports target counts and
fails when either count differs from the input batch. Do not mark a source operational until
the cloud count and time semantics have both been checked.
