#!/usr/bin/env python3
"""Cross market behaviour at dislocation events.

Protocol: docs/plan/spillover-study.md. Development only, recorded window. Writes
results/spillover-study.json.

    python3 scripts/build_spillover_study.py
"""
from __future__ import annotations

import collections
import glob
import json
import math
import random
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "spillover-study.json"
TAKER_BPS = 4.5
HORIZONS = (4, 20, 60)
MINUTE_BARS = 4
MATCH_MS = 30_000
DRAWS = 5000
SEED = 42


def percentile(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    position = q * (len(ordered) - 1)
    low, high = int(math.floor(position)), int(math.ceil(position))
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def load_markets() -> dict[str, list[dict]]:
    by_market: dict[str, list[dict]] = collections.defaultdict(list)
    for path in sorted(glob.glob(str(ROOT / "data" / "tape" / "*.jsonl"))):
        with open(path) as handle:
            for line in handle:
                if line.strip():
                    row = json.loads(line)
                    by_market[row["coin"]].append(row)
    for rows in by_market.values():
        rows.sort(key=lambda row: row.get("time") or 0)
    return by_market


def main() -> int:
    markets = load_markets()
    times = {market: [row.get("time") or 0 for row in rows] for market, rows in markets.items()}
    mids = {market: [float(row["mid"]) for row in rows] for market, rows in markets.items()}
    spreads = {market: [float(row.get("spread_bps") or 0) for row in rows] for market, rows in markets.items()}
    depths = {market: [min(float(row.get("depth_bid_notional") or 0), float(row.get("depth_ask_notional") or 0))
                       for row in markets[market]] for market in markets}

    def nearest(market: str, timestamp: int) -> int | None:
        series = times[market]
        if not series:
            return None
        low, high = 0, len(series) - 1
        while low < high:
            middle = (low + high) // 2
            if series[middle] < timestamp:
                low = middle + 1
            else:
                high = middle
        for candidate in (low - 1, low):
            if 0 <= candidate < len(series) and abs(series[candidate] - timestamp) <= MATCH_MS:
                return candidate
        return None

    events = {}
    for market, rows in markets.items():
        n = len(rows)
        mids_m = mids[market]
        moves = {i: mids_m[i] / mids_m[i - MINUTE_BARS] - 1 for i in range(MINUTE_BARS, n)}
        abs_moves = [abs(value) for value in moves.values()]
        threshold_99 = percentile(abs_moves, 0.99)
        threshold_95 = percentile(abs_moves, 0.95)
        events[market] = {"L2": [(i, -1.0 if moves[i] > 0 else 1.0) for i in range(MINUTE_BARS, n)
                                 if abs(moves[i]) >= threshold_99],
                          "L3": [(i, -1.0 if moves[i] > 0 else 1.0) for i in range(MINUTE_BARS, n)
                                 if abs(moves[i]) >= threshold_95]}

    random.seed(SEED)
    results = {}
    for level in ("L2", "L3"):
        for source in sorted(markets):
            for target in sorted(markets):
                nets, depths_at_entry, pairs = [], [], 0
                for index, direction in events[source][level]:
                    entry = nearest(target, times[source][index])
                    if entry is None:
                        continue
                    for horizon in (HORIZONS[-1],):
                        if entry + horizon >= len(markets[target]):
                            continue
                        gross = direction * (mids[target][entry + horizon] / mids[target][entry] - 1) * 1e4
                        cost = 2 * (TAKER_BPS + spreads[target][entry] / 2)
                        nets.append(gross - cost)
                        depths_at_entry.append(depths[target][entry])
                        pairs += 1
                if not nets:
                    continue
                null = []
                candidates = list(range(MINUTE_BARS, len(markets[target]) - HORIZONS[-1]))
                for _ in range(DRAWS // 8):
                    draws = random.choices(candidates, k=max(1, len(nets)))
                    null.append(statistics.mean([
                        (-1.0 if mids[target][i] / mids[target][i - MINUTE_BARS] - 1 > 0 else 1.0)
                        * (mids[target][i + HORIZONS[-1]] / mids[target][i] - 1) * 1e4
                        - 2 * (TAKER_BPS + spreads[target][i] / 2) for i in draws]))
                observed = statistics.mean(nets)
                p_value = (1 + sum(1 for value in null if value >= observed)) / (1 + len(null))
                results.setdefault(level, {})[f"{source}->{target}"] = {
                    "n": len(nets), "net_mean_bps": round(observed, 2),
                    "net_median_bps": round(statistics.median(nets), 2),
                    "median_depth_usd": round(statistics.median(depths_at_entry), 0),
                    "null_p": round(p_value, 4)}
    report = {"status": "development only; recorded window; protocol docs/plan/spillover-study.md",
              "horizon_bars": HORIZONS[-1], "markets": {m: len(rows) for m, rows in sorted(markets.items())},
              "results": results,
              "caveats": ["one venue, one window", "GAS and SPX depth is too thin for capacity",
                          "development only"]}
    OUT.write_text(json.dumps(report, indent=1) + "\n")
    for level, pairs in results.items():
        print(f"level {level}, horizon {HORIZONS[-1]} bars:")
        for pair, stats in sorted(pairs.items(), key=lambda item: -item[1]["net_mean_bps"]):
            print(f"  {pair}: n {stats['n']}, net mean {stats['net_mean_bps']:+.2f} bps, "
                  f"median {stats['net_median_bps']:+.2f}, depth ${stats['median_depth_usd']:,.0f}, p {stats['null_p']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
