"""Archive original SEC filing documents/exhibits and metadata to the Snowflake raw layer.

The SEC source is public and needs no API key, but requires a truthful contact User-Agent.
Run one operator at a time and stay well below SEC fair-access limits.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from zipfile import ZIP_DEFLATED, ZipFile

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "central_ingest"))
import sync

STAGE = "VECTOR_RESEARCH.RAW.SEC_FILING_ARCHIVE"
MANIFEST = "VECTOR_RESEARCH.RAW.SEC_FILING_PACKAGE_MANIFESTS"
DOCS = "VECTOR_RESEARCH.RAW.SEC_FILING_DOCUMENTS"
ARCHIVE_ROOT = "https://www.sec.gov/Archives/edgar/data"
KEY_TERMS = re.compile(
    r"backlog|remaining performance obligations|\bRPO\b|guidance|capital expenditure|\bcapex\b|"
    r"operating margin|gross margin|revenue|\bMW\b|megawatt|commission|delay|cancel|customer|"
    r"counterparty|segment", re.I)


class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())


def plain_text(data: bytes) -> str:
    parser = TextOnly()
    try:
        parser.feed(data.decode("utf-8", "replace"))
        return " ".join(parser.parts)
    except Exception:
        return data.decode("utf-8", "replace")


def contexts(data: bytes, limit: int = 160) -> list[str]:
    text = re.sub(r"\s+", " ", plain_text(data))
    out, seen = [], set()
    for match in KEY_TERMS.finditer(text):
        fragment = text[max(0, match.start() - 180):min(len(text), match.end() + 240)]
        normalized = fragment.casefold()
        if normalized not in seen:
            seen.add(normalized)
            out.append(fragment)
            if len(out) >= limit:
                break
    return out


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


def setup(cursor) -> None:
    cursor.execute(f"CREATE STAGE IF NOT EXISTS {STAGE}")
    cursor.execute(f"""CREATE TABLE IF NOT EXISTS {MANIFEST} (
        ACCESSION VARCHAR NOT NULL, CIK VARCHAR NOT NULL, TICKER VARCHAR NOT NULL,
        ISSUER VARCHAR, FORM VARCHAR NOT NULL, FILED_DATE DATE, ACCEPTANCE_UTC TIMESTAMP_TZ,
        AVAILABLE_AT TIMESTAMP_TZ, FILING_INDEX_URL VARCHAR NOT NULL, PACKAGE_STAGE_PATH VARCHAR NOT NULL,
        PACKAGE_SHA256 VARCHAR NOT NULL, PACKAGE_SIZE_BYTES NUMBER(38,0) NOT NULL,
        DOCUMENT_COUNT NUMBER(38,0) NOT NULL, DOCUMENTS_JSON VARCHAR NOT NULL,
        RETRIEVED_AT TIMESTAMP_TZ NOT NULL, LICENSE_STATUS VARCHAR NOT NULL,
        PRIMARY KEY (ACCESSION, PACKAGE_SHA256))""")
    cursor.execute(f"""CREATE TABLE IF NOT EXISTS {DOCS} (
        ACCESSION VARCHAR NOT NULL, CIK VARCHAR NOT NULL, TICKER VARCHAR NOT NULL, ISSUER VARCHAR,
        FORM VARCHAR NOT NULL, FILED_DATE DATE, ACCEPTANCE_UTC TIMESTAMP_TZ, AVAILABLE_AT TIMESTAMP_TZ,
        DOCUMENT_NAME VARCHAR NOT NULL, DOCUMENT_TYPE VARCHAR, DOCUMENT_URL VARCHAR NOT NULL,
        DOCUMENT_SHA256 VARCHAR NOT NULL, DOCUMENT_SIZE_BYTES NUMBER(38,0) NOT NULL,
        PACKAGE_STAGE_PATH VARCHAR NOT NULL, PACKAGE_SHA256 VARCHAR NOT NULL,
        MATCHED_TEXT_CONTEXTS VARCHAR, RETRIEVED_AT TIMESTAMP_TZ NOT NULL,
        PRIMARY KEY (ACCESSION, DOCUMENT_NAME, PACKAGE_SHA256))""")


def _get(session: requests.Session, url: str, delay: float = 0.25) -> requests.Response:
    last = None
    for attempt in range(6):
        try:
            response = session.get(url, timeout=60)
            if response.status_code == 200:
                time.sleep(delay)
                return response
            if response.status_code not in (403, 429, 500, 502, 503, 504):
                response.raise_for_status()
            last = requests.HTTPError(f"SEC returned {response.status_code} for {url}")
        except requests.RequestException as exc:
            last = exc
        time.sleep(min(2 ** attempt, 30))
    raise last or RuntimeError(f"could not retrieve SEC URL {url}")


def filing_rows() -> list[dict[str, str]]:
    path = ROOT / "results" / "filings-register.csv"
    with path.open(newline="", encoding="utf-8-sig") as stream:
        candidates = [row for row in csv.DictReader(stream)
                      if row.get("ticker", "").upper() in {"PWR", "ETN", "EME", "DLR"}
                      and row.get("form", "").upper().removesuffix("/A") in {"8-K", "10-K", "10-Q"}
                      and row.get("filed_date", "") >= "2016-01-01"]
    # Some registers contain multiple candidate rows for one accession; one original package suffices.
    unique: dict[str, dict[str, str]] = {}
    for row in candidates:
        unique.setdefault(row["accession"], row)
    return sorted(unique.values(), key=lambda row: (row["filed_date"], row["accession"]))


def save_and_upload(row: dict[str, str], issuer: str, session: requests.Session,
                    retrieved_at: str, dry_run: bool = False) -> tuple[list[dict], dict]:
    cik, accession = row["cik"].zfill(10), row["accession"]
    compact = accession.replace("-", "")
    index_url = f"{ARCHIVE_ROOT}/{int(cik)}/{compact}/index.json"
    index = _get(session, index_url).json()
    items = index.get("directory", {}).get("item", [])
    accession_dir = ROOT / "results" / "sec-packages" / compact
    accession_dir.mkdir(parents=True, exist_ok=True)
    package = accession_dir / f"{compact}.zip"
    details, hashes = [], []
    with ZipFile(package, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        archive.writestr("index.json", json.dumps(index, sort_keys=True, ensure_ascii=False))
        for item in items:
            name = item.get("name", "")
            # Directory records are absent in index.json, but reject unsafe paths defensively.
            if not name or "/" in name or "\\" in name or name in {".", ".."}:
                continue
            url = urljoin(index_url.rsplit("/", 1)[0] + "/", name)
            response = _get(session, url)
            content = response.content
            digest = hashlib.sha256(content).hexdigest()
            archive.writestr(f"documents/{name}", content)
            hashes.append(digest)
            info = {"name": name, "type": item.get("type", ""), "size_bytes": len(content),
                    "url": url, "sha256": digest}
            details.append(info)
            if name.lower().endswith((".htm", ".html", ".txt", ".xml")):
                contexts_for_doc = contexts(content)
            else:
                contexts_for_doc = []
            details[-1]["matched_text_contexts"] = contexts_for_doc
    package_hash = hashlib.sha256(package.read_bytes()).hexdigest()
    package_stage = f"@{STAGE}/accession={compact}/{package.name}"
    manifest = {
        "accession": accession, "cik": cik, "ticker": row["ticker"], "issuer": issuer,
        "form": row["form"], "filed_date": row["filed_date"],
        "acceptance_utc": row.get("acceptance_utc", ""),
        "available_at": row.get("earliest_availability_utc", ""), "filing_index_url": index_url,
        "package_stage_path": package_stage, "package_sha256": package_hash,
        "package_size_bytes": package.stat().st_size, "document_count": len(details),
        "documents": details, "retrieved_at": retrieved_at,
        "license": "public SEC EDGAR filing and exhibits; preserve SEC attribution",
    }
    if dry_run:
        package.unlink(missing_ok=True)
        return details, manifest

    with snowflake_connection() as connection:
        with connection.cursor() as cursor:
            setup(cursor)
            uri = package.resolve().as_uri().replace("'", "''")
            cursor.execute(f"PUT '{uri}' @{STAGE}/accession={compact} AUTO_COMPRESS=FALSE OVERWRITE=TRUE")
            result = cursor.fetchone()
            if result and len(result) > 6 and str(result[6]).upper() not in {"UPLOADED", "SKIPPED"}:
                raise RuntimeError(f"Snowflake stage upload failed for accession {accession}")
            cursor.execute(f"""MERGE INTO {MANIFEST} t USING
                (SELECT %s ACCESSION,%s CIK,%s TICKER,%s ISSUER,%s FORM,%s FILED_DATE,
                 %s ACCEPTANCE_UTC,%s AVAILABLE_AT,%s FILING_INDEX_URL,%s PACKAGE_STAGE_PATH,
                 %s PACKAGE_SHA256,%s PACKAGE_SIZE_BYTES,%s DOCUMENT_COUNT,%s DOCUMENTS_JSON,
                 %s RETRIEVED_AT,%s LICENSE_STATUS) s
                ON t.ACCESSION=s.ACCESSION AND t.PACKAGE_SHA256=s.PACKAGE_SHA256
                WHEN MATCHED THEN UPDATE SET RETRIEVED_AT=s.RETRIEVED_AT
                WHEN NOT MATCHED THEN INSERT (ACCESSION,CIK,TICKER,ISSUER,FORM,FILED_DATE,
                 ACCEPTANCE_UTC,AVAILABLE_AT,FILING_INDEX_URL,PACKAGE_STAGE_PATH,PACKAGE_SHA256,
                 PACKAGE_SIZE_BYTES,DOCUMENT_COUNT,DOCUMENTS_JSON,RETRIEVED_AT,LICENSE_STATUS)
                 VALUES (s.ACCESSION,s.CIK,s.TICKER,s.ISSUER,s.FORM,s.FILED_DATE,s.ACCEPTANCE_UTC,
                 s.AVAILABLE_AT,s.FILING_INDEX_URL,s.PACKAGE_STAGE_PATH,s.PACKAGE_SHA256,
                 s.PACKAGE_SIZE_BYTES,s.DOCUMENT_COUNT,s.DOCUMENTS_JSON,s.RETRIEVED_AT,s.LICENSE_STATUS)""",
                (accession, cik, row["ticker"], issuer, row["form"], row["filed_date"],
                 row.get("acceptance_utc") or None, row.get("earliest_availability_utc") or None,
                 index_url, package_stage, package_hash, package.stat().st_size, len(details),
                 json.dumps(details, ensure_ascii=False), retrieved_at, manifest["license"]))
            doc_values = []
            for item in details:
                doc_values.append((accession, cik, row["ticker"], issuer, row["form"], row["filed_date"],
                    row.get("acceptance_utc") or None, row.get("earliest_availability_utc") or None,
                    item["name"], item["type"], item["url"], item["sha256"], item["size_bytes"],
                    package_stage, package_hash, json.dumps(item["matched_text_contexts"], ensure_ascii=False), retrieved_at))
            cursor.execute("""CREATE TEMPORARY TABLE GQH_SEC_DOC_LOAD_STAGE (
                ACCESSION VARCHAR,CIK VARCHAR,TICKER VARCHAR,ISSUER VARCHAR,FORM VARCHAR,FILED_DATE DATE,
                ACCEPTANCE_UTC TIMESTAMP_TZ,AVAILABLE_AT TIMESTAMP_TZ,DOCUMENT_NAME VARCHAR,
                DOCUMENT_TYPE VARCHAR,DOCUMENT_URL VARCHAR,DOCUMENT_SHA256 VARCHAR,
                DOCUMENT_SIZE_BYTES NUMBER(38,0),PACKAGE_STAGE_PATH VARCHAR,PACKAGE_SHA256 VARCHAR,
                MATCHED_TEXT_CONTEXTS VARCHAR,RETRIEVED_AT TIMESTAMP_TZ)""")
            cursor.executemany("INSERT INTO GQH_SEC_DOC_LOAD_STAGE VALUES (" + ",".join(["%s"] * 17) + ")", doc_values)
            cursor.execute(f"""MERGE INTO {DOCS} t USING GQH_SEC_DOC_LOAD_STAGE s
                ON t.ACCESSION=s.ACCESSION AND t.DOCUMENT_NAME=s.DOCUMENT_NAME AND t.PACKAGE_SHA256=s.PACKAGE_SHA256
                WHEN NOT MATCHED THEN INSERT (ACCESSION,CIK,TICKER,ISSUER,FORM,FILED_DATE,
                 ACCEPTANCE_UTC,AVAILABLE_AT,DOCUMENT_NAME,DOCUMENT_TYPE,DOCUMENT_URL,DOCUMENT_SHA256,
                 DOCUMENT_SIZE_BYTES,PACKAGE_STAGE_PATH,PACKAGE_SHA256,MATCHED_TEXT_CONTEXTS,RETRIEVED_AT)
                 VALUES (s.ACCESSION,s.CIK,s.TICKER,s.ISSUER,s.FORM,s.FILED_DATE,s.ACCEPTANCE_UTC,
                 s.AVAILABLE_AT,s.DOCUMENT_NAME,s.DOCUMENT_TYPE,s.DOCUMENT_URL,s.DOCUMENT_SHA256,
                 s.DOCUMENT_SIZE_BYTES,s.PACKAGE_STAGE_PATH,s.PACKAGE_SHA256,s.MATCHED_TEXT_CONTEXTS,s.RETRIEVED_AT)""")
        connection.commit()
    return details, manifest


def main() -> int:
    sync.load_local_env()
    user_agent = os.getenv("EDGAR_USER_AGENT", "")
    if "@" not in user_agent or "example.com" in user_agent:
        raise SystemExit("Set EDGAR_USER_AGENT to a truthful project name and contact email in the private .env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-date", default="2016-01-01")
    parser.add_argument("--to-date", default="2026-10-03")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    rows = [row for row in filing_rows() if args.from_date <= row["filed_date"] <= args.to_date]
    if args.limit:
        rows = rows[:args.limit]
    if not rows:
        raise SystemExit("No matching accession-register rows")
    session = requests.Session()
    session.headers.update({"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"})
    # CIK -> issuer map only labels the filing; CIK and accession remain the primary keys.
    issuers = {"1050915": "Quanta Services, Inc.", "1551182": "Eaton Corporation plc",
               "105634": "EMCOR Group, Inc.", "1297996": "Digital Realty Trust, Inc."}
    for row in rows:
        ticker = row["ticker"].upper()
        cik = str(int(row["cik"]))
        row["ticker"] = ticker
        retrieved = datetime.now(timezone.utc).isoformat()
        detail, manifest = save_and_upload(row, issuers.get(cik, ticker), session, retrieved, args.dry_run)
        print(f"SEC {row['accession']}: docs={len(detail)} package_sha256={manifest['package_sha256']} "
              f"bytes={manifest['package_size_bytes']}", flush=True)
    print(f"completed SEC packages={len(rows)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
