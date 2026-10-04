#!/usr/bin/env python3
"""Export pinned Hyperliquid mirror L2 snapshots to canonical engine JSONL.

This adapter intentionally emits only absolute ``depth_snapshot`` events. It does
not convert snapshots into deltas, and it does not map trade prints into the
engine's ``buyer_is_maker`` field because the source-side semantics are not
validated. Source artifacts are hash-checked before parsing.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iso_ns(value: int) -> str:
    seconds, nanos = divmod(value, 1_000_000_000)
    stamp = datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    return f"{stamp}.{nanos:09d}Z"


def scaled(value: str, scale: int) -> int:
    number = Decimal(value)
    if not number.is_finite() or number <= 0:
        raise ValueError("nonpositive or nonfinite book level")
    return int((number * scale).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def export(plan_path: Path, objects: Path, output: Path, manifest_path: Path) -> dict:
    import pyarrow as pa
    import pyarrow.parquet as pq

    plan = json.loads(plan_path.read_text())
    candidates = [entry for entry in plan["files"] if entry["kind"] == "books"]
    if len(candidates) != 1:
        raise ValueError("plan must contain exactly one books object")
    source = candidates[0]
    if source["dataset"] != "gionuibk/hyperliquidL2Book-v2":
        raise ValueError("unexpected dataset")
    raw_path = objects / source["sha256"]
    if raw_path.stat().st_size != source["size"] or sha256(raw_path) != source["sha256"]:
        raise ValueError("source size or SHA-256 mismatch")

    parquet = pq.ParquetFile(raw_path)
    if parquet.schema_arrow.names != ["timestamp", "coin", "payload"]:
        raise ValueError("unexpected mirror schema")
    if not pa.types.is_timestamp(parquet.schema_arrow.field("timestamp").type) or parquet.schema_arrow.field("timestamp").type.unit != "ns":
        raise ValueError("outer timestamp must retain nanosecond units")

    events = []
    for batch in parquet.iter_batches(batch_size=4096):
        clocks = batch.column(batch.schema.get_field_index("timestamp")).cast(pa.int64()).to_pylist()
        coins = batch.column(batch.schema.get_field_index("coin")).to_pylist()
        payloads = batch.column(batch.schema.get_field_index("payload")).to_pylist()
        for receive_ns, coin, payload in zip(clocks, coins, payloads):
            if coin != "BTC":
                continue
            message = json.loads(payload)
            if message.get("channel") != "l2Book":
                raise ValueError("unexpected payload channel")
            data = message["data"]
            if data.get("coin") != "BTC" or not isinstance(data.get("time"), int):
                raise ValueError("invalid BTC book identity or event time")
            sides = data.get("levels")
            if not isinstance(sides, list) or len(sides) != 2:
                raise ValueError("expected bid and ask side arrays")
            normalized = []
            for side in sides:
                normalized.append([[scaled(level["px"], 10_000), scaled(level["sz"], 1_000_000)]
                                   for level in side])
            events.append((receive_ns, {
                "kind": "depth_snapshot",
                "venue": "hyperliquid-perp",
                "symbol": "BTC",
                "event_time": iso_ns(data["time"] * 1_000_000),
                "receive_time": iso_ns(receive_ns),
                "sequence": None,
                "source_id": f"{source['dataset']}@{source['revision']}:{source['path']}",
                "source_path": str(raw_path),
                "source_sha256": source["sha256"],
                "quality": "suspect",
                "quality_reason": "third-party aggregated L2 snapshot; outer clock is an unverified recorded-time proxy; no venue sequence",
                "last_update_id": None,
                "bids": normalized[0],
                "asks": normalized[1],
            }))

    events.sort(key=lambda item: item[0])
    if not events:
        raise ValueError("no BTC book snapshots in selected object")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        for _, event in events:
            stream.write(json.dumps(event, separators=(",", ":")) + "\n")
    receipt = {
        "dataset": "hyperliquid-mirror-btc-l2-snapshot-pilot",
        "source_dataset": source["dataset"],
        "source_revision": source["revision"],
        "source_path": source["path"],
        "source_url": f"https://huggingface.co/datasets/{source['dataset']}/resolve/{source['revision']}/{source['path']}",
        "source_size_bytes": source["size"],
        "source_sha256": source["sha256"],
        "paired_trade_source_sha256": next(e["sha256"] for e in plan["files"] if e["kind"] == "trades"),
        "canonical_file": str(output),
        "canonical_size_bytes": output.stat().st_size,
        "canonical_sha256": sha256(output),
        "canonical_rows": len(events),
        "event_time_range": [events[0][1]["event_time"], events[-1][1]["event_time"]],
        "receive_time_range": [events[0][1]["receive_time"], events[-1][1]["receive_time"]],
        "contents": "BTC aggregated L2 absolute snapshots only; trade prints remain separate and are not converted to maker-side events",
        "sequence_available": False,
        "availability_clock": "outer Parquet timestamp treated as recorded/receive-time proxy; semantics and feed completeness unverified",
        "quality": "suspect",
        "training_ready": False,
        "adapter_sha256": sha256(Path(__file__)),
    }
    receipt["manifest_sha256"] = hashlib.sha256(
        (json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n").encode()).hexdigest()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--objects", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    result = export(args.plan, args.objects, args.output, args.manifest)
    print(json.dumps({k: result[k] for k in ("canonical_rows", "canonical_size_bytes", "canonical_sha256", "source_sha256", "adapter_sha256")}))


if __name__ == "__main__":
    main()
