"""Fetch EIA-860M monthly releases, preserve originals in Snowflake, and mirror compact panels."""

from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import json
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "central_ingest"))

import sync
from eia.vintages import fetch_vintage, read_vintage, vintage_index
from eia.xlsx import find_header, read_sheets

STAGE = "VECTOR_RESEARCH.RAW.EIA860M_ARCHIVE"
TABLE = "VECTOR_RESEARCH.RAW.EIA860M_GENERATOR_VINTAGES"
MANIFEST_TABLE = "VECTOR_RESEARCH.RAW.EIA860M_FILE_MANIFESTS"
CSV_FIELDS = (
    "vintage_month", "available_at", "sheet", "plant_id", "generator_id", "entity_name",
    "plant_name", "state", "sector", "technology", "capacity_mw", "planned_month",
    "actual_month", "status", "entity_id", "source_url", "source_file_sha256", "retrieved_at",
)
SNOWFLAKE_COLUMNS = (
    "VINTAGE_MONTH", "AVAILABLE_AT", "SHEET", "PLANT_ID", "GENERATOR_ID", "ENTITY_NAME",
    "PLANT_NAME", "STATE", "SECTOR", "TECHNOLOGY", "NAMEPLATE_CAPACITY_MW",
    "PLANNED_OPERATION_MONTH", "ACTUAL_OPERATING_MONTH", "STATUS", "ENTITY_ID", "SOURCE_URL",
    "SOURCE_FILE_SHA256", "RETRIEVED_AT",
)


def month_key(value: str) -> tuple[int, int]:
    year, month = (int(part) for part in value.split("-", 1))
    if not 1 <= month <= 12:
        raise ValueError(f"invalid month: {value}")
    return year, month


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def snowflake_connection():
    import snowflake.connector

    name = os.getenv("SNOWFLAKE_CONNECTION_NAME")
    if name:
        return snowflake.connector.connect(connection_name=name)
    options = {
        "account": os.environ["SNOWFLAKE_ACCOUNT"], "user": os.environ["SNOWFLAKE_USER"],
        "warehouse": os.environ["SNOWFLAKE_WAREHOUSE"], "database": "VECTOR_RESEARCH", "schema": "RAW",
    }
    if os.getenv("SNOWFLAKE_ROLE"):
        options["role"] = os.environ["SNOWFLAKE_ROLE"]
    if os.getenv("SNOWFLAKE_PRIVATE_KEY_FILE"):
        options["private_key_file"] = os.environ["SNOWFLAKE_PRIVATE_KEY_FILE"]
    else:
        options["password"] = os.environ["SNOWFLAKE_PASSWORD"]
    return snowflake.connector.connect(**options)


