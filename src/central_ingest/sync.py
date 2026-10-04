#!/usr/bin/env python3
"""Load one source snapshot into the team's Snowflake and TigerData stores."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zipfile import ZipFile
from urllib.parse import urlencode


ROOT = Path(__file__).resolve().parents[2]
LOCAL_ENV_KEYS = {
    "TIGERDATA_URL", "TIGERDATA_PASSWORD", "SNOWFLAKE_CONNECTION_NAME", "SNOWFLAKE_ACCOUNT",
    "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD", "SNOWFLAKE_WAREHOUSE",
    "SNOWFLAKE_ROLE", "SNOWFLAKE_PRIVATE_KEY_FILE", "MASSIVE_API_KEY",
    "GQH_MASSIVE_TEAM_STRATEGY_LICENSE", "EDGAR_USER_AGENT", "FMP_API_KEY",
}


def load_local_env() -> None:
    """Read a simple gitignored KEY=VALUE file without shell evaluation."""
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if separator and key in LOCAL_ENV_KEYS and value:
            os.environ.setdefault(key, value.strip())


@dataclass(frozen=True)
class Source:
    path: str
    url: str
    required: tuple[str, ...]
    event_field: str
    available_field: str = ""
    license_status: str = "source terms not assessed by loader; review before external redistribution"


SOURCES: dict[str, Source] = {
    "sec_filings": Source("results/filings-register.csv", "https://data.sec.gov/submissions/", ("cik", "accession", "acceptance_utc"), "acceptance_utc", "earliest_availability_utc"),
    "sec_obligation_facts": Source(
        "results/obligation-panel.csv",
        "https://data.sec.gov/api/xbrl/companyfacts/",
        ("ticker", "cik", "concept", "period_end", "value", "change", "accession",
         "acceptance_utc", "earliest_availability_utc"),
        "earliest_availability_utc", "earliest_availability_utc",
        license_status="public SEC Company Facts-derived event panel; preserve SEC attribution; derived panel, not raw filing text",
    ),
    "aws_compute_monthly_family": Source(
        "results/compute-price-monthly.csv",
        "https://doi.org/10.5281/zenodo.23082767",
        ("month", "family", "quotes", "median_usd_per_instance_hour", "zones"),
        "month",
        license_status="CC BY 4.0; derived monthly family medians from AWS Spot Price History v2026-09; cite the Zenodo DOI",
    ),
    "sec_provider_capex_quarterly": Source(
        "results/provider-capex-quarterly.csv",
        "https://data.sec.gov/api/xbrl/companyfacts/",
        ("ticker", "cik", "concept", "period_end", "value_usd", "form", "filed", "fy", "fp"),
        "period_end",
        license_status="Public SEC Company Facts-derived quarterly panel; preserve SEC attribution; current extract may contain restated values and is not a PIT vintage archive",
    ),
    "census_c30": Source("data/orthogonal-starter-2026-10-03/census_c30_ai_infra_nsa.csv", "https://www.census.gov/construction/c30/xlsx/privtime.xlsx", ("observation_month", "data_center_musd"), "observation_month"),
    "eia860m_full_2024_12": Source("data/public-first-wave/eia860m-2024-12-capacity.csv", "https://www.eia.gov/electricity/data/eia860m/archive/xls/december_generator2024.xlsx", ("inventory_status", "vintage_month", "plant_id", "generator_id"), "vintage_month"),
    "eia860m_proposed_2024_12": Source("data/public-first-wave/eia860m-2024-12-proposed.csv", "https://www.eia.gov/electricity/data/eia860m/archive/xls/december_generator2024.xlsx", ("vintage_month", "inventory_status", "plant_id", "generator_id"), "vintage_month"),
    "eia930_pjm_sample": Source("data/public-first-wave/eia930-pjm-2024-01-01.csv", "https://api.eia.gov/v2/electricity/rto/region-data/data/", ("period", "respondent", "demand_mwh"), "period"),
    "hyperliquid_ws_capture": Source("data/hyperliquid/ws", "wss://api.hyperliquid.xyz/ws",
                                      ("recv_ts", "channel"), "recv_ts", "available_at"),
    "hyperliquid_book_capture": Source("data/hyperliquid/book", "https://api.hyperliquid.xyz/info",
                                       ("recv_ts", "coin"), "recv_ts", "available_at"),
    "philly_delivery_times": Source("data/orthogonal-starter-2026-10-03/philly_delivery_times.csv", "https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/MBOS/Historical-Data/Data-Series/bos_history.csv?sc_lang=en", ("DATE", "dtcdfsa"), "DATE"),
    "nyfed_gscpi": Source("data/orthogonal-starter-2026-10-03/nyfed_gscpi_monthly.csv", "https://www.newyorkfed.org/medialibrary/research/interactives/gscpi/downloads/gscpi_data.xlsx", ("observation_date", "gscpi"), "observation_date"),
    "fred_rates": Source("data/orthogonal-starter-2026-10-03/fred_daily.csv", "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS2,DGS10", ("observation_date", "DGS10"), "observation_date"),
    "fred_market": Source("data/orthogonal-starter-2026-10-03/fred_daily_close.csv", "https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS,NASDAQCOM", ("observation_date",), "observation_date"),
    "fred_industry": Source("data/orthogonal-starter-2026-10-03/fred_monthly.csv", "https://fred.stlouisfed.org/graph/fredgraph.csv?id=FEDFUNDS,IPG3344S", ("observation_date",), "observation_date"),
}

M3_FILES = {
    "m3_shipments": ("shipments.xlsx", "naicsvsp.xlsx"),
    "m3_new_orders": ("new_orders.xlsx", "naicsnop.xlsx"),
    "m3_unfilled_orders": ("unfilled_orders.xlsx", "naicsuop.xlsx"),
}
M3_SERIES = {"35S", "35C", "34S", "34A", "33S", "33H", "ITI", "CRP"}

TIGER_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS public.gqh_source_records (
    source_id text NOT NULL,
    batch_sha256 char(64) NOT NULL,
    row_index integer NOT NULL,
    event_time_text text,
    available_at_text text,
    source_url text NOT NULL,
    payload_json jsonb NOT NULL,
    row_sha256 char(64) NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (source_id, batch_sha256, row_index)
)
"""
TIGER_INDEX_DDL = """CREATE INDEX IF NOT EXISTS gqh_source_records_source_event_idx
    ON public.gqh_source_records (source_id, event_time_text)"""

