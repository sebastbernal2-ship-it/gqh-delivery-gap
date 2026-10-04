#!/usr/bin/env python3
"""Export a bounded Tiger query as an OCaml fixture.

Two output formats:

- normalized: the legacy Binance normalized JSONL that Binance_l2 consumes.
- canonical: the Exec_event JSONL contract with integer ticks and units.

Canonical fixtures carry a manifest with the row count, time range, source
hashes, query version, and configuration hash, so a replay run is reproducible.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PRICE_TICKS = 10_000
QUANTITY_UNITS = 1_000_000
QUERY_VERSION = "quanthacks-fixture-v1"
DEFAULT_VENUE = "binance-futures"


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def received_text(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("received_time must be text")
    value = value.strip()
    if "." in value and "D" in value:
        date, clock = value.split("D", 1)
        return f"{date}D{clock.rstrip('Z')}"
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    parsed = parsed.astimezone(timezone.utc)
    return parsed.strftime("%Y.%m.%dD%H:%M:%S.%f") + "000"


def bool_field(value: object, field: str) -> bool:
    """Accept Python bools and the string forms a SQL client returns.

    A Postgres boolean arrives as "t" or "f" through some clients, and
    bool("f") is True, so the text forms must be mapped deliberately.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"t", "true", "1"}:
            return True
        if text in {"f", "false", "0", ""}:
            return False
    raise ValueError(f"{field} is not a boolean")


def levels(value: object, field: str) -> list[list[str]]:
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, list):
        raise ValueError(f"{field} must be an array")
    result = []
    for level in value:
        if not isinstance(level, list) or len(level) != 2:
            raise ValueError(f"{field} must contain price-size pairs")
        price, size = level
        result.append([str(price), str(size)])
    return result


def row_to_normalized(row: dict[str, object]) -> dict[str, object]:
    kind = str(row["kind"])
    if kind not in {"snapshot", "update"}:
        raise ValueError(f"invalid depth kind: {kind}")
    event_time_ms = int(row["event_time_ms"])
    if event_time_ms < 0:
        raise ValueError("event_time_ms must be nonnegative")
    normalized: dict[str, object] = {
        "kind": kind,
        "segment": int(row["segment"]),
        "symbol": str(row["symbol"]),
        "received_time": received_text(row["received_time"]),
        "event_time_ms": event_time_ms,
        "source_path": str(row["source_path"]),
        "source_sha256": str(row["source_sha256"]),
        "applied": bool(row["applied"]),
        "bids": levels(row["bids"], "bids"),
        "asks": levels(row["asks"], "asks"),
    }
    for name in (
        "last_update_id",
        "first_update_id",
        "final_update_id",
        "previous_update_id",
    ):
        value = row.get(name)
        normalized[name] = None if value is None else int(value)
    return normalized


# ---------------------------------------------------------------- canonical


def scaled_int(value: object, decimals: int, field: str) -> int:
    text = str(value).strip()
    if text == "" or text.startswith("-") or text.startswith("+"):
        raise ValueError(f"{field} must be an unsigned decimal")
    whole, point, fraction = text.partition(".")
    if whole == "" or not whole.isdigit():
        raise ValueError(f"{field} is not a decimal number")
    if point and (fraction == "" or not fraction.isdigit()):
        raise ValueError(f"{field} is not a decimal number")
    if len(fraction) > decimals:
        if fraction[decimals:].strip("0") != "":
            raise ValueError(f"{field} exceeds {decimals} decimal places")
        fraction = fraction[:decimals]
    fraction = fraction.ljust(decimals, "0")
    return int(whole) * (10**decimals) + (int(fraction) if fraction else 0)


def price_ticks(value: object) -> int:
    return scaled_int(value, 4, "price")


def quantity_units(value: object) -> int:
    return scaled_int(value, 6, "quantity")