def setup_snowflake(cursor) -> None:
    cursor.execute(f"CREATE STAGE IF NOT EXISTS {STAGE}")
    cursor.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE} (
        VINTAGE_MONTH VARCHAR NOT NULL, AVAILABLE_AT DATE NOT NULL, SHEET VARCHAR NOT NULL,
        PLANT_ID VARCHAR NOT NULL, GENERATOR_ID VARCHAR NOT NULL, ENTITY_NAME VARCHAR,
        PLANT_NAME VARCHAR, STATE VARCHAR, SECTOR VARCHAR, TECHNOLOGY VARCHAR,
        NAMEPLATE_CAPACITY_MW VARCHAR, PLANNED_OPERATION_MONTH VARCHAR,
        ACTUAL_OPERATING_MONTH VARCHAR, STATUS VARCHAR, ENTITY_ID VARCHAR, SOURCE_URL VARCHAR NOT NULL,
        SOURCE_FILE_SHA256 VARCHAR NOT NULL, RETRIEVED_AT TIMESTAMP_TZ NOT NULL
    )""")
    cursor.execute(f"""CREATE TABLE IF NOT EXISTS {MANIFEST_TABLE} (
        VINTAGE_MONTH VARCHAR NOT NULL, SOURCE_FILE_SHA256 VARCHAR NOT NULL,
        SOURCE_URL VARCHAR NOT NULL, SOURCE_FILENAME VARCHAR NOT NULL, SOURCE_SIZE_BYTES NUMBER(38,0) NOT NULL,
        RETRIEVED_AT TIMESTAMP_TZ NOT NULL, AVAILABLE_AT DATE NOT NULL,
        PLANNED_ROWS NUMBER(38,0) NOT NULL, OPERATING_ROWS NUMBER(38,0) NOT NULL,
        CANCELED_ROWS NUMBER(38,0) NOT NULL, STAGE_PATH VARCHAR NOT NULL, LICENSE_STATUS VARCHAR NOT NULL,
        PRIMARY KEY (VINTAGE_MONTH, SOURCE_FILE_SHA256)
    )""")


def record_rows(vintage: str, file_hash: str, source_url: str, retrieved_at: str,
                sheets: dict[str, list[Any]]) -> list[dict[str, str]]:
    year, month = month_key(vintage)
    available = date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)
    # The prior month-end is used so we never allow that vintage before its month had ended.
    from datetime import timedelta
    available_text = (available - timedelta(days=1)).isoformat()
    # The shared EIA parser retains owner/entity name but its current dataclass omits
    # Entity ID. Recover that source field from the same original workbook by stable
    # plant/generator keys instead of silently losing it in the central archive.
    entity_ids: dict[tuple[str, str, str], str] = {}
    month_name = calendar.month_name[month].lower()
    path = ROOT / "results" / "eia-cache" / f"{month_name}_generator{year}.xlsx"
    for sheet_name, sheet_rows in read_sheets(path, tuple(sheets)).items():
        header_i = find_header(sheet_rows)
        header = sheet_rows[header_i]
        plant_col = header.index("Plant ID") if "Plant ID" in header else -1
        generator_col = header.index("Generator ID") if "Generator ID" in header else -1
        entity_col = header.index("Entity ID") if "Entity ID" in header else -1
        if min(plant_col, generator_col, entity_col) < 0:
            continue
        for raw in sheet_rows[header_i + 1:]:
            if max(plant_col, generator_col, entity_col) < len(raw):
                entity_ids[(sheet_name, raw[plant_col], raw[generator_col])] = raw[entity_col]
    rows = []
    for sheet, generators in sheets.items():
        for g in generators:
            rows.append({
                "vintage_month": vintage, "available_at": available_text, "sheet": sheet,
                "plant_id": g.plant_id, "generator_id": g.generator_id,
                "entity_name": g.entity_name, "plant_name": g.plant_name, "state": g.state,
                "sector": g.sector, "technology": g.technology, "capacity_mw": g.capacity_mw,
                "planned_month": g.statement, "actual_month": g.realized, "status": g.status,
                "entity_id": entity_ids.get((sheet, g.plant_id, g.generator_id), ""), "source_url": source_url,
                "source_file_sha256": file_hash, "retrieved_at": retrieved_at,
            })
    return rows


def tiger_aggregates(vintage: str, file_hash: str, rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    accum: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        key = (row["state"], row["sheet"], row["technology"])
        rec = accum.setdefault(key, {"generator_count": 0, "capacity_mw": Decimal(0)})
        rec["generator_count"] += 1
        try:
            rec["capacity_mw"] += Decimal(row["capacity_mw"].replace(",", ""))
        except (InvalidOperation, AttributeError):
            pass
    output = []
    for index, ((state, sheet, technology), values) in enumerate(sorted(accum.items())):
        payload = {
            "vintage_month": vintage, "source_file_sha256": file_hash, "state": state,
            "inventory_sheet": sheet, "technology": technology,
            "generator_count": values["generator_count"], "nameplate_capacity_mw": str(values["capacity_mw"]),
        }
        output.append({**payload, "row_index": index, "row_sha256": hashlib.sha256(canonical(payload).encode()).hexdigest()})
    return output


def put_local(cursor, local_path: Path, stage_path: str) -> None:
    uri = local_path.resolve().as_uri().replace("'", "''")
    cursor.execute(f"PUT '{uri}' @{STAGE}/{stage_path} AUTO_COMPRESS=FALSE OVERWRITE=FALSE")
    result = cursor.fetchone()
    if result and len(result) > 6 and str(result[6]).upper() not in {"UPLOADED", "SKIPPED"}:
        raise RuntimeError("Snowflake stage upload did not report success")


def write_snowflake(vintage: str, file_hash: str, source_url: str, source_path: Path,
                    retrieved_at: str, rows: list[dict[str, str]], aggregates: list[dict[str, Any]]) -> None:
    csv_dir = ROOT / "results" / "eia-cache" / "parsed"
    csv_dir.mkdir(parents=True, exist_ok=True)
    csv_path = csv_dir / f"records-{vintage}-{file_hash[:12]}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    stage_path = f"vintage={vintage}/sha256={file_hash}"
    with snowflake_connection() as connection:
        with connection.cursor() as cursor:
            setup_snowflake(cursor)
            cursor.execute(f"SELECT COUNT(*) FROM {TABLE} WHERE VINTAGE_MONTH=%s AND SOURCE_FILE_SHA256=%s", (vintage, file_hash))
            existing = int(cursor.fetchone()[0])
            if existing not in (0, len(rows)):
                raise RuntimeError(f"existing Snowflake vintage has {existing} rows; expected {len(rows)}")
            if existing == 0:
                # PUT treats the destination as a directory and appends the local basename.
                put_local(cursor, source_path, stage_path)
                put_local(cursor, csv_path, stage_path)
                cursor.execute(f"""COPY INTO {TABLE} ({', '.join(SNOWFLAKE_COLUMNS)})
                    FROM @{STAGE}/{stage_path}/ FILE_FORMAT=(TYPE=CSV SKIP_HEADER=1
                    FIELD_OPTIONALLY_ENCLOSED_BY='"' EMPTY_FIELD_AS_NULL=TRUE)
                    FILES=('{csv_path.name}') ON_ERROR='ABORT_STATEMENT'""")
                cursor.execute(f"SELECT COUNT(*) FROM {TABLE} WHERE VINTAGE_MONTH=%s AND SOURCE_FILE_SHA256=%s", (vintage, file_hash))
                count = int(cursor.fetchone()[0])
                if count != len(rows):
                    raise RuntimeError(f"Snowflake vintage row count {count} != {len(rows)}")
            else:
                count = existing
            # CSVs are transient COPY inputs: parsed rows are verified in the table and
            # the original XLSX is the archival object. Remove only this exact CSV object.
            cursor.execute(f"REMOVE @{STAGE}/{stage_path}/{csv_path.name}")

            available = rows[0]["available_at"]
            counts = {sheet: sum(row["sheet"] == sheet for row in rows)
                      for sheet in ("Planned", "Operating", "Canceled or Postponed")}
            license_status = "public U.S. EIA-860M archive; source attribution and raw XLSX retained"
            cursor.execute(f"""MERGE INTO {MANIFEST_TABLE} t USING
                (SELECT %s VINTAGE_MONTH,%s SOURCE_FILE_SHA256,%s SOURCE_URL,%s SOURCE_FILENAME,
                 %s SOURCE_SIZE_BYTES,%s RETRIEVED_AT,%s AVAILABLE_AT,%s PLANNED_ROWS,%s OPERATING_ROWS,
                 %s CANCELED_ROWS,%s STAGE_PATH,%s LICENSE_STATUS) s
                ON t.VINTAGE_MONTH=s.VINTAGE_MONTH AND t.SOURCE_FILE_SHA256=s.SOURCE_FILE_SHA256
                WHEN MATCHED THEN UPDATE SET RETRIEVED_AT=s.RETRIEVED_AT
                WHEN NOT MATCHED THEN INSERT (VINTAGE_MONTH,SOURCE_FILE_SHA256,SOURCE_URL,SOURCE_FILENAME,
                 SOURCE_SIZE_BYTES,RETRIEVED_AT,AVAILABLE_AT,PLANNED_ROWS,OPERATING_ROWS,CANCELED_ROWS,
                 STAGE_PATH,LICENSE_STATUS) VALUES (s.VINTAGE_MONTH,s.SOURCE_FILE_SHA256,s.SOURCE_URL,
                 s.SOURCE_FILENAME,s.SOURCE_SIZE_BYTES,s.RETRIEVED_AT,s.AVAILABLE_AT,s.PLANNED_ROWS,
                 s.OPERATING_ROWS,s.CANCELED_ROWS,s.STAGE_PATH,s.LICENSE_STATUS)""",
                (vintage, file_hash, source_url, source_path.name, source_path.stat().st_size,
                 retrieved_at, available, counts["Planned"], counts["Operating"],
                 counts["Canceled or Postponed"], stage_path, license_status))
            connection.commit()
    print(f"Snowflake EIA-860M {vintage}: generators={len(rows)} staged_original={stage_path}/original.xlsx sha256={file_hash}", flush=True)


def write_tiger(vintage: str, file_hash: str, source_url: str, retrieved_at: str,
                raw_rows: list[dict[str, str]], aggregates: list[dict[str, Any]]) -> None:
    import psycopg

    sync.load_local_env()
    with psycopg.connect(os.environ["TIGERDATA_URL"], password=os.environ["TIGERDATA_PASSWORD"], connect_timeout=20) as connection:
        with connection.cursor() as cursor:
            cursor.execute("""CREATE TABLE IF NOT EXISTS public.gqh_eia860m_state_vintage (
                source_file_sha256 char(64) NOT NULL, row_index integer NOT NULL,
                vintage_month date NOT NULL, available_at date NOT NULL,
                state text NOT NULL, inventory_sheet text NOT NULL,
                technology text NOT NULL, generator_count bigint NOT NULL,
                nameplate_capacity_mw numeric(24,6) NOT NULL, row_sha256 char(64) NOT NULL,
                source_url text NOT NULL, retrieved_at timestamptz NOT NULL,
                PRIMARY KEY(source_file_sha256,row_index))""")
            cursor.executemany("""INSERT INTO public.gqh_eia860m_state_vintage
                (source_file_sha256,row_index,vintage_month,available_at,state,inventory_sheet,technology,generator_count,
                 nameplate_capacity_mw,row_sha256,source_url,retrieved_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (source_file_sha256,row_index) DO NOTHING""",
                [(file_hash, row["row_index"], vintage + "-01", raw_rows[0]["available_at"], row["state"], row["inventory_sheet"],
                  row["technology"], row["generator_count"], row["nameplate_capacity_mw"],
                  row["row_sha256"], source_url, retrieved_at) for row in aggregates])
            cursor.execute("""SELECT row_sha256 FROM public.gqh_eia860m_state_vintage
                WHERE source_file_sha256=%s ORDER BY row_index""", (file_hash,))
            actual = [item[0] for item in cursor.fetchall()]
            expected = [row["row_sha256"] for row in aggregates]
            if actual != expected:
                raise RuntimeError(f"TigerData aggregate hash reconciliation failed for {vintage}")
            manifest = {
                "source_id": "eia860m_generator_vintages", "batch_sha256": file_hash,
                "retrieved_at_utc": retrieved_at, "source_url": source_url,
                "row_count": len(raw_rows), "tiger_aggregate_count": len(aggregates),
                "license": "public U.S. EIA-860M archive; source attribution and raw XLSX retained",
                "vintage_month": vintage, "availability_end_of_month": raw_rows[0]["available_at"],
                "source_file_sha256": file_hash,
            }
            cursor.execute("""INSERT INTO public.gqh_ingestion_manifests
                (source_id,batch_sha256,retrieved_at,source_url,row_count,source_license,manifest_json)
                VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb)
                ON CONFLICT (source_id,batch_sha256) DO UPDATE SET
                    retrieved_at=EXCLUDED.retrieved_at,manifest_json=EXCLUDED.manifest_json""",
                ("eia860m_generator_vintages", file_hash, retrieved_at, source_url, len(raw_rows),
                 manifest["license"], canonical(manifest)))
        connection.commit()
    print(f"TigerData EIA-860M {vintage}: state-summary={len(aggregates)}; full records remain in Snowflake", flush=True)


def ingest_one(year: int, month: int, url: str, target: str) -> None:
    path = fetch_vintage(year, month)
    raw = path.read_bytes()
    file_hash = hashlib.sha256(raw).hexdigest()
    vintage = f"{year:04d}-{month:02d}"
    retrieved_at = datetime.now(timezone.utc).isoformat()
    parsed = read_vintage(path, year, month)
    rows = record_rows(vintage, file_hash, url, retrieved_at, parsed)
    if not rows or not all(sheet in parsed for sheet in ("Planned", "Operating", "Canceled or Postponed")):
        raise RuntimeError(f"EIA-860M vintage {vintage} incomplete")
    aggregates = tiger_aggregates(vintage, file_hash, rows)
    write_snowflake(vintage, file_hash, url, path, retrieved_at, rows, aggregates)
    if target == "both":
        write_tiger(vintage, file_hash, url, retrieved_at, rows, aggregates)


def main() -> int:
    sync.load_local_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-month", default="2016-01")
    parser.add_argument("--to-month", default="")
    parser.add_argument("--limit", type=int, default=0, help="small smoke test; 0 means all selected vintages")
    parser.add_argument("--target", choices=("both", "snowflake"), default="snowflake",
                        help="default is Snowflake because TigerData is near/over its observed quota; use both only after verifying capacity")
    args = parser.parse_args()
    start = month_key(args.from_month)
    if args.to_month:
        end = month_key(args.to_month)
    else:
        today = date.today()
        previous_month = today.month - 1 or 12
        previous_year = today.year if today.month > 1 else today.year - 1
        end = (previous_year, previous_month)
    if end < start:
        parser.error("--to-month precedes --from-month")
    index = vintage_index()
    months = sorted(month for month in index if start <= month <= end)
    expected = []
    y, m = start
    while (y, m) <= end:
        expected.append((y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    missing = sorted(set(expected) - set(months))
    if missing:
        raise RuntimeError(f"EIA-860M public archive index misses requested vintages: {missing[:12]}")
    if args.limit:
        months = months[:args.limit]
    for year, month in months:
        ingest_one(year, month, index[(year, month)], args.target)
    print(f"completed EIA-860M vintages: {len(months)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