SNOWFLAKE_DDL = """
CREATE TABLE IF NOT EXISTS VECTOR_RESEARCH.RAW.SOURCE_RECORDS (
    SOURCE_ID VARCHAR NOT NULL,
    BATCH_SHA256 VARCHAR NOT NULL,
    ROW_INDEX NUMBER(38,0) NOT NULL,
    EVENT_TIME_TEXT VARCHAR,
    AVAILABLE_AT_TEXT VARCHAR,
    SOURCE_URL VARCHAR NOT NULL,
    PAYLOAD_JSON VARCHAR NOT NULL,
    ROW_SHA256 VARCHAR NOT NULL,
    LOADED_AT TIMESTAMP_TZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (SOURCE_ID, BATCH_SHA256, ROW_INDEX)
)"""

TIGER_MANIFEST_DDL = """
CREATE TABLE IF NOT EXISTS public.gqh_ingestion_manifests (
    source_id text NOT NULL,
    batch_sha256 char(64) NOT NULL,
    retrieved_at timestamptz NOT NULL,
    source_url text NOT NULL,
    row_count bigint NOT NULL,
    source_license text NOT NULL,
    manifest_json jsonb NOT NULL,
    PRIMARY KEY (source_id, batch_sha256)
)
"""

SNOWFLAKE_MANIFEST_DDL = """
CREATE TABLE IF NOT EXISTS VECTOR_RESEARCH.RAW.INGESTION_MANIFESTS (
    SOURCE_ID VARCHAR NOT NULL,
    BATCH_SHA256 VARCHAR NOT NULL,
    RETRIEVED_AT TIMESTAMP_TZ NOT NULL,
    SOURCE_URL VARCHAR NOT NULL,
    ROW_COUNT NUMBER(38,0) NOT NULL,
    SOURCE_LICENSE VARCHAR NOT NULL,
    MANIFEST_JSON VARCHAR NOT NULL,
    PRIMARY KEY (SOURCE_ID, BATCH_SHA256)
)
"""


