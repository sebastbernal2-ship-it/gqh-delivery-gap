#!/usr/bin/env python3
"""Validate Binance trade-event capture and emit KDB-X JSONL rows."""

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


def positive_number(value, field):
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"invalid {field}") from error
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"invalid {field}")
    return str(value)


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
            if not isinstance(data, dict) or data.get("e") not in {"aggTrade", "trade"}:
                raise ValueError(f"line {number}: expected Binance trade event")
            if not isinstance(stream, str):
                raise ValueError(f"line {number}: invalid stream")
            yield number, received, data


def validate_and_normalize(path: Path):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    source = str(path)
    previous_received = None
    previous_trade_id = None
    symbol = None
    normalized = []

    for number, received, data in read_rows(path):
        if previous_received is not None and received < previous_received:
            raise ValueError(f"line {number}: capture timestamps are not monotonic")
        previous_received = received

        event_ms = data.get("E")
        trade_ms = data.get("T")
        trade_id = data.get("a", data.get("t"))
        current_symbol = data.get("s")
        if not all(isinstance(value, int) for value in (event_ms, trade_ms, trade_id)):
            raise ValueError(f"line {number}: invalid trade timestamp or ID")
        if event_ms < 0 or trade_ms < 0 or trade_id < 0:
            raise ValueError(f"line {number}: negative trade timestamp or ID")
        if previous_trade_id is not None and trade_id < previous_trade_id:
            raise ValueError(f"line {number}: trade IDs are not monotonic")
        previous_trade_id = trade_id
        if not isinstance(current_symbol, str) or not current_symbol:
            raise ValueError(f"line {number}: invalid trade symbol")
        if symbol is None:
            symbol = current_symbol
        elif current_symbol != symbol:
            raise ValueError(f"line {number}: multiple symbols in one trade segment")
        if not isinstance(data.get("m"), bool):
            raise ValueError(f"line {number}: invalid maker flag")

        normalized.append(
            {
                "received_time": received.strftime("%Y.%m.%dD%H:%M:%S.%f") + "000",
                "event_time_ms": event_ms,
                "trade_time_ms": trade_ms,
                "source_path": source,
                "source_sha256": digest,
                "symbol": current_symbol,
                "trade_id": trade_id,
                "price": positive_number(data.get("p"), "trade price"),
                "quantity": positive_number(data.get("q"), "trade quantity"),
                "buyer_is_maker": data["m"],
            }
        )
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
