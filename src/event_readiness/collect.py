"""Optional read-only Snowflake metadata snapshot. No provider fetch, DDL, PUT, DELETE or MERGE."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json

from .archive import ACCESSION, STAGE

# Static statements deliberately avoid payload/price/label columns. The inventory includes date
# coverage only, even for the sealed window: no observations or returns are retrieved.
QUERIES = {
    "source_inventory": """SELECT SOURCE_ID, BATCH_SHA256, COUNT(*) ROW_COUNT,
        COUNT(DISTINCT ROW_INDEX) DISTINCT_ROW_INDEX_COUNT,
        MIN(EVENT_TIME_TEXT) FIRST_EVENT, MAX(EVENT_TIME_TEXT) LAST_EVENT
        FROM VECTOR_RESEARCH.RAW.SOURCE_RECORDS GROUP BY SOURCE_ID, BATCH_SHA256""",
    "source_manifests": """SELECT SOURCE_ID, BATCH_SHA256, ROW_COUNT, RETRIEVED_AT
        FROM VECTOR_RESEARCH.RAW.INGESTION_MANIFESTS""",
    "eia_manifests": """SELECT VINTAGE_MONTH, SOURCE_FILE_SHA256, PLANNED_ROWS, OPERATING_ROWS, CANCELED_ROWS, RETRIEVED_AT
        FROM VECTOR_RESEARCH.RAW.EIA860M_FILE_MANIFESTS""",
}


def rows(cursor, sql: str, params=None) -> list[dict]:
    cursor.execute(sql, params) if params is not None else cursor.execute(sql)
    names = [str(column[0]).lower() for column in cursor.description]
    def scalar(value):
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Decimal):
            return int(value) if value == int(value) else str(value)
        return value
    return [{name: scalar(value) for name, value in zip(names, row)} for row in cursor.fetchall()]


def collect(connection, accessions: list[str]) -> dict:
    if not accessions or not all(ACCESSION.fullmatch(a) for a in accessions):
        raise ValueError("invalid selection")
    accessions = sorted(set(accessions))
    placeholders = ",".join(["%s"] * len(accessions))
    result = {"schema_version": 1, "started_at_utc": datetime.now(timezone.utc).isoformat(),
              "query_receipts": [], "query_failures": [], "expected_accessions": accessions}
    with connection.cursor() as cursor:
        selected = {
            "manifests": f"""SELECT ACCESSION, PACKAGE_SHA256, PACKAGE_STAGE_PATH,
                PACKAGE_SIZE_BYTES, DOCUMENT_COUNT, DOCUMENTS_JSON, TICKER, RETRIEVED_AT
                FROM VECTOR_RESEARCH.RAW.SEC_FILING_PACKAGE_MANIFESTS
                WHERE ACCESSION IN ({placeholders})""",
            "documents": f"""SELECT ACCESSION, PACKAGE_SHA256, PACKAGE_STAGE_PATH,
                DOCUMENT_NAME, DOCUMENT_SHA256, DOCUMENT_SIZE_BYTES
                FROM VECTOR_RESEARCH.RAW.SEC_FILING_DOCUMENTS WHERE ACCESSION IN ({placeholders})""",
        }
        for name, sql in selected.items():
            result[name] = rows(cursor, sql, accessions)
            result["query_receipts"].append({"name": name, "query_id": cursor.sfqid})
        for manifest in result["manifests"]:
            raw = json.loads(manifest.pop("documents_json"))
            manifest["documents"] = [{k: d[k] for k in ("name", "sha256", "size_bytes")} for d in raw]
        result["stage_objects"] = rows(cursor, f"LIST @{STAGE}")
        result["query_receipts"].append({"name": "stage_objects", "query_id": cursor.sfqid})
        for name, sql in QUERIES.items():
            try:
                result[name] = rows(cursor, sql)
                result["query_receipts"].append({"name": name, "query_id": cursor.sfqid})
            except Exception as exc:
                # Missing table/role is an explicit incomplete inventory, never an empty success.
                result[name] = None
                result["query_failures"].append({"name": name, "error_type": type(exc).__name__})
    result["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    result["inventory_complete"] = not result["query_failures"]
    return result


def reconcile_sources(snapshot: dict) -> dict:
    inventories = snapshot.get("source_inventory")
    manifests = snapshot.get("source_manifests")
    if inventories is None or manifests is None:
        return {"counts_reconciled": False, "issues": ["source_inventory_unavailable"]}
    issues = []
    observed = {}
    expected = {}
    for label, records, target in (("inventory", inventories, observed), ("manifest", manifests, expected)):
        for record in records:
            key = (record["source_id"], record["batch_sha256"])
            if key in target:
                issues.append({"code": "duplicate_" + label, "source_id": key[0], "batch_sha256": key[1]})
            target[key] = record
    for key in sorted(observed.keys() | expected.keys()):
        source_id, sha = key
        code = None
        if key not in observed or key not in expected:
            code = "missing_batch_or_manifest"
        elif int(observed[key]["row_count"]) != int(expected[key]["row_count"]):
            code = "row_count_mismatch"
        elif int(observed[key]["row_count"]) != int(observed[key]["distinct_row_index_count"]):
            code = "duplicate_row_index"
        if code:
            issues.append({"code": code, "source_id": source_id, "batch_sha256": sha})
    return {"counts_reconciled": not issues and bool(observed), "batch_count": len(observed),
            "issues": issues, "limitation": "Counts only; payload/row hashes, rights and point-in-time availability are not verified."}