def rfc3339(second: int, microsecond: int) -> str:
    moment = datetime.fromtimestamp(second, tz=timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%S") + f".{microsecond:06d}000Z"


def rfc3339_from_ms(value: object) -> str:
    milliseconds = int(value)
    if milliseconds < 0:
        raise ValueError("millisecond timestamp must be nonnegative")
    seconds, remainder = divmod(milliseconds, 1000)
    return rfc3339(seconds, remainder * 1000)


def rfc3339_from_text(value: object) -> str:
    parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    parsed = parsed.astimezone(timezone.utc)
    return rfc3339(int(parsed.timestamp()), parsed.microsecond)


def int_field(row: dict[str, object], name: str, field: str) -> int:
    value = row.get(name)
    if value is None or isinstance(value, bool):
        raise ValueError(f"{field} is missing")
    number = int(value)
    if number < 0:
        raise ValueError(f"{field} must be nonnegative")
    return number


def provenance(row: dict[str, object]) -> dict[str, object]:
    source_path = str(row.get("source_path") or row.get("source") or "")
    source_sha256 = str(row.get("source_sha256") or "")
    if source_path == "" or source_sha256 == "":
        raise ValueError("row is missing provenance")
    return {
        "source_id": source_path,
        "source_path": source_path,
        "source_sha256": source_sha256,
    }


def quality_fields(row: dict[str, object]) -> dict[str, object]:
    applied = row.get("applied")
    if applied is not None and not bool_field(applied, "applied"):
        return {
            "quality": "suspect",
            "quality_reason": "capture row was not applied to the book",
        }
    return {"quality": "healthy"}


def row_to_canonical_depth(row: dict[str, object], venue: str) -> dict[str, object]:
    kind = str(row["kind"])
    if kind not in {"snapshot", "update"}:
        raise ValueError(f"invalid depth kind: {kind}")
    event: dict[str, object] = {
        "kind": "depth_snapshot" if kind == "snapshot" else "depth_update",
        "venue": venue,
        "symbol": str(row["symbol"]),
        "event_time": rfc3339_from_ms(row["event_time_ms"]),
        "receive_time": rfc3339_from_text(row["received_time"]),
        "sequence": None,
        "bids": [
            [price_ticks(price), quantity_units(size)]
            for price, size in levels(row["bids"], "bids")
        ],
        "asks": [
            [price_ticks(price), quantity_units(size)]
            for price, size in levels(row["asks"], "asks")
        ],
    }
    event.update(provenance(row))
    event.update(quality_fields(row))
    if kind == "snapshot":
        event["last_update_id"] = row.get("last_update_id")
    else:
        event["first_update_id"] = int_field(row, "first_update_id", "first_update_id")
        event["last_update_id"] = int_field(row, "final_update_id", "final_update_id")
        previous = row.get("previous_update_id")
        event["previous_update_id"] = None if previous is None else int(previous)
    return event


def row_to_canonical_trade(row: dict[str, object], venue: str) -> dict[str, object]:
    trade_id = str(row["trade_id"]).strip()
    if trade_id == "" or not trade_id.isdigit():
        raise ValueError("trade_id must be a nonnegative integer")
    event: dict[str, object] = {
        "kind": "trade",
        "venue": venue,
        "symbol": str(row["symbol"]),
        "event_time": rfc3339_from_ms(row["trade_time_ms"]),
        "receive_time": rfc3339_from_text(row["received_time"]),
        "sequence": None,
        "trade_id": int(trade_id),
        "price_ticks": price_ticks(row["price"]),
        "quantity_units": quantity_units(row["quantity"]),
        "buyer_is_maker": bool_field(row.get("buyer_is_maker"), "buyer_is_maker"),
    }
    event.update(provenance(row))
    event.update({"quality": "healthy"})
    return event


def row_to_canonical_observation(row: dict[str, object], venue: str) -> dict[str, object]:
    symbol = str(row.get("symbol") or "")
    if symbol == "":
        raise ValueError("observation has no symbol")
    payload = row.get("payload")
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload, dict):
        raise ValueError("observation payload must be an object")
    observed_at = rfc3339_from_text(row["observed_at"])
    event: dict[str, object] = {
        "kind": "observation",
        "venue": venue,
        "symbol": symbol,
        "event_time": observed_at,
        "receive_time": observed_at,
        "sequence": None,
        "data_type": str(row["data_type"]),
        "payload": json.dumps(payload, separators=(",", ":")),
        "quality": "healthy",
    }
    event.update(provenance(row))
    return event


CANONICAL_KINDS = {
    "depth": row_to_canonical_depth,
    "trades": row_to_canonical_trade,
    "observations": row_to_canonical_observation,
}


def manifest_for(fixture: str, rows: list[dict[str, object]], args, sha256: str):
    times = [str(row["event_time"]) for row in rows]
    hashes = sorted(
        {str(row["source_sha256"]) for row in rows if row.get("source_sha256")}
    )
    config = json.dumps(
        {
            "query_version": QUERY_VERSION,
            "price_ticks": PRICE_TICKS,
            "quantity_units": QUANTITY_UNITS,
            "kind": args.kind,
            "venue": args.venue,
        },
        sort_keys=True,
    ).encode("utf-8")
    return {
        "fixture": fixture,
        "format": "canonical",
        "kind": args.kind,
        "query_version": QUERY_VERSION,
        "row_count": len(rows),
        "event_time_range": [min(times), max(times)] if times else None,
        "source_hashes": hashes,
        "symbol": args.symbol,
        "start": args.start,
        "end": args.end,
        "config_sha256": hashlib.sha256(config).hexdigest(),
        "fixture_sha256": sha256,
        "created_at": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
    }


# ------------------------------------------------------------------- queries


DEPTH_COLUMNS = (
    "kind, segment, symbol, received_time, event_time_ms, source_path, "
    "source_sha256, applied, last_update_id, first_update_id, final_update_id, "
    "previous_update_id, bids, asks"
)


