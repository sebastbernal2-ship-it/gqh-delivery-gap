#!/usr/bin/env python3
"""Convert a Hyperliquid websocket capture into the engine's canonical fixture format.

Follows `orderbook-engine/docs/engine-io-contract.md`: one JSON object per line, integer units only
(price 1e-4 ticks, quantity 1e-6 units, rate 1e-8), full provenance envelope, and the ordering contract of
five minute receive-time buckets with snapshots first inside a bucket.

Conventions that are assumptions and recorded as such in the manifest:
  - trade `side` is the taker side, so `B` means the taker bought and `buyer_is_maker` is false.
  - `activeAssetCtx` carries no venue timestamp, so receive time is used for both clocks and the row is
    marked `suspect` with that reason.
  - `l2Book` snapshots carry no update id, so `last_update_id` is null and `sequence` carries venue time.

    python3 scripts/build_hyperliquid_fixture.py data/hyperliquid/ws/ws-*.jsonl --out-dir data/hyperliquid/fixtures
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENUE = "hyperliquid"
PRICE_SCALE = 10_000
QUANTITY_SCALE = 1_000_000
RATE_SCALE = 100_000_000
BUCKET_SECONDS = 300


def rfc3339(seconds: float) -> str:
    stamp = dt.datetime.fromtimestamp(seconds, tz=dt.timezone.utc)
    return stamp.strftime("%Y-%m-%dT%H:%M:%S.") + f"{stamp.microsecond:06d}000Z"


def ms_to_seconds(value) -> float | None:
    try:
        return float(value) / 1000.0
    except (TypeError, ValueError):
        return None


def ticks(price) -> int:
    return int(round(float(price) * PRICE_SCALE))


def units(quantity) -> int:
    return int(round(float(quantity) * QUANTITY_SCALE))


def rate(value) -> int:
    return int(round(float(value) * RATE_SCALE))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture")
    parser.add_argument("--out-dir", default=str(ROOT / "data" / "hyperliquid" / "fixtures"))
    parser.add_argument("--sample-minutes", type=float, default=10.0,
                        help="how many minutes of the capture go into the committed sample")
    parser.add_argument("--sample-out", default=str(ROOT / "results" / "hyperliquid-fixture"))
    args = parser.parse_args()

    capture = Path(args.capture)
    if not capture.exists():
        raise SystemExit(f"capture not found: {capture}")
    digest = hashlib.sha256(capture.read_bytes()).hexdigest()
    source_path = str(capture.relative_to(ROOT)) if capture.is_relative_to(ROOT) else str(capture)

    rows = []
    first_receive = last_receive = None
    for line in capture.open():
        if not line.strip():
            continue
        record = json.loads(line)
        channel = record.get("channel")
        receive = record.get("recv_ts")
        data = record.get("data")
        if receive is None or data is None:
            continue
        first_receive = receive if first_receive is None else min(first_receive, receive)
        last_receive = receive if last_receive is None else max(last_receive, receive)
        envelope = {"venue": VENUE, "source_id": "hyperliquid-ws", "source_path": source_path,
                    "source_sha256": digest, "sequence": None, "quality": "healthy"}
        if channel == "l2Book" and isinstance(data, dict):
            coin = data.get("coin", "")
            venue_time = ms_to_seconds(data.get("time")) or receive
            levels = data.get("levels") or [[], []]
            bids = [[ticks(level["px"]), units(level["sz"])] for level in levels[0]] if levels else []
            asks = [[ticks(level["px"]), units(level["sz"])] for level in levels[1]] if len(levels) > 1 else []
            rows.append({**envelope, "kind": "depth_snapshot", "symbol": coin,
                         "event_time": rfc3339(venue_time), "receive_time": rfc3339(receive),
                         "sequence": int(data.get("time") or 0), "last_update_id": None,
                         "bids": bids, "asks": asks, "_bucket": int(receive // BUCKET_SECONDS),
                         "_snapshot": True})
        elif channel == "trades" and isinstance(data, list):
            for trade in data:
                coin = trade.get("coin", "")
                venue_time = ms_to_seconds(trade.get("time")) or receive
                side = str(trade.get("side", "")).upper()
                rows.append({**envelope, "kind": "trade", "symbol": coin,
                             "event_time": rfc3339(venue_time), "receive_time": rfc3339(receive),
                             "sequence": int(trade.get("tid") or 0),
                             "trade_id": int(trade.get("tid") or 0),
                             "price_ticks": ticks(trade.get("px")),
                             "quantity_units": units(trade.get("sz")),
                             "buyer_is_maker": side == "A",
                             "_bucket": int(receive // BUCKET_SECONDS), "_snapshot": False})
        elif channel == "activeAssetCtx" and isinstance(data, dict):
            coin = data.get("coin", "")
            ctx = data.get("ctx") or {}
            payload = {**envelope, "kind": "mark", "symbol": coin,
                       "event_time": rfc3339(receive), "receive_time": rfc3339(receive),
                       "quality": "suspect", "quality_reason": "venue provides no timestamp; receive time used",
                       "_bucket": int(receive // BUCKET_SECONDS), "_snapshot": False}
            if ctx.get("markPx"):
                payload["mark_ticks"] = ticks(ctx["markPx"])
            if ctx.get("oraclePx"):
                payload["index_ticks"] = ticks(ctx["oraclePx"])
            if ctx.get("funding"):
                payload["rate"] = rate(ctx["funding"])
            rows.append(payload)
            if ctx.get("openInterest"):
                rows.append({**envelope, "kind": "observation", "symbol": coin,
                             "event_time": rfc3339(receive), "receive_time": rfc3339(receive),
                             "quality": "suspect", "quality_reason": "venue provides no timestamp; receive time used",
                             "field": "open_interest_units", "value": units(ctx["openInterest"]),
                             "_bucket": int(receive // BUCKET_SECONDS), "_snapshot": False})

    # The engine's ordering contract: bucket by five minute receive windows, snapshots first, then by time.
    rows.sort(key=lambda row: (row["_bucket"], 0 if row["_snapshot"] else 1, row["receive_time"], row["kind"]))
    for row in rows:
        row.pop("_bucket", None)
        row.pop("_snapshot", None)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    full = out_dir / (capture.stem + ".fixture.jsonl")
    full.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows))

    sample_rows = [row for row in rows
                   if first_receive is not None and row["receive_time"] <= rfc3339(first_receive + args.sample_minutes * 60)]
    sample_dir = Path(args.sample_out)
    sample_dir.mkdir(parents=True, exist_ok=True)
    sample = sample_dir / "hyperliquid-10min.fixture.jsonl"
    sample.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in sample_rows))
    sample_manifest = {
        "fixture": str(sample.relative_to(ROOT)),
        "fixture_sha256": hashlib.sha256(sample.read_bytes()).hexdigest(),
        "format": "canonical",
        "venue": VENUE,
        "kind": "mixed depth, trades, mark and observation",
        "row_count": len(sample_rows),
        "event_time_range": [rows[0]["event_time"], rows[-1]["event_time"]] if rows else [],
        "source": source_path,
        "source_sha256": digest,
        "created_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "query_version": "quanthacks-hyperliquid-fixture-v1",
        "conventions": {
            "units": "price 1e-4 ticks, quantity 1e-6 units, rate 1e-8",
            "trade_side": "side B means the taker bought, so buyer_is_maker is false",
            "book": "snapshots, not deltas; no update id exists, last_update_id is null",
            "context_rows": "marked suspect because the venue provides no timestamp",
            "ordering": "five minute receive buckets, snapshots first, then receive time",
        },
        "mode": "aggregated book snapshots with bounded fills; no order level FIFO is available",
    }
    (sample_dir / "hyperliquid-10min.manifest.json").write_text(json.dumps(sample_manifest, indent=1) + "\n")
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["kind"]] = counts.get(row["kind"], 0) + 1
    print(f"full fixture {full.relative_to(ROOT) if full.is_relative_to(ROOT) else full}: {len(rows)} rows {counts}")
    print(f"sample {sample.relative_to(ROOT)}: {len(sample_rows)} rows, "
          f"{(sample.stat().st_size / 1e6):.2f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
