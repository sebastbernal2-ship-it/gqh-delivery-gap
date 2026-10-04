"""Verify retained acquisitions, then publish additive, content-addressed Snowflake batches.

One writer per dataset. No changes to the existing SOURCE_RECORDS or feature tables.
Completion certifies byte/row reconciliation, not point-in-time research suitability.
"""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import logging
import os
from pathlib import Path
import re
import tempfile
import zipfile

from .acquisition import atomic_json, canonical, sha, strict_json

PREFIX = "VECTOR_RESEARCH.RAW.RESEARCH_ACQUISITION"
STAGE = PREFIX + "_STAGE"
HASH = re.compile(r"[0-9a-f]{64}\Z")


def valid_hash(value):
    if not isinstance(value, str) or not HASH.fullmatch(value):
        raise ValueError("invalid content hash")
    return value


def prepare(root):
    """No network. Reject corruption or missing provenance before any warehouse mutation."""
    root = Path(root)
    manifest = strict_json((root / "complete.json").read_bytes())
    valid_hash(manifest["sha256"])
    records = root / "records.jsonl"
    if manifest["file"] != records.name or sha(records.read_bytes()) != manifest["sha256"]:
        raise ValueError("normalized file checksum mismatch")
    receipts = {}
    files = [root / "complete.json", records]
    if (root / "plan.json").exists():
        files.append(root / "plan.json")
    for path in sorted((root / "requests").glob("*.json")):
        receipt = strict_json(path.read_bytes())
        digest = valid_hash(receipt["sha256"])
        obj = root / "objects" / digest
        if obj.is_symlink() or not obj.is_file():
            raise ValueError("missing retained source object")
        data = obj.read_bytes()
        if sha(data) != digest or len(data) != receipt["size_bytes"] or receipt["http_status"] != 200:
            raise ValueError("source receipt integrity failure")
        receipts[(digest, receipt["url"])] = receipt
        files.extend([obj, path])
    if not receipts:
        raise ValueError("no source receipts")
    output = root / "warehouse"
    output.mkdir(exist_ok=True)
    ndjson = output / "rows.jsonl.gz"
    digest = hashlib.sha256()
    count = 0
    with ndjson.open("wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as packed:
        with records.open("rb") as source:
            for count, line in enumerate(source, 1):
                row = strict_json(line)
                if (row.get("source_sha256"), row.get("source_url")) not in receipts:
                    raise ValueError("row has no matching retained source receipt")
                payload = line.decode("utf-8").rstrip("\n")
                if line != (canonical(row) + "\n").encode():
                    raise ValueError("records must use canonical JSONL encoding")
                digest.update(line)
                packed.write((canonical({"row_index": count - 1, "row_sha256": sha(payload.encode()),
                                         "payload_json": payload}) + "\n").encode())
    if count != manifest["rows"] or count == 0 or digest.hexdigest() != manifest["sha256"]:
        raise ValueError("normalized row count or checksum mismatch")
    ndjson_hash = sha(ndjson.read_bytes())
    immutable_json = output / (ndjson_hash + ".jsonl.gz")
    ndjson.replace(immutable_json)
    bundle = output / "source.zip"
    with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(set(files), key=lambda p: p.relative_to(root).as_posix()):
            name = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    bundle_hash = sha(bundle.read_bytes())
    immutable_zip = output / (bundle_hash + ".zip")
    bundle.replace(immutable_zip)
    # Bundle identity also binds receipts, request scope, and transformation manifest.
    result = {"run_id": bundle_hash, "dataset_name": root.name, "rows": count,
              "records_sha256": manifest["sha256"], "bundle_sha256": bundle_hash,
              "transport_sha256": ndjson_hash, "source_receipts": len(receipts),
              "strategy_ready": False, "manifest": manifest}
    atomic_json(output / "prepared.json", result)
    return result, immutable_zip, immutable_json


def verify_rows(cursor, table, run_id, expected):
    # Fixed table names only. Bound run values never enter SQL syntax.
    if table not in {PREFIX + "_ROWS", "ACQUISITION_COPY"}:
        raise ValueError("invalid reconciliation table")
    where, params = (" WHERE RUN_ID=%s", (run_id,)) if table != "ACQUISITION_COPY" else ("", ())
    cursor.execute(f"SELECT ROW_INDEX,ROW_SHA256,PAYLOAD_JSON FROM {table}{where} ORDER BY ROW_INDEX", params)
    digest, count = hashlib.sha256(), 0
    while True:
        rows = cursor.fetchmany(2000)
        if not rows:
            break
        for index, row_hash, payload in rows:
            if index != count or sha(payload.encode()) != row_hash:
                raise ValueError("warehouse row identity or checksum failure")
            digest.update((payload + "\n").encode())
            count += 1
    if count != expected["rows"] or digest.hexdigest() != expected["records_sha256"]:
        raise ValueError("warehouse batch checksum or count failure")


def sql_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def publish(root, connection):
    prepared, bundle, transport = prepare(root)
    run = prepared["run_id"]
    location = f"@{STAGE}/{run}"
    with connection.cursor() as cur:
        cur.execute(f"CREATE STAGE IF NOT EXISTS {STAGE}")
        cur.execute(f"""CREATE TABLE IF NOT EXISTS {PREFIX}_ROWS (
            RUN_ID VARCHAR NOT NULL, ROW_INDEX NUMBER NOT NULL, ROW_SHA256 VARCHAR NOT NULL,
            PAYLOAD_JSON VARCHAR NOT NULL)""")
        cur.execute(f"""CREATE TABLE IF NOT EXISTS {PREFIX}_RUNS (
            RUN_ID VARCHAR NOT NULL, DATASET_NAME VARCHAR NOT NULL, ROW_COUNT NUMBER NOT NULL,
            RECORDS_SHA256 VARCHAR NOT NULL, BUNDLE_SHA256 VARCHAR NOT NULL, STAGE_PREFIX VARCHAR NOT NULL,
            MANIFEST_JSON VARCHAR NOT NULL, VERIFIED_AT TIMESTAMP_TZ NOT NULL)""")
        # Content-hash filenames and OVERWRITE=FALSE avoid mutable source paths.
        for path in (bundle, transport):
            cur.execute(f"PUT {sql_literal('file://' + str(path.resolve()))} {location} AUTO_COMPRESS=FALSE OVERWRITE=FALSE")
            cur.fetchall()
        with tempfile.TemporaryDirectory(prefix="gqh-archive-verify-") as tmp:
            cur.execute(f"GET {location}/{bundle.name} {sql_literal('file://' + tmp + '/')} OVERWRITE=TRUE")
            cur.fetchall()
            if sha((Path(tmp) / bundle.name).read_bytes()) != prepared["bundle_sha256"]:
                raise ValueError("downloaded Snowflake archive checksum mismatch")
        cur.execute(f"SELECT COUNT(*) FROM {PREFIX}_RUNS WHERE RUN_ID=%s", (run,))
        existing = cur.fetchone()[0]
        if existing:
            if existing != 1:
                raise ValueError("duplicate warehouse manifests")
            verify_rows(cur, PREFIX + "_ROWS", run, prepared)
            outcome = "already_verified"
        else:
            cur.execute("""CREATE OR REPLACE TEMPORARY TABLE ACQUISITION_COPY (
                ROW_INDEX NUMBER, ROW_SHA256 VARCHAR, PAYLOAD_JSON VARCHAR)""")
            cur.execute(f"""COPY INTO ACQUISITION_COPY FROM (
                SELECT $1:row_index::NUMBER,$1:row_sha256::VARCHAR,$1:payload_json::VARCHAR
                FROM {location}/) FILES=({sql_literal(transport.name)})
                FILE_FORMAT=(TYPE=JSON COMPRESSION=GZIP) ON_ERROR=ABORT_STATEMENT FORCE=TRUE""")
            cur.fetchall()
            verify_rows(cur, "ACQUISITION_COPY", run, prepared)
            # DDL above is outside the transaction. Rows and completion manifest commit together.
            cur.execute("BEGIN")
            try:
                cur.execute(f"SELECT COUNT(*) FROM {PREFIX}_ROWS WHERE RUN_ID=%s", (run,))
                if cur.fetchone()[0] != 0:
                    raise ValueError("unmanifested rows exist; reconcile before retry")
                cur.execute(f"INSERT INTO {PREFIX}_ROWS SELECT %s,ROW_INDEX,ROW_SHA256,PAYLOAD_JSON FROM ACQUISITION_COPY", (run,))
                verify_rows(cur, PREFIX + "_ROWS", run, prepared)
                cur.execute(f"INSERT INTO {PREFIX}_RUNS VALUES (%s,%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP())",
                            (run, prepared["dataset_name"], prepared["rows"], prepared["records_sha256"],
                             prepared["bundle_sha256"], location, canonical(prepared["manifest"])))
                cur.execute("COMMIT")
            except Exception:
                cur.execute("ROLLBACK")
                raise
            outcome = "published_verified"
    result = {**prepared, "status": outcome, "stage_prefix": location,
              "verified_at_utc": datetime.now(timezone.utc).isoformat()}
    atomic_json(Path(root) / "warehouse" / "published.json", result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("--publish", action="store_true", help="Write the additive Snowflake acquisition tables")
    args = p.parse_args()
    if not args.publish:
        result, _, _ = prepare(args.root)
    else:
        import snowflake.connector
        logging.getLogger("snowflake").setLevel(logging.ERROR)
        with snowflake.connector.connect(account=os.environ["SNOWFLAKE_ACCOUNT"],
            user=os.environ["SNOWFLAKE_USER"], password=os.environ["SNOWFLAKE_PASSWORD"],
            warehouse=os.environ["SNOWFLAKE_WAREHOUSE"], role=os.environ["SNOWFLAKE_ROLE"],
            database="VECTOR_RESEARCH", schema="RAW", login_timeout=30, network_timeout=120,
            session_parameters={"STATEMENT_TIMEOUT_IN_SECONDS": 300, "QUERY_TAG": "gqh-candidate-acquisition-v1"}) as conn:
            result = publish(args.root, conn)
    print(canonical({k: result[k] for k in ("run_id", "dataset_name", "rows", "records_sha256")}), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Provider/connector exceptions can contain credential-bearing request details.
        print(canonical({"status": "incomplete", "error_type": type(exc).__name__,
                         "errno": getattr(exc, "errno", None)}), flush=True)
        raise SystemExit(1)