def query_for(kind: str, symbol: str | None, start: str | None, end: str | None) -> str:
    predicates = []
    if symbol:
        predicates.append(f"symbol = {sql_quote(symbol)}")
    if start:
        predicates.append(f"received_time >= {sql_quote(start)}::timestamptz")
    if end:
        predicates.append(f"received_time < {sql_quote(end)}::timestamptz")
    where = " WHERE " + " AND ".join(predicates) if predicates else ""
    if kind == "depth":
        # Snapshots first inside their capture window: the normalizer writes
        # the updates received during a snapshot fetch before the snapshot row,
        # and those updates belong after it. Grouping by the five-minute wall
        # clock bucket and putting the snapshot first makes the fixture
        # replayable in file order, so no consumer has to infer alignment.
        # The row's own segment column cannot do this, because it restarts in
        # every per-window normalized file.
        return (
            f"SELECT {DEPTH_COLUMNS} FROM depth_events{where} "
            "ORDER BY floor(extract(epoch from received_time) / 300), "
            "(kind = 'snapshot') DESC, received_time, event_key"
        )
    if kind == "trades":
        return (
            "SELECT symbol, received_time, trade_time_ms, trade_id, price, "
            "quantity, buyer_is_maker, source_path, source_sha256 "
            f"FROM trade_events{where} ORDER BY received_time, event_key"
        )
    if kind == "observations":
        observed = []
        if symbol:
            observed.append(f"symbol = {sql_quote(symbol)}")
        if start:
            observed.append(f"observed_at >= {sql_quote(start)}::timestamptz")
        if end:
            observed.append(f"observed_at < {sql_quote(end)}::timestamptz")
        observed_where = " WHERE " + " AND ".join(observed) if observed else ""
        return (
            "SELECT observed_at, data_type, source, symbol, payload, source_sha256 "
            f"FROM observations{observed_where} ORDER BY observed_at, data_type"
        )
    raise ValueError(f"unsupported kind: {kind}")


def query_json(
    tiger: str, service: str | None, sql: str, query_json_path: Path | None
) -> list[dict[str, object]]:
    if query_json_path is not None:
        value = json.loads(query_json_path.read_text(encoding="utf-8"))
    else:
        command = [tiger]
        if service:
            command += ["--service-id", service]
        command += [
            "db",
            "query",
            "--read-only",
            "--output",
            "json",
            "--command",
            sql,
        ]
        completed = subprocess.run(command, check=False, text=True, capture_output=True)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
        value = json.loads(completed.stdout)
    if isinstance(value, list):
        rows = value
    elif isinstance(value, dict) and isinstance(value.get("rows"), list):
        rows = value["rows"]
    elif isinstance(value, dict) and isinstance(value.get("data"), list):
        rows = value["data"]
    elif isinstance(value, dict) and isinstance(value.get("result_sets"), list):
        result_sets = value["result_sets"]
        if len(result_sets) != 1 or not isinstance(result_sets[0], dict):
            raise ValueError("Tiger fixture export requires one result set")
        result_set = result_sets[0]
        columns = result_set.get("columns")
        raw_rows = result_set.get("rows")
        if not isinstance(columns, list) or not isinstance(raw_rows, list):
            raise ValueError("Tiger result set is missing columns or rows")
        names = [column.get("name") for column in columns if isinstance(column, dict)]
        if len(names) != len(columns) or not all(isinstance(name, str) for name in names):
            raise ValueError("Tiger result set has invalid column names")
        rows = [dict(zip(names, raw_row)) for raw_row in raw_rows]
    else:
        raise ValueError("Tiger query JSON must be a row array or result set")
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("Tiger query rows must be objects")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--service")
    parser.add_argument("--symbol")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--format", choices=["normalized", "canonical"], default="normalized")
    parser.add_argument("--kind", choices=sorted(CANONICAL_KINDS), default="depth")
    parser.add_argument("--venue", default=DEFAULT_VENUE)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--query-json", type=Path, help="Use saved Tiger JSON for offline tests")
    parser.add_argument("--output", type=Path, default=Path("-"))
    parser.add_argument("--tiger", default="tiger")
    args = parser.parse_args()
    try:
        rows = query_json(
            args.tiger,
            args.service,
            query_for(args.kind, args.symbol, args.start, args.end),
            args.query_json,
        )
        if args.format == "normalized":
            events = [row_to_normalized(row) for row in rows]
        else:
            convert = CANONICAL_KINDS[args.kind]
            events = [convert(row, args.venue) for row in rows]
        lines = [json.dumps(event, separators=(",", ":")) for event in events]
        document = "".join(line + "\n" for line in lines)
        handle = (
            sys.stdout
            if str(args.output) == "-"
            else args.output.open("w", encoding="utf-8")
        )
        try:
            handle.write(document)
        finally:
            if handle is not sys.stdout:
                handle.close()
        if args.manifest is not None:
            digest = hashlib.sha256(document.encode("utf-8")).hexdigest()
            manifest = manifest_for(str(args.output), events, args, digest)
            args.manifest.write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            print(
                f"manifest={args.manifest} rows={len(events)} sha256={digest}",
                file=sys.stderr,
            )
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"Tiger fixture export failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
