#!/usr/bin/env python3
"""Run the frozen conjunction on a websocket capture: one second mids and open interest.

The reversion study ran on fifteen second REST snapshots. The capture carries context at one second, so
this asks whether the finer clock changes the event count. Rule is the frozen one from
`src/live/hyperliquid.py`: a one step move beyond three trailing sigmas, window sixty, with open interest
down one percent against the window median.

    python3 scripts/evaluate_ws_capture_conjunction.py data/hyperliquid/ws/ws-*.jsonl
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from live.hyperliquid import trigger  # noqa: E402

OUT = ROOT / "results" / "hyperliquid-ws-conjunction.json"
HORIZONS_MINUTES = (1, 5, 15, 60)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("captures", nargs="+")
    args = parser.parse_args()

    series: dict[str, list[dict]] = collections.defaultdict(list)
    for path in args.captures:
        for line in Path(path).open():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("channel") != "activeAssetCtx" or not isinstance(row.get("data"), dict):
                continue
            data = row["data"]
            ctx = data.get("ctx") or {}
            try:
                series[data.get("coin")].append({"ts": float(row["recv_ts"]),
                                                 "mid": float(ctx.get("midPx") or 0),
                                                 "oi": float(ctx.get("openInterest") or 0)})
            except (TypeError, ValueError):
                continue

    report: dict = {"captures": args.captures, "per_coin": {}, "horizons_minutes": HORIZONS_MINUTES}
    for coin, rows in sorted(series.items()):
        rows.sort(key=lambda row: row["ts"])
        if len(rows) < 120:
            report["per_coin"][coin] = {"samples": len(rows), "status": "insufficient"}
            continue
        mids = [row["mid"] for row in rows]
        ois = [row["oi"] for row in rows]
        events = []
        for index in range(65, len(rows)):
            if trigger(mids[:index + 1], ois[:index + 1], window=60, sigma_multiple=3.0, oi_drop=0.01):
                events.append(index)
        paths = {}
        for horizon in HORIZONS_MINUTES:
            steps = horizon * 60
            values = []
            for index in events:
                if index + steps < len(rows) and mids[index]:
                    values.append((mids[index + steps] / mids[index] - 1) * 1e4)
            paths[str(horizon)] = {"n": len(values),
                                   "mean_bps": round(statistics.mean(values), 2) if values else None}
        report["per_coin"][coin] = {
            "samples": len(rows),
            "span_minutes": round((rows[-1]["ts"] - rows[0]["ts"]) / 60, 1),
            "events": len(events),
            "event_times": [rows[index]["ts"] for index in events][:20],
            "forward_paths": paths,
        }
    OUT.write_text(json.dumps(report, indent=1) + "\n")
    for coin, block in report["per_coin"].items():
        print(f"{coin}: {block.get('samples')} samples, {block.get('span_minutes')} minutes, "
              f"events {block.get('events')}")
        if block.get("forward_paths"):
            print("   paths:", json.dumps(block["forward_paths"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
