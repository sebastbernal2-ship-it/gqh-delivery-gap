#!/usr/bin/env python3
"""Forced flow reversion at zero latency advantage, on the recorded tape.

Protocol: docs/plan/cascade-reversion-study.md. Levels, entry, costs and null are declared there.
Development only. Writes results/cascade-reversion-study.json.

    python3 scripts/build_cascade_reversion_study.py
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
OUT = ROOT / "results" / "cascade-reversion-study.json"
TAKER_BPS = 4.5
HORIZONS = (4, 20, 60)
DRAWS = 5000
SEED = 42
SIGMA_WINDOW = 60
MINUTE_BARS = 4
PERCENTILE_WINDOW = 100


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
    levels: dict[str, dict] = {name: {"events": 0, "per_market": collections.Counter(), "results": {}}
                               for name in ("L1", "L2", "L3", "L4", "L5", "L6")}
    event_store: dict[str, dict[str, list[tuple[str, int, float]]]] = {name: collections.defaultdict(list)
                                                                      for name in levels}
    for market, rows in sorted(markets.items()):
        mid = [float(row["mid"]) for row in rows]
        spread = [float(row.get("spread_bps") or 0) for row in rows]
        depth = [min(float(row.get("depth_bid_notional") or 0), float(row.get("depth_ask_notional") or 0))
                 for row in rows]
        funding = [float(row.get("funding") or 0) for row in rows]
        oi = [float(row.get("open_interest") or 0) for row in rows]
        n = len(rows)
        steps = [mid[i] / mid[i - 1] - 1 for i in range(1, n)]
        minute_moves = {i: mid[i] / mid[i - MINUTE_BARS] - 1 for i in range(MINUTE_BARS, n)}
        abs_minute = [abs(value) for value in minute_moves.values()]
        threshold_99 = percentile(abs_minute, 0.99)
        threshold_95 = percentile(abs_minute, 0.95)
        for i in range(MINUTE_BARS, n):
            move = minute_moves[i]
            m1_hit = abs(move) >= threshold_99
            m1_loose = abs(move) >= threshold_95
            # L1 is the frozen rule itself, taken from the live module rather than reimplemented.
            frozen = trigger(mid[:i + 1], oi[:i + 1], window=SIGMA_WINDOW, sigma_multiple=3.0, oi_drop=0.01)
            funding_window = funding[max(0, i - PERCENTILE_WINDOW):i]
            fz = None
            if len(funding_window) > 20 and statistics.pstdev(funding_window) > 0:
                fz = (funding[i] - statistics.mean(funding_window)) / statistics.pstdev(funding_window)
            depth_window = depth[max(0, i - PERCENTILE_WINDOW):i]
            thin = bool(depth_window) and depth[i] < percentile(depth_window, 0.2)
            direction = -1.0 if move > 0 else 1.0
            hits = {"L1": frozen, "L2": m1_hit, "L3": m1_loose,
                    "L4": fz is not None and abs(fz) > 2.0,
                    "L5": thin, "L6": m1_hit and thin}
            for name, hit in hits.items():
                if hit:
                    if name == "L4":
                        entry_direction = -1.0 if fz > 0 else 1.0
                    else:
                        entry_direction = direction
                    levels[name]["events"] += 1
                    levels[name]["per_market"][market] += 1
                    event_store[name][market].append((market, i, entry_direction))
    # Results per level and horizon, with the random-time null.
    random.seed(SEED)
    for name, store in event_store.items():
        if levels[name]["events"] == 0:
            continue
        for horizon in HORIZONS:
            pooled_gross, pooled_net, costs, depths, per_market_means = [], [], [], [], {}
            for market, events in store.items():
                rows = markets[market]
                mid = [float(row["mid"]) for row in rows]
                spread = [float(row.get("spread_bps") or 0) for row in rows]
                depth = [min(float(row.get("depth_bid_notional") or 0), float(row.get("depth_ask_notional") or 0))
                         for row in rows]
                market_gross = []
                for _, index, direction in events:
                    if index + horizon >= len(rows):
                        continue
                    gross = direction * (mid[index + horizon] / mid[index] - 1) * 1e4
                    cost = 2 * (TAKER_BPS + spread[index] / 2)
                    pooled_gross.append(gross)
                    pooled_net.append(gross - cost)
                    costs.append(cost)
                    depths.append(depth[index])
                    market_gross.append(gross)
                if market_gross:
                    per_market_means[market] = round(statistics.mean(market_gross), 2)
            if not pooled_net:
                continue
            # Null: random entry times with the same direction rule, same horizon accounting.
            null_means = []
            for market, events in store.items():
                rows = markets[market]
                n_rows = len(rows)
                if n_rows <= horizon + MINUTE_BARS:
                    continue
                mid = [float(row["mid"]) for row in rows]
                spread = [float(row.get("spread_bps") or 0) for row in rows]
                candidates = list(range(MINUTE_BARS, n_rows - horizon))
                for _ in range(DRAWS // max(1, len(store))):
                    draws = random.choices(candidates, k=max(1, len(events)))
                    total = 0.0
                    for index in draws:
                        move = mid[index] / mid[index - MINUTE_BARS] - 1
                        direction = -1.0 if move > 0 else 1.0
                        gross = direction * (mid[index + horizon] / mid[index] - 1) * 1e4
                        cost = 2 * (TAKER_BPS + spread[index] / 2)
                        total += gross - cost
                    null_means.append(total / len(draws))
            observed_mean = statistics.mean(pooled_net)
            p_value = (1 + sum(1 for value in null_means if value >= observed_mean)) / (1 + len(null_means)) \
                if null_means else None
            levels[name]["results"][str(horizon)] = {
                "n": len(pooled_net),
                "gross_mean_bps": round(statistics.mean(pooled_gross), 2),
                "gross_median_bps": round(statistics.median(pooled_gross), 2),
                "net_mean_bps": round(observed_mean, 2),
                "net_median_bps": round(statistics.median(pooled_net), 2),
                "cost_mean_bps": round(statistics.mean(costs), 2),
                "doubled_cost_net_mean_bps": round(statistics.mean(
                    [gross - 2 * cost for gross, cost in zip(pooled_gross, costs)]), 2),
                "median_depth_usd": round(statistics.median(depths), 0),
                "per_market_gross_mean_bps": per_market_means,
                "null_p": round(p_value, 4) if p_value is not None else None,
            }
    report = {
        "status": "development only; recorded window, not a backtest; protocol docs/plan/cascade-reversion-study.md",
        "markets": {market: len(rows) for market, rows in sorted(markets.items())},
        "levels": {name: {"events": levels[name]["events"],
                          "per_market": dict(levels[name]["per_market"]),
                          "results": levels[name]["results"]} for name in levels},
        "costs": {"taker_bps_per_side": TAKER_BPS, "spread_charged": "half spread per side, measured at entry",
                  "doubled": "reported per horizon as doubled_cost_net_mean_bps"},
        "caveats": ["one recorded window, four markets, one venue", "entry at the condition bar close, no speed used",
                    "a positive level here is a candidate, not an edge"],
    }
    OUT.write_text(json.dumps(report, indent=1) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    for name in levels:
        count = levels[name]["events"]
        print(f"{name}: {count} events, per market {dict(levels[name]['per_market'])}")
        for horizon, stats in levels[name]["results"].items():
            print(f"  h={horizon}: n {stats['n']}, net mean {stats['net_mean_bps']:+.2f} bps "
                  f"(gross {stats['gross_mean_bps']:+.2f}), doubled {stats['doubled_cost_net_mean_bps']:+.2f}, "
                  f"p {stats['null_p']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