def canonical(row: dict[str, Any]) -> str:
    return json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def read_csv(source_id: str) -> tuple[list[dict[str, Any]], Source]:
    source = SOURCES[source_id]
    path = ROOT / source.path
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or not set(source.required).issubset(reader.fieldnames):
            raise ValueError(f"{source_id}: missing required columns")
        rows = list(reader)
    if not rows:
        raise ValueError(f"{source_id}: empty source")
    return rows, source


def read_jsonl_capture(source_id: str) -> tuple[list[dict[str, Any]], Source]:
    """Read a local JSONL capture directory as one batch: one row per recorded message.

    The payload keeps the recorded message and its file and line, so provenance survives the load. New
    files produce a new batch; the repo's rule is to query by source and pick the intended batch hash.
    """
    source = SOURCES[source_id]
    directory = ROOT / source.path
    files = sorted(directory.glob("*.jsonl"))
    if not files:
        raise ValueError(f"{source_id}: no capture files under {source.path}")
    rows: list[dict[str, Any]] = []
    for path in files:
        for number, line in enumerate(path.open(), start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            missing = [key for key in source.required if key not in record]
            if missing:
                raise ValueError(f"{source_id}: {path.name} line {number} missing {missing}")
            try:
                stamp = float(record["recv_ts"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{source_id}: {path.name} line {number} bad recv_ts") from exc
            iso = datetime.fromtimestamp(stamp, timezone.utc).isoformat()
            rows.append({"recv_ts": iso, "available_at": iso, "file": path.name, "line": number,
                         "channel": record.get("channel"), "payload": record.get("data")})
    if not rows:
        raise ValueError(f"{source_id}: empty capture")
    return rows, source


def read_m3(source_id: str) -> tuple[list[dict[str, Any]], Source]:
    import openpyxl

    filename, upstream = M3_FILES[source_id]
    path = ROOT / "data/public-first-wave/m3" / filename
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rows: list[dict[str, Any]] = []
    try:
        for source_row in workbook.active.values:
            series_id, year, *months = source_row
            if not isinstance(series_id, str) or series_id[1:4] not in M3_SERIES:
                continue
            if series_id[0] not in ("A", "U") or not isinstance(year, int):
                raise ValueError(f"{source_id}: malformed M3 series/year")
            for month, value in enumerate(months[:12], start=1):
                if value is None:
                    continue
                if not isinstance(value, (int, float)):
                    raise ValueError(f"{source_id}: nonnumeric M3 observation")
                rows.append({
                    "observation_month": f"{year:04d}-{month:02d}",
                    "source_series_id": series_id,
                    "series_code": series_id[1:4],
                    "seasonal_adjustment": "seasonally_adjusted" if series_id[0] == "A" else "unadjusted",
                    "metric": source_id.removeprefix("m3_"),
                    "value_musd": value,
                })
    finally:
        workbook.close()
    if not rows:
        raise ValueError(f"{source_id}: no selected observations")
    source = Source("data/public-first-wave/m3/" + filename,
                    "https://www.census.gov/manufacturing/m3/prel/historical_data/histshts/naics/" + upstream,
                    ("observation_month", "source_series_id", "value_musd"), "observation_month")
    return rows, source


def read_eia923_pjm_2024() -> tuple[list[dict[str, Any]], Source]:
    """Extract a small PJM plant/fuel/month panel from EIA's 2024 final workbook."""
    import openpyxl

    path = ROOT / "data/public-first-wave/eia923_2024.zip"
    with ZipFile(path) as archive:
        member = next((name for name in archive.namelist() if "Schedules_2_3_4_5" in name), None)
        if member is None:
            raise ValueError("EIA-923 workbook is missing from source ZIP")
        workbook = openpyxl.load_workbook(io.BytesIO(archive.read(member)), read_only=True, data_only=True)
    try:
        sheet = workbook["Page 1 Generation and Fuel Data"]
        rows: list[dict[str, Any]] = []
        for number, record in enumerate(sheet.values, start=1):
            if number <= 6 or record[16] != "PJM":
                continue
            plant_id = record[0]
            if not isinstance(plant_id, (int, float)):
                continue
            for month in range(1, 13):
                netgen = record[78 + month]
                heat_input = record[54 + month]
                if not isinstance(netgen, (int, float)) and not isinstance(heat_input, (int, float)):
                    continue
                rows.append({
                    "observation_month": f"2024-{month:02d}",
                    "plant_id": int(plant_id),
                    "plant_name": record[3],
                    "plant_state": record[6],
                    "balancing_authority": "PJM",
                    "prime_mover": record[13],
                    "fuel_code": record[14],
                    "net_generation_mwh": netgen if isinstance(netgen, (int, float)) else None,
                    "total_fuel_mmbtu": heat_input if isinstance(heat_input, (int, float)) else None,
                    "source_vintage": "2024_final",
                })
    finally:
        workbook.close()
    if not rows:
        raise ValueError("EIA-923 PJM source has no numeric observations")
    return rows, Source("data/public-first-wave/eia923_2024.zip",
                        "https://www.eia.gov/electricity/data/eia923/archive/xls/f923_2024.zip",
                        ("observation_month", "plant_id"), "observation_month")


def read_massive(source_id: str, start: str, end: str, tickers: list[str]) -> tuple[list[dict[str, Any]], Source]:
    if os.getenv("GQH_MASSIVE_TEAM_STRATEGY_LICENSE") != "confirmed":
        raise ValueError("Set GQH_MASSIVE_TEAM_STRATEGY_LICENSE=confirmed after sponsor confirmation")
    key = os.getenv("MASSIVE_API_KEY")
    if not key:
        raise ValueError("MASSIVE_API_KEY is not set")
    if not start or not end or start > end:
        raise ValueError("Massive needs --from and --to in YYYY-MM-DD order")
    # This macOS Python environment lacks a usable system CA bundle. The Snowflake connector
    # already depends on certifi; let urllib use the same trusted CA bundle for HTTPS.
    if not os.getenv("SSL_CERT_FILE"):
        import certifi
        os.environ["SSL_CERT_FILE"] = certifi.where()
    from massive import (DISCLOSURE_FIELDS, request_json, get_bars,
                         get_corporate_actions, get_ticker_events, get_ticker_details)

    rows: list[dict[str, Any]] = []
    for ticker in tickers or ["PWR", "ETN", "EME", "DLR", "SPY"]:
        ticker = ticker.upper()
        if source_id in ("massive_bars", "massive_bars_unadjusted"):
            rows.extend(get_bars(ticker, start, end, key, adjusted=(source_id == "massive_bars")))
            continue
        if source_id in ("massive_splits", "massive_dividends"):
            action = "splits" if source_id == "massive_splits" else "dividends"
            rows.extend(get_corporate_actions(action, ticker, start, end, key))
            continue
        if source_id == "massive_ticker_events":
            rows.extend(get_ticker_events(ticker, key))
            continue
        if source_id == "massive_ticker_metadata":
            rows.append(get_ticker_details(ticker, start, key))
            rows.append(get_ticker_details(ticker, end, key))
            continue
        query = urlencode({"tickers": ticker, "filing_date.gte": start,
                           "filing_date.lte": end, "limit": 1000})
        url = f"https://api.massive.com/stocks/filings/8-K/vX/disclosures?{query}"
        while url:
            page = request_json(url, key)
            for result in page.get("results", []):
                if not result.get("accession_number") or not result.get("filing_date"):
                    raise ValueError("Massive disclosure lacks filing identity")
                rows.append({field: result.get(field) for field in DISCLOSURE_FIELDS})
            url = page.get("next_url")
    if source_id == "massive_8k":
        unique = {}
        for row in rows:
            identity = (row["accession_number"], row.get("tertiary_category"), row.get("supporting_text"))
            unique[identity] = row
        rows = sorted(unique.values(), key=lambda row: (row["filing_date"], row["accession_number"], row.get("tertiary_category") or ""))
    if not rows and source_id in {"massive_splits", "massive_dividends", "massive_ticker_events"}:
        rows = [{"record_kind": "empty_interval_receipt", "ticker": ticker.upper(),
                 "requested_from": start, "requested_to": end, "result_count": 0}
                for ticker in (tickers or ["PWR", "ETN", "EME", "DLR", "SPY"])]
    if not rows:
        raise ValueError(f"{source_id}: no observations returned")
    massive_license = "Massive GQH sponsor permission confirmed by project lead; project-scoped use"
    source_info = {
        "massive_bars": Source("", "https://api.massive.com/v2/aggs/ticker/", ("ticker", "bar_time_utc"), "bar_time_utc", license_status=massive_license),
        "massive_bars_unadjusted": Source("", "https://api.massive.com/v2/aggs/ticker/", ("ticker", "bar_time_utc"), "bar_time_utc", license_status=massive_license),
        "massive_8k": Source("", "https://api.massive.com/stocks/filings/8-K/vX/disclosures", ("accession_number", "filing_date"), "filing_date", license_status=massive_license),
        "massive_splits": Source("", "https://api.massive.com/stocks/v1/splits", ("ticker", "execution_date"), "execution_date", license_status=massive_license),
        "massive_dividends": Source("", "https://api.massive.com/stocks/v1/dividends", ("ticker", "ex_dividend_date"), "ex_dividend_date", license_status=massive_license),
        "massive_ticker_events": Source("", "https://api.massive.com/vX/reference/tickers/{id}/events", ("ticker",), "ticker", license_status=massive_license),
        "massive_ticker_metadata": Source("", "https://api.massive.com/v3/reference/tickers/{ticker}?date={as_of_date}", ("requested_ticker", "as_of_date"), "as_of_date", license_status=massive_license),
    }
    return rows, source_info[source_id]


def make_batch(source_id: str, rows: list[dict[str, Any]], source: Source) -> tuple[str, list[tuple]]:
    if not rows:
        raise ValueError("empty batch")
    payloads = [canonical(row) for row in rows]
    batch_sha = hashlib.sha256((source_id + "\n" + "\n".join(payloads)).encode()).hexdigest()
    encoded = []
    for index, (row, payload) in enumerate(zip(rows, payloads)):
        encoded.append((source_id, batch_sha, index, row.get(source.event_field),
                        row.get(source.available_field) if source.available_field else None,
                        source.url, payload, hashlib.sha256(payload.encode()).hexdigest()))
    return batch_sha, encoded


def tiger_load(url: str, source_id: str, batch_sha: str, encoded: list[tuple], manifest: dict[str, Any]) -> int:
    import psycopg

    with psycopg.connect(url, password=os.getenv("TIGERDATA_PASSWORD"), connect_timeout=20) as connection:
        with connection.cursor() as cursor:
            cursor.execute(TIGER_TABLE_DDL)
            cursor.execute(TIGER_INDEX_DDL)
            cursor.execute(TIGER_MANIFEST_DDL)
            cursor.executemany("""
                INSERT INTO public.gqh_source_records
                    (source_id,batch_sha256,row_index,event_time_text,available_at_text,
                     source_url,payload_json,row_sha256)
                VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s)
                ON CONFLICT (source_id,batch_sha256,row_index) DO NOTHING
            """, encoded)
            cursor.execute("SELECT count(*) FROM public.gqh_source_records WHERE source_id=%s AND batch_sha256=%s", (source_id, batch_sha))
            count = cursor.fetchone()[0]
            if count != len(encoded):
                raise RuntimeError(f"TigerData row count {count} != source rows {len(encoded)}")
            cursor.execute("""SELECT row_sha256 FROM public.gqh_source_records
                WHERE source_id=%s AND batch_sha256=%s ORDER BY row_index""",
                (source_id, batch_sha))
            if [row[0] for row in cursor.fetchall()] != [row[7] for row in encoded]:
                raise RuntimeError("TigerData row hash reconciliation failed")
            cursor.execute("""INSERT INTO public.gqh_ingestion_manifests
                (source_id,batch_sha256,retrieved_at,source_url,row_count,source_license,manifest_json)
                VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb)
                ON CONFLICT (source_id,batch_sha256) DO UPDATE SET
                    retrieved_at=EXCLUDED.retrieved_at, row_count=EXCLUDED.row_count,
                    source_license=EXCLUDED.source_license, manifest_json=EXCLUDED.manifest_json""",
                (source_id, batch_sha, manifest["retrieved_at_utc"], manifest["source_url"],
                 len(encoded), manifest["license"], canonical(manifest)))
        connection.commit()
    return count


def snowflake_load(source_id: str, batch_sha: str, encoded: list[tuple], manifest: dict[str, Any]) -> int:
    import snowflake.connector

    name = os.getenv("SNOWFLAKE_CONNECTION_NAME")
    if name:
        connection = snowflake.connector.connect(connection_name=name)
    else:
        options = {
            "account": os.environ["SNOWFLAKE_ACCOUNT"],
            "user": os.environ["SNOWFLAKE_USER"],
            "warehouse": os.environ["SNOWFLAKE_WAREHOUSE"],
            "database": "VECTOR_RESEARCH",
            "schema": "RAW",
        }
        if os.getenv("SNOWFLAKE_ROLE"):
            options["role"] = os.environ["SNOWFLAKE_ROLE"]
        if os.getenv("SNOWFLAKE_PRIVATE_KEY_FILE"):
            options["private_key_file"] = os.environ["SNOWFLAKE_PRIVATE_KEY_FILE"]
        else:
            options["password"] = os.environ["SNOWFLAKE_PASSWORD"]
        connection = snowflake.connector.connect(**options)
    try:
        with connection.cursor() as cursor:
            cursor.execute(SNOWFLAKE_DDL)
            cursor.execute(SNOWFLAKE_MANIFEST_DDL)
            cursor.execute("""CREATE TEMPORARY TABLE GQH_LOAD_STAGE (
                SOURCE_ID VARCHAR, BATCH_SHA256 VARCHAR, ROW_INDEX NUMBER(38,0),
                EVENT_TIME_TEXT VARCHAR, AVAILABLE_AT_TEXT VARCHAR, SOURCE_URL VARCHAR,
                PAYLOAD_JSON VARCHAR, ROW_SHA256 VARCHAR)""")
            cursor.executemany("INSERT INTO GQH_LOAD_STAGE VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", encoded)
            cursor.execute("""MERGE INTO VECTOR_RESEARCH.RAW.SOURCE_RECORDS t
                USING GQH_LOAD_STAGE s
                ON t.SOURCE_ID=s.SOURCE_ID AND t.BATCH_SHA256=s.BATCH_SHA256
                   AND t.ROW_INDEX=s.ROW_INDEX
                WHEN NOT MATCHED THEN INSERT
                    (SOURCE_ID,BATCH_SHA256,ROW_INDEX,EVENT_TIME_TEXT,AVAILABLE_AT_TEXT,
                     SOURCE_URL,PAYLOAD_JSON,ROW_SHA256)
                VALUES (s.SOURCE_ID,s.BATCH_SHA256,s.ROW_INDEX,s.EVENT_TIME_TEXT,
                        s.AVAILABLE_AT_TEXT,s.SOURCE_URL,s.PAYLOAD_JSON,s.ROW_SHA256)""")
            cursor.execute("SELECT count(*) FROM VECTOR_RESEARCH.RAW.SOURCE_RECORDS WHERE SOURCE_ID=%s AND BATCH_SHA256=%s", (source_id, batch_sha))
            count = cursor.fetchone()[0]
            if count != len(encoded):
                raise RuntimeError(f"Snowflake row count {count} != source rows {len(encoded)}")
            cursor.execute("""SELECT ROW_SHA256 FROM VECTOR_RESEARCH.RAW.SOURCE_RECORDS
                WHERE SOURCE_ID=%s AND BATCH_SHA256=%s ORDER BY ROW_INDEX""",
                (source_id, batch_sha))
            if [row[0] for row in cursor.fetchall()] != [row[7] for row in encoded]:
                raise RuntimeError("Snowflake row hash reconciliation failed")
            cursor.execute("""MERGE INTO VECTOR_RESEARCH.RAW.INGESTION_MANIFESTS t
                USING (SELECT %s SOURCE_ID,%s BATCH_SHA256,%s RETRIEVED_AT,%s SOURCE_URL,
                       %s ROW_COUNT,%s SOURCE_LICENSE,%s MANIFEST_JSON) s
                ON t.SOURCE_ID=s.SOURCE_ID AND t.BATCH_SHA256=s.BATCH_SHA256
                WHEN MATCHED THEN UPDATE SET RETRIEVED_AT=s.RETRIEVED_AT,ROW_COUNT=s.ROW_COUNT,
                    SOURCE_LICENSE=s.SOURCE_LICENSE,MANIFEST_JSON=s.MANIFEST_JSON
                WHEN NOT MATCHED THEN INSERT
                    (SOURCE_ID,BATCH_SHA256,RETRIEVED_AT,SOURCE_URL,ROW_COUNT,SOURCE_LICENSE,MANIFEST_JSON)
                    VALUES (s.SOURCE_ID,s.BATCH_SHA256,s.RETRIEVED_AT,s.SOURCE_URL,s.ROW_COUNT,
                            s.SOURCE_LICENSE,s.MANIFEST_JSON)""",
                (source_id, batch_sha, manifest["retrieved_at_utc"], manifest["source_url"],
                 len(encoded), manifest["license"], canonical(manifest)))
        connection.commit()
        return count
    finally:
        connection.close()


def main() -> int:
    load_local_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--source", choices=sorted(SOURCES) + sorted(M3_FILES) + [
        "eia923_pjm_2024", "massive_bars", "massive_bars_unadjusted", "massive_8k",
        "massive_splits", "massive_dividends", "massive_ticker_events", "massive_ticker_metadata"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--target", choices=("both", "snowflake", "tigerdata"), default="snowflake",
                        help="defaults to Snowflake; use both only after confirming TigerData capacity")
    parser.add_argument("--from", dest="start")
    parser.add_argument("--to", dest="end")
    parser.add_argument("--ticker", action="append", default=[])
    args = parser.parse_args()
    if args.list:
        print("\n".join(sorted(SOURCES) + sorted(M3_FILES) + [
            "eia923_pjm_2024", "massive_bars", "massive_bars_unadjusted", "massive_8k",
            "massive_splits", "massive_dividends", "massive_ticker_events", "massive_ticker_metadata"]))
        return 0
    if not args.source:
        parser.error("--source is required unless --list is used")
    if not args.dry_run:
        if args.target in ("both", "tigerdata") and not os.getenv("TIGERDATA_URL"):
            parser.error("TIGERDATA_URL is required for shared loading")
        snowflake_base = all(os.getenv(key) for key in
                             ("SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_WAREHOUSE"))
        snowflake_auth = bool(os.getenv("SNOWFLAKE_PASSWORD") or os.getenv("SNOWFLAKE_PRIVATE_KEY_FILE"))
        if args.target in ("both", "snowflake") and not os.getenv("SNOWFLAKE_CONNECTION_NAME") and not (snowflake_base and snowflake_auth):
            parser.error("Snowflake connection name or account/user/password/warehouse is required")
    try:
        if args.source.startswith("massive_"):
            rows, source = read_massive(args.source, args.start, args.end, args.ticker)
        elif args.source in M3_FILES:
            rows, source = read_m3(args.source)
        elif args.source in ("hyperliquid_ws_capture", "hyperliquid_book_capture"):
            rows, source = read_jsonl_capture(args.source)
        elif args.source == "eia923_pjm_2024":
            rows, source = read_eia923_pjm_2024()
        else:
            rows, source = read_csv(args.source)
        batch_sha, encoded = make_batch(args.source, rows, source)
        if args.dry_run:
            print(f"validated {args.source}: rows={len(encoded)} batch_sha256={batch_sha}; no database writes")
            return 0
        manifest = {
            "source_id": args.source, "batch_sha256": batch_sha,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_path": source.path, "source_url": source.url,
            "requested_from": args.start, "requested_to": args.end,
            "tickers": [ticker.upper() for ticker in (args.ticker or ["PWR", "ETN", "EME", "DLR", "SPY"])],
            "row_count": len(encoded), "license": source.license_status,
            "availability_note": "available_at is populated only when source provides a timestamp; this batch time is retrieval/ingest time, not historical public availability",
        }
        snow_count = snowflake_load(args.source, batch_sha, encoded, manifest) if args.target in ("both", "snowflake") else "skipped"
        tiger_count = tiger_load(os.environ["TIGERDATA_URL"], args.source, batch_sha, encoded, manifest) if args.target in ("both", "tigerdata") else "skipped"
        print(f"loaded {args.source}: source={len(encoded)} snowflake={snow_count} tigerdata={tiger_count} batch_sha256={batch_sha}")
        return 0
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(f"load failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        # Driver exceptions can include connection strings or secret values.
        print(f"database/API operation failed ({type(exc).__name__}); details suppressed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
