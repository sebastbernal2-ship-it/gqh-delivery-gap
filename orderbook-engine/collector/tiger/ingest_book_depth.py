#!/usr/bin/env python3
"""Load Tardis book-depth metrics into the Tiger observations table.

The Tardis book-depth CSV reports, for each timestamp, a cumulative depth and
notional at each percentage distance from the mid price. Each CSV row becomes
one observation with data_type book-depth, and the file itself becomes one
source_manifests row keyed by its SHA-256.

Writes need a session that is not read-only. Use read_only=prod so PROD
services stay protected while DEV stays writable, and restore read_only=all
after the load.

The load is idempotent: rows from the same file hash and data type are deleted
before insert, and the printed rollback statement removes exactly those rows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

DATA_TYPE = "book-depth"
SOURCE_KIND = "tardis-book-depth-metrics"
MANIFEST_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "quanthacks.market_simulator")
BATCH_ROWS = 200


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_timestamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S.%f+00")


def decimal_text(value: str, field: str) -> str:
    text = value.strip()
    if text == "" or text[0] == "-":
        raise ValueError(f"{field} must be an unsigned decimal")
    digits = text.replace(".", "", 1)
    if not digits.isdigit():
        raise ValueError(f"{field} is not a decimal number")
    return text


def read_rows(path: Path, symbol: str):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines:
        raise ValueError("book-depth file is empty")
    header = lines[0].split(",")
    if header != ["timestamp", "percentage", "depth", "notional"]:
        raise ValueError("unexpected book-depth header")
    rows = []
    for number, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        fields = line.split(",")
        if len(fields) != 4:
            raise ValueError(f"line {number}: expected 4 columns")
        observed_at = parse_timestamp(fields[0])
        try:
            percentage = int(fields[1])
        except ValueError as error:
            raise ValueError(f"line {number}: invalid percentage") from error
        payload = {
            "percentage": percentage,
            "depth": decimal_text(fields[2], "depth"),
            "notional": decimal_text(fields[3], "notional"),
        }
        rows.append(
            {
                "observed_at": observed_at,
                "symbol": symbol,
                "payload": payload,
            }
        )
    return rows


def select_rows(rows, start: datetime | None, end: datetime | None, limit: int | None):
    selected = [
        row
        for row in rows
        if (start is None or row["observed_at"] >= start)
        and (end is None or row["observed_at"] < end)
    ]
    if limit is not None:
        selected = selected[:limit]
    return selected


def manifest_id(source_uri: str, sha256: str) -> str:
    return str(uuid.uuid5(MANIFEST_NAMESPACE, f"{source_uri}:{sha256}"))


def build_sql(rows, symbol: str, source_uri: str, sha256: str) -> str:
    statements = [
        "DELETE FROM observations WHERE source_sha256 = "
        f"{sql_quote(sha256)} AND data_type = {sql_quote(DATA_TYPE)};"
    ]
    for offset in range(0, len(rows), BATCH_ROWS):
        batch = rows[offset : offset + BATCH_ROWS]
        values = []
        for row in batch:
            payload = json.dumps(row["payload"], separators=(",", ":"))
            values.append(
                "("
                + ", ".join(
                    [
                        sql_quote(sql_timestamp(row["observed_at"])) + "::timestamptz",
                        sql_quote(DATA_TYPE),
                        sql_quote(source_uri),
                        sql_quote(symbol),
                        sql_quote(payload) + "::jsonb",
                        sql_quote(sha256),
                    ]
                )
                + ")"
            )
        statements.append(
            "INSERT INTO observations "
            "(observed_at, data_type, source, symbol, payload, source_sha256) VALUES\n"
            + ",\n".join(values)
            + ";"
        )
    first = min(row["observed_at"] for row in rows)
    last = max(row["observed_at"] for row in rows)
    metadata = json.dumps(
        {
            "rows": len(rows),
            "first_observed_at": sql_timestamp(first),
            "last_observed_at": sql_timestamp(last),
            "data_type": DATA_TYPE,
            "symbol": symbol,
        },
        separators=(",", ":"),
    )
    statements.append(
        "INSERT INTO source_manifests "
        "(source_id, source_kind, source_uri, sha256, captured_at, metadata) VALUES ("
        + ", ".join(
            [
                sql_quote(manifest_id(source_uri, sha256)) + "::uuid",
                sql_quote(SOURCE_KIND),
                sql_quote(source_uri),
                sql_quote(sha256),
                "NULL",
                sql_quote(metadata) + "::jsonb",
            ]
        )
        + ") ON CONFLICT (source_id) DO UPDATE SET metadata = EXCLUDED.metadata;"
    )
    return "\n".join(statements)


def rollback_sql(source_uri: str, sha256: str) -> str:
    return (
        "DELETE FROM observations WHERE source_sha256 = "
        f"{sql_quote(sha256)} AND data_type = {sql_quote(DATA_TYPE)};\n"
        "DELETE FROM source_manifests WHERE source_id = "
        f"{sql_quote(manifest_id(source_uri, sha256))}::uuid;"
    )


def run_tiger(tiger: str, service: str | None, sql: str) -> None:
    command = [tiger]
    if service:
        command += ["--service-id", service]
    command += ["db", "query"]
    completed = subprocess.run(
        command, input=sql, text=True, capture_output=True, check=False
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--service")
    parser.add_argument("--tiger", default="tiger")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        sha256 = hashlib.sha256(args.csv.read_bytes()).hexdigest()
        source_uri = f"file:{args.csv.resolve()}"
        rows = read_rows(args.csv, args.symbol)
        start = parse_timestamp(args.start) if args.start else None
        end = parse_timestamp(args.end) if args.end else None
        rows = select_rows(rows, start, end, args.limit)
        if not rows:
            raise ValueError("no rows selected")
        sql = build_sql(rows, args.symbol, source_uri, sha256)
        print(
            f"rows={len(rows)} statements={sql.count(';')} bytes={len(sql)} "
            f"sha256={sha256} manifest={manifest_id(source_uri, sha256)}"
        )
        if args.dry_run:
            print(sql[:2000])
            return 0
        run_tiger(args.tiger, args.service, sql)
        print(f"loaded {len(rows)} {DATA_TYPE} observations")
        print("rollback:")
        print(rollback_sql(source_uri, sha256))
    except (OSError, ValueError, RuntimeError) as error:
        print(f"book-depth ingest failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
