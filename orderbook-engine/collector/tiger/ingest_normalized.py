#!/usr/bin/env python3
"""Load normalized capture rows into the Tiger depth and trade tables.

Input is the JSONL that collector/normalize_capture.py and
collector/normalize_trades.py produce. Each row keeps its raw-file SHA-256 as
provenance, and the load is idempotent: rows from the same source hash are
deleted before insert, and the exact rollback statement is printed.

Writes need a session that is not read-only. Use read_only=prod so PROD
services stay protected while DEV stays writable, and restore read_only=all
after the load.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from ingest_book_depth import (
    manifest_id,
    run_tiger,
    sql_quote,
    sql_timestamp,
)

KIND_TABLES = {"depth": "depth_events", "trades": "trade_events"}
SOURCE_KINDS = {
    "depth": "binance-futures-depth",
    "trades": "binance-futures-trades",
}
BATCH_ROWS = 200


TIME_RE = re.compile(
    r"^(?P<year>\d{4})[.\-](?P<month>\d{2})[.\-](?P<day>\d{2})"
    r"[DT](?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})"
    r"(?:\.(?P<fraction>\d{1,9}))?"
    r"(?P<offset>Z|[+-]\d{2}:?\d{2})?$"
)


def parse_time(value: object) -> datetime:
    text = str(value).strip()
    match = TIME_RE.match(text)
    if match is None:
        raise ValueError(f"invalid timestamp: {text}")
    fraction = (match.group("fraction") or "").ljust(6, "0")[:6]
    parsed = datetime(
        int(match.group("year")),
        int(match.group("month")),
        int(match.group("day")),
        int(match.group("hour")),
        int(match.group("minute")),
        int(match.group("second")),
        int(fraction or "0"),
        tzinfo=timezone.utc,
    )
    return parsed.astimezone(timezone.utc)


def read_rows(path: Path, kind: str):
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"line {number}: invalid JSON") from error
        if not isinstance(row, dict):
            raise ValueError(f"line {number}: row is not an object")
        for name in ("received_time", "source_path", "source_sha256", "symbol"):
            if not row.get(name):
                raise ValueError(f"line {number}: missing {name}")
        if kind == "trades":
            for name in ("trade_time_ms", "trade_id", "price", "quantity"):
                if row.get(name) is None:
                    raise ValueError(f"line {number}: missing {name}")
        else:
            for name in ("kind", "segment", "event_time_ms", "bids", "asks", "applied"):
                if row.get(name) is None:
                    raise ValueError(f"line {number}: missing {name}")
        rows.append(row)
    return rows


def event_key(row: dict, kind: str) -> str:
    if kind == "trades":
        return f"trade:{row['trade_id']}"
    identifier = row.get("final_update_id")
    if identifier is None:
        identifier = row.get("last_update_id")
    return f"{row['kind']}:{row['segment']}:{identifier}"


def row_values(row: dict, kind: str) -> str:
    received = sql_quote(sql_timestamp(parse_time(row["received_time"]))) + "::timestamptz"
    key = sql_quote(event_key(row, kind))
    if kind == "trades":
        return (
            "("
            + ", ".join(
                [
                    key,
                    received,
                    str(int(row["trade_time_ms"])),
                    sql_quote(str(row["symbol"])),
                    sql_quote(str(row["trade_id"])),
                    sql_quote(str(row["price"])) + "::numeric",
                    sql_quote(str(row["quantity"])) + "::numeric",
                    "TRUE" if row.get("buyer_is_maker") else "FALSE",
                    sql_quote(str(row["source_path"])),
                    sql_quote(str(row["source_sha256"])),
                ]
            )
            + ")"
        )
    return (
        "("
        + ", ".join(
            [
                key,
                received,
                str(int(row["event_time_ms"])),
                sql_quote(str(row["symbol"])),
                str(int(row["segment"])),
                sql_quote(str(row["kind"])),
                "TRUE" if row["applied"] else "FALSE",
                "NULL"
                if row.get("last_update_id") is None
                else str(int(row["last_update_id"])),
                "NULL"
                if row.get("first_update_id") is None
                else str(int(row["first_update_id"])),
                "NULL"
                if row.get("final_update_id") is None
                else str(int(row["final_update_id"])),
                "NULL"
                if row.get("previous_update_id") is None
                else str(int(row["previous_update_id"])),
                sql_quote(json.dumps(row["bids"], separators=(",", ":"))) + "::jsonb",
                sql_quote(json.dumps(row["asks"], separators=(",", ":"))) + "::jsonb",
                sql_quote(str(row["source_path"])),
                sql_quote(str(row["source_sha256"])),
            ]
        )
        + ")"
    )


DEPTH_COLUMNS = (
    "(event_key, received_time, event_time_ms, symbol, segment, kind, applied, "
    "last_update_id, first_update_id, final_update_id, previous_update_id, "
    "bids, asks, source_path, source_sha256)"
)
TRADE_COLUMNS = (
    "(event_key, received_time, trade_time_ms, symbol, trade_id, price, "
    "quantity, buyer_is_maker, source_path, source_sha256)"
)


def build_sql(rows, kind: str, source_uri: str) -> str:
    table = KIND_TABLES[kind]
    columns = TRADE_COLUMNS if kind == "trades" else DEPTH_COLUMNS
    hashes = sorted({str(row["source_sha256"]) for row in rows})
    statements = [
        f"DELETE FROM {table} WHERE source_sha256 = {sql_quote(sha256)};"
        for sha256 in hashes
    ]
    for offset in range(0, len(rows), BATCH_ROWS):
        batch = rows[offset : offset + BATCH_ROWS]
        values = ",\n".join(row_values(row, kind) for row in batch)
        statements.append(f"INSERT INTO {table} {columns} VALUES\n{values};")
    for sha256 in hashes:
        rows_for_hash = [row for row in rows if str(row["source_sha256"]) == sha256]
        source_path = sorted({str(row["source_path"]) for row in rows_for_hash})[0]
        metadata = json.dumps(
            {
                "rows": len(rows_for_hash),
                "kind": kind,
                "symbol": str(rows_for_hash[0]["symbol"]),
                "source_path": source_path,
                "first_received_time": sql_timestamp(
                    min(parse_time(row["received_time"]) for row in rows_for_hash)
                ),
                "last_received_time": sql_timestamp(
                    max(parse_time(row["received_time"]) for row in rows_for_hash)
                ),
            },
            separators=(",", ":"),
        )
        statements.append(
            "INSERT INTO source_manifests "
            "(source_id, source_kind, source_uri, sha256, captured_at, metadata) VALUES ("
            + ", ".join(
                [
                    sql_quote(manifest_id(source_path, sha256)) + "::uuid",
                    sql_quote(SOURCE_KINDS[kind]),
                    sql_quote(source_path),
                    sql_quote(sha256),
                    "NULL",
                    sql_quote(metadata) + "::jsonb",
                ]
            )
            + ") ON CONFLICT (source_id) DO UPDATE SET metadata = EXCLUDED.metadata;"
        )
    return "\n".join(statements)


def rollback_sql(rows, kind: str) -> str:
    table = KIND_TABLES[kind]
    hashes = sorted({str(row["source_sha256"]) for row in rows})
    statements = [
        f"DELETE FROM {table} WHERE source_sha256 = {sql_quote(sha256)};"
        for sha256 in hashes
    ]
    for sha256 in hashes:
        source_path = sorted(
            {str(row["source_path"]) for row in rows if str(row["source_sha256"]) == sha256}
        )[0]
        statements.append(
            "DELETE FROM source_manifests WHERE source_id = "
            f"{sql_quote(manifest_id(source_path, sha256))}::uuid;"
        )
    return "\n".join(statements)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", type=Path)
    parser.add_argument("--kind", choices=sorted(KIND_TABLES), required=True)
    parser.add_argument("--service")
    parser.add_argument("--tiger", default="tiger")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        rows = read_rows(args.jsonl, args.kind)
        if not rows:
            raise ValueError("no rows to load")
        source_uri = str(args.jsonl)
        sql = build_sql(rows, args.kind, source_uri)
        print(
            f"rows={len(rows)} kind={args.kind} statements={sql.count(';')} "
            f"bytes={len(sql)}"
        )
        if args.dry_run:
            print(sql[:1500])
            return 0
        run_tiger(args.tiger, args.service, sql)
        print(f"loaded {len(rows)} {KIND_TABLES[args.kind]} rows")
        print("rollback:")
        print(rollback_sql(rows, args.kind))
    except (OSError, ValueError, RuntimeError) as error:
        print(f"normalized ingest failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
