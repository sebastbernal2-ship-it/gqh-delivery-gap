#!/usr/bin/env python3
"""Maker entry at the dislocation extreme, paired against the taker entry.

Protocol: docs/plan/maker-entry-study.md. Development only, recorded window. Writes
results/maker-entry-study.json.

    python3 scripts/build_maker_entry_study.py
"""
from __future__ import annotations

import collections
import glob
import json
import math
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from live.hyperliquid import trigger  # noqa: E402

OUT = ROOT / "results" / "maker-entry-study.json"
MAKER_BPS = 1.5
TAKER_BPS = 4.5
HORIZONS = (4, 20, 60)
FILL_WINDOW = 4
MINUTE_BARS = 4
SIGMA_WINDOW = 60
PERCENTILE_WINDOW = 100
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
                    if row.get("best_bid") and row.get("best_ask"):
                        by_market[row["coin"]].append(row)
    for rows in by_market.values():
        rows.sort(key=lambda row: row.get("time") or 0)
    return by_market


def main() -> int:
    markets = load_markets()
    levels = {name: {} for name in ("L1", "L2", "L3", "L6")}
    events: dict[str, dict[str, list[tuple[int, float]]]] = {name: collections.defaultdict(list)
                                                             for name in levels}
    for market, rows in sorted(markets.items()):
        mid = [float(row["mid"]) for row in rows]
        depth = [min(float(row.get("depth_bid_notional") or 0), float(row.get("depth_ask_notional") or 0))
                 for row in rows]
        oi = [float(row.get("open_interest") or 0) for row in rows]
        n = len(rows)
        moves = {i: mid[i] / mid[i - MINUTE_BARS] - 1 for i in range(MINUTE_BARS, n)}
        abs_moves = [abs(value) for value in moves.values()]
        threshold_99 = percentile(abs_moves, 0.99)
        threshold_95 = percentile(abs_moves, 0.95)
        for i in range(MINUTE_BARS, n):
            move = moves[i]
            thin = bool(depth[max(0, i - PERCENTILE_WINDOW):i]) and depth[i] < percentile(
                depth[max(0, i - PERCENTILE_WINDOW):i], 0.2)
            frozen = trigger(mid[:i + 1], oi[:i + 1], window=SIGMA_WINDOW, sigma_multiple=3.0, oi_drop=0.01) \
                if i >= SIGMA_WINDOW + 2 else False
            direction = -1.0 if move > 0 else 1.0
            hits = {"L1": frozen, "L2": abs(move) >= threshold_99, "L3": abs(move) >= threshold_95,
                    "L6": abs(move) >= threshold_99 and thin}
            for name, hit in hits.items():
                if hit:
                    events[name][market].append((i, direction))

    random.seed(SEED)
    for name, store in events.items():
        for horizon in HORIZONS:
            maker_net, taker_net, pair_diff, gone = [], [], [], 0
            fills_hit = fills_miss = 0
            filled_taker, unfilled_taker = [], []
            penetration = {0.0: [0, 0, []], 0.5: [0, 0, []], 1.0: [0, 0, []]}
            for market, hits in store.items():
                rows = markets[market]
                mid = [float(row["mid"]) for row in rows]
                bid = [float(row["best_bid"]) for row in rows]
                ask = [float(row["best_ask"]) for row in rows]
                spread = [float(row.get("spread_bps") or 0) for row in rows]
                for index, direction in hits:
                    if index + horizon >= len(rows):
                        gone += 1
                        continue
                    # Taker baseline, the T20 convention.
                    taker_gross = direction * (mid[index + horizon] / mid[index] - 1) * 1e4
                    taker_cost = 2 * (TAKER_BPS + spread[index] / 2)
                    taker_net.append(taker_gross - taker_cost)
                    # Maker entry: rest at the extreme, exit as a taker at the horizon.
                    if direction > 0:
                        limit = bid[index]
                        fill_index = next((j for j in range(index + 1, min(index + 1 + FILL_WINDOW, len(rows)))
                                           if ask[j] <= limit), None)
                    else:
                        limit = ask[index]
                        fill_index = next((j for j in range(index + 1, min(index + 1 + FILL_WINDOW, len(rows)))
                                           if bid[j] >= limit), None)
                    if fill_index is None or fill_index + horizon >= len(rows):
                        fills_miss += 1
                        unfilled_taker.append(taker_gross - taker_cost)
                        continue
                    fills_hit += 1
                    filled_taker.append(taker_gross - taker_cost)
                    for step in (0.0, 0.5, 1.0):
                        buffer = step * spread[fill_index] / 1e4
                        crossed = (ask[fill_index] <= limit - buffer if direction > 0
                                   else bid[fill_index] >= limit + buffer)
                        if crossed:
                            penetration[step][0] += 1
                            penetration[step][2].append(
                                direction * (mid[fill_index + horizon] / limit - 1) * 1e4
                                - (MAKER_BPS + TAKER_BPS + spread[fill_index + horizon] / 2))
                        else:
                            penetration[step][1] += 1
                    exit_index = fill_index + horizon
                    maker_gross = direction * (mid[exit_index] / limit - 1) * 1e4
                    maker_cost = MAKER_BPS + TAKER_BPS + spread[exit_index] / 2
                    maker_net.append(maker_gross - maker_cost)
                    # Pair against the taker result on the same event and the same horizon end.
                    paired_taker = direction * (mid[exit_index] / mid[index] - 1) * 1e4 - taker_cost
                    pair_diff.append((maker_gross - maker_cost) - paired_taker)
            if not maker_net:
                continue
            # Null: random times, same direction rule and the same maker model.
            null_means = []
            for market, _hits in store.items():
                rows = markets[market]
                if len(rows) <= horizon + FILL_WINDOW + MINUTE_BARS:
                    continue
                mid = [float(row["mid"]) for row in rows]
                bid = [float(row["best_bid"]) for row in rows]
                ask = [float(row["best_ask"]) for row in rows]
                spread = [float(row.get("spread_bps") or 0) for row in rows]
                candidates = list(range(MINUTE_BARS, len(rows) - horizon - FILL_WINDOW - 1))
                count = max(1, len(store[market]))
                total, taken = 0.0, 0
                for _ in range(DRAWS // max(1, len(store))):
                    draws = random.choices(candidates, k=count)
                    for index in draws:
                        move = mid[index] / mid[index - MINUTE_BARS] - 1
                        direction = -1.0 if move > 0 else 1.0
                        if direction > 0:
                            limit = bid[index]
                            fill_index = next((j for j in range(index + 1, min(index + 1 + FILL_WINDOW, len(rows)))
                                               if ask[j] <= limit), None)
                        else:
                            limit = ask[index]
                            fill_index = next((j for j in range(index + 1, min(index + 1 + FILL_WINDOW, len(rows)))
                                               if bid[j] >= limit), None)
                        if fill_index is None or fill_index + horizon >= len(rows):
                            continue
                        exit_index = fill_index + horizon
                        gross = direction * (mid[exit_index] / limit - 1) * 1e4
                        total += gross - (MAKER_BPS + TAKER_BPS + spread[exit_index] / 2)
                        taken += 1
                if taken:
                    null_means.append(total / taken)
            observed = statistics.mean(maker_net)
            p_value = (1 + sum(1 for value in null_means if value >= observed)) / (1 + len(null_means)) \
                if null_means else None
            levels[name][str(horizon)] = {
                "events": len(maker_net) + fills_miss,
                "fills": fills_hit, "fill_rate": round(fills_hit / max(1, fills_hit + fills_miss), 3),
                "maker_net_mean_bps": round(observed, 2),
                "maker_net_median_bps": round(statistics.median(maker_net), 2),
                "taker_net_mean_bps": round(statistics.mean(taker_net), 2) if taker_net else None,
                "paired_difference_bps": round(statistics.mean(pair_diff), 2) if pair_diff else None,
                "null_p": round(p_value, 4) if p_value is not None else None,
                "doubled_cost_maker_bps": round(statistics.mean(
                    [value - (MAKER_BPS + TAKER_BPS) for value in maker_net]), 2),
                "filled_taker_mean_bps": round(statistics.mean(filled_taker), 2) if filled_taker else None,
                "unfilled_taker_mean_bps": round(statistics.mean(unfilled_taker), 2) if unfilled_taker else None,
                "unfilled_share": round(len(unfilled_taker) / max(1, len(filled_taker) + len(unfilled_taker)), 3),
                "penetration": {str(step): {"fills": data[0], "misses": data[1],
                                            "net_mean_bps": round(statistics.mean(data[2]), 2) if data[2] else None}
                                for step, data in penetration.items()},
            }
    report = {
        "status": "development only; recorded window; protocol docs/plan/maker-entry-study.md",
        "markets": {market: len(rows) for market, rows in sorted(markets.items())},
        "levels": {name: {horizon: stats for horizon, stats in levels[name].items()} for name in levels},
        "caveats": ["best bid and ask snapshots at fifteen seconds", "no queue position or partial fills modelled",
                    "maker results are an upper bound"],
    }
    OUT.write_text(json.dumps(report, indent=1) + "\n")
    for name in levels:
        for horizon, stats in levels[name].items():
            print(f"{name} h={horizon}: events {stats['events']} fills {stats['fills']} "
                  f"({stats['fill_rate']:.0%}) maker {stats['maker_net_mean_bps']:+.2f} bps, "
                  f"taker {stats['taker_net_mean_bps']:+.2f}, filled {stats['filled_taker_mean_bps']}, "
                  f"unfilled {stats['unfilled_taker_mean_bps']}, p {stats['null_p']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
