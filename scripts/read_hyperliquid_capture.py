#!/usr/bin/env python3
"""Summarize a Hyperliquid websocket capture: counts, span, cadence, and the reconstructed series.

This is the consumer side of `scripts/collect_hyperliquid_ws.py`, and the handoff tool for whoever wires the
engine. It reads one capture file and writes a small summary plus optional per coin series of marks, open
interest, funding and trade aggregates, so nothing has to be re derived from raw JSONL each time.

    python3 scripts/read_hyperliquid_capture.py data/hyperliquid/ws/ws-20261004T071502Z.jsonl
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--out")
    args = parser.parse_args()
    path = Path(args.path)
    if not path.exists():
        raise SystemExit(f"capture not found: {path}")

    counts = collections.Counter()
    coins = collections.Counter()
    first = last = None
    context: dict[str, list[dict]] = collections.defaultdict(list)
    trades: dict[str, list[dict]] = collections.defaultdict(list)
    book_sizes: dict[str, list[int]] = collections.defaultdict(list)
    book_intervals: dict[str, list[float]] = collections.defaultdict(list)
    book_last: dict[str, float] = {}
    for line in path.open():
        if not line.strip():
            continue
        row = json.loads(line)
        channel = row.get("channel", "unknown")
        counts[channel] += 1
        stamp = row.get("recv_ts")
        first = stamp if first is None else min(first, stamp) if stamp else first
        last = stamp if last is None else max(last, stamp) if stamp else last
        data = row.get("data")
        if channel == "activeAssetCtx" and isinstance(data, dict):
            coin = data.get("coin")
            ctx = data.get("ctx") or {}
            coins[coin] += 1
            try:
                context[coin].append({"ts": stamp, "funding": float(ctx.get("funding") or 0),
                                      "open_interest": float(ctx.get("openInterest") or 0),
                                      "mark": float(ctx.get("markPx") or 0),
                                      "oracle": float(ctx.get("oraclePx") or 0),
                                      "mid": float(ctx.get("midPx") or 0)})
            except (TypeError, ValueError):
                continue
        elif channel == "trades" and isinstance(data, list):
            for trade in data:
                coin = trade.get("coin")
                coins[coin] += 1
                try:
                    trades[coin].append({"ts": trade.get("time"), "px": float(trade.get("px") or 0),
                                         "sz": float(trade.get("sz") or 0), "side": trade.get("side"),
                                         "users": trade.get("users")})
                except (TypeError, ValueError):
                    continue
        elif channel == "l2Book" and isinstance(data, dict):
            coin = data.get("coin")
            levels = data.get("levels") or [[], []]
            coins[coin] += 1
            book_sizes[coin].append(sum(len(side) for side in levels))
            if stamp is not None and coin in book_last:
                book_intervals[coin].append(stamp - book_last[coin])
            if stamp is not None:
                book_last[coin] = stamp

    per_coin = {}
    for coin in sorted(coins):
        marks = [row["mark"] for row in context.get(coin, []) if row["mark"]]
        intervals = book_intervals.get(coin, [])
        per_coin[coin] = {
            "messages": coins[coin],
            "context_samples": len(context.get(coin, [])),
            "trade_prints": len(trades.get(coin, [])),
            "book_snapshots": len(book_sizes.get(coin, [])),
            "book_median_levels": statistics.median(book_sizes.get(coin, [])) if book_sizes.get(coin) else None,
            "book_median_interval_s": round(statistics.median(intervals), 2) if intervals else None,
            "mark_first": marks[0] if marks else None,
            "mark_last": marks[-1] if marks else None,
        }
    summary = {"file": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
               "lines": sum(counts.values()), "channels": dict(counts),
               "span_seconds": round(last - first, 1) if first and last else None,
               "per_coin": per_coin,
               "note": "no liquidation flag exists on trades; order level FIFO is not available from public data"}
    out = Path(args.out) if args.out else path.with_suffix(".summary.json")
    out.write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
