#!/usr/bin/env python3
"""Validate one completed Binance capture and emit KDB-X JSONL rows."""

import argparse
import gzip
import hashlib
import json
import math
import sys
from datetime import datetime
from pathlib import Path


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def level_rows(value, field):
    if not isinstance(value, list):
        raise ValueError(f"{field} is not an array")
    rows = []
    for level in value:
        if not isinstance(level, list) or len(level) != 2:
            raise ValueError(f"invalid {field} level")
        price_text, size_text = level
        try:
            price = float(price_text)
            size = float(size_text)
        except (TypeError, ValueError) as error:
            raise ValueError(f"invalid {field} price or size") from error
        if not math.isfinite(price) or price <= 0 or not math.isfinite(size) or size < 0:
            raise ValueError(f"invalid {field} price or size")
        rows.append([str(price_text), str(size_text)])
    return rows


def read_rows(path: Path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                received_text, body = line.rstrip("\n").split(" ", 1)
                received = parse_time(received_text)
                envelope = json.loads(body)
                data = envelope["data"]
                stream = envelope["stream"]
            except (ValueError, KeyError, json.JSONDecodeError) as error:
                raise ValueError(f"line {number}: malformed capture row") from error
            if not isinstance(data, dict) or not isinstance(stream, str):
                raise ValueError(f"line {number}: invalid capture envelope")
            yield number, received, stream, data


def validate_and_normalize(path: Path):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    source = str(path)
    previous_received = None
    current = None
    bootstrapped = False
    pending = []
    segment = 0
    normalized = []

    def append_row(kind, received, stream, data, applied):
        nonlocal normalized
        event_ms = data.get("E")
        if not isinstance(event_ms, int) or event_ms < 0:
            raise ValueError("invalid Binance event timestamp")
        row = {
            "kind": kind,
            "segment": segment,
            "symbol": str(data.get("s") or stream.split("@", 1)[0].upper()),
            "received_time": received.strftime("%Y.%m.%dD%H:%M:%S.%f") + "000",
            "event_time_ms": event_ms,
            "source_path": source,
            "source_sha256": digest,
            "applied": applied,
            "bids": level_rows(data["bids"] if kind == "snapshot" else data["b"], "bids"),
            "asks": level_rows(data["asks"] if kind == "snapshot" else data["a"], "asks"),
        }
        if kind == "snapshot":
            row.update(
                last_update_id=data["lastUpdateId"],
                first_update_id=None,
                final_update_id=None,
                previous_update_id=None,
            )
        else:
            row.update(
                last_update_id=None,
                first_update_id=data["U"],
                final_update_id=data["u"],
                previous_update_id=data["pu"],
            )
        normalized.append(row)

    def apply_update(received, stream, data):
        nonlocal current, bootstrapped
        first_id = data.get("U")
        final_id = data.get("u")
        previous_id = data.get("pu")
        if not all(isinstance(value, int) for value in (first_id, final_id, previous_id)):
            raise ValueError("invalid Binance update ID")
        if first_id < 0 or final_id < first_id or previous_id < 0:
            raise ValueError("invalid Binance update ID range")
        if current is None:
            pending.append((received, stream, data))
            return
        if final_id <= current:
            append_row("update", received, stream, data, False)
            return
        next_id = current + 1
        bridges_snapshot = first_id <= next_id <= final_id
        contiguous = previous_id == current if bootstrapped else previous_id == current or bridges_snapshot
        if not contiguous:
            raise ValueError(f"Binance update gap: expected previous update {current}, got {previous_id}")
        current = final_id
        bootstrapped = True
        append_row("update", received, stream, data, True)

    for number, received, stream, data in read_rows(path):
        if previous_received is not None and received < previous_received:
            raise ValueError(f"line {number}: capture timestamps are not monotonic")
        previous_received = received
        if "lastUpdateId" in data:
            last_id = data["lastUpdateId"]
            if not isinstance(last_id, int) or last_id < 0:
                raise ValueError(f"line {number}: invalid snapshot update ID")
            segment += 1
            current = last_id
            bootstrapped = False
            buffered, pending = pending, []
            for buffered_received, buffered_stream, buffered_data in buffered:
                apply_update(buffered_received, buffered_stream, buffered_data)
            append_row("snapshot", received, stream, data, True)
        else:
            apply_update(received, stream, data)

    if current is None:
        raise ValueError("capture has no snapshot")
    if pending:
        raise ValueError("capture ended before buffered updates reached a snapshot")
    return normalized


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        rows = validate_and_normalize(args.capture)
        with args.output.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, separators=(",", ":")) + "\n")
        print(f"validated_rows={len(rows)} output={args.output}")
    except (OSError, ValueError) as error:
        print(f"capture rejected: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
