#!/usr/bin/env python3
"""The intensity surprise split by who owns the capital.

Protocol: docs/plan/intensity-segment-study.md. Development only, a declared second look at one dataset.
Writes results/intensity-segment-study.json.

    python3 scripts/build_intensity_segment_study.py
"""
from __future__ import annotations

import collections
import csv
import json
import math
import random
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAPEX = ROOT / "results" / "complex-capex-quarterly.csv"
REVENUE = ROOT / "results" / "complex-revenue-quarterly.csv"
PANEL = ROOT / "results" / "market-panel.json"
CACHE = ROOT / "results" / "bar-cache"
OUT = ROOT / "results" / "intensity-segment-study.json"
PREFERRED = "RevenueFromContractWithCustomerExcludingAssessedTax"
HORIZONS = (5, 20, 60)
DRAWS = 5000
SEED = 42
MIN_NAMES = 4
OWNED = {"hyperscaler", "compute_and_ai", "buildout"}
LEASED = {"data_center_reit", "power", "fuel_and_nuclear"}


def rank(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(order):
        end = index
        while end + 1 < len(order) and values[order[end + 1]] == values[order[index]]:
            end += 1
        average = (index + end) / 2 + 1
        for position in range(index, end + 1):
            ranks[order[position]] = average
        index = end + 1
    return ranks


def spearman(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 4:
        return float("nan")
    rx, ry = rank(xs), rank(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    numerator = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    denominator = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return numerator / denominator if denominator else float("nan")


def month_gap(a: str, b: str) -> int:
    return (int(a[:4]) - int(b[:4])) * 12 + (int(a[5:7]) - int(b[5:7]))


def load_observations() -> list[dict]:
    capex: dict[str, dict[str, dict]] = collections.defaultdict(dict)
    for row in csv.DictReader(CAPEX.open()):
        capex[row["ticker"]][row["period_end"]] = row
    revenue: dict[tuple[str, str], dict] = {}
    for row in csv.DictReader(REVENUE.open()):
        key = (row["ticker"], row["period_end"])
        current = revenue.get(key)
        if current is None or (row["concept"] == PREFERRED and current["concept"] != PREFERRED):
            revenue[key] = row
    revenue_by_ticker: dict[str, dict[str, dict]] = collections.defaultdict(dict)
    for (ticker, period_end), row in revenue.items():
        revenue_by_ticker[ticker][period_end] = row
    groups = json.loads(PANEL.read_text())["groups"]
    group_of = {}
    for group, payload in groups.items():
        for series in payload["series"]:
            group_of.setdefault(series["ticker"], group)
    bars = {}
    for ticker in sorted(set(group_of)):
        path = CACHE / f"{ticker}.json"
        if path.exists():
            bars[ticker] = json.loads(path.read_text())

    observations = []
    for ticker, quarters in sorted(capex.items()):
        if ticker not in bars or ticker not in revenue_by_ticker:
            continue
        for period_end, cap_row in sorted(quarters.items()):
            rev_row = next((candidate for rev_end, candidate in revenue_by_ticker[ticker].items()
                            if abs(month_gap(rev_end, period_end)) <= 20), None)
            if not rev_row or float(rev_row["value_usd"]) <= 0 or float(cap_row["value_usd"]) <= 0:
                continue
            year_ago = f"{int(period_end[:4]) - 1}{period_end[4:]}"
            year_cap = next((candidate for cand_end, candidate in quarters.items()
                             if abs(month_gap(cand_end, year_ago)) <= 1), None)
            year_rev = next((candidate for cand_end, candidate in revenue_by_ticker[ticker].items()
                             if abs(month_gap(cand_end, year_ago)) <= 1), None)
            if not year_cap or not year_rev or float(year_cap["value_usd"]) <= 0 or float(year_rev["value_usd"]) <= 0:
                continue
            intensity = float(cap_row["value_usd"]) / float(rev_row["value_usd"])
            prior = float(year_cap["value_usd"]) / float(year_rev["value_usd"])
            event_date = max(cap_row.get("filed", ""), rev_row.get("filed", ""))
            if intensity <= 0 or prior <= 0 or not event_date:
                continue
            observation = {"ticker": ticker, "period_end": period_end, "quarter": period_end[:7],
                           "event_date": event_date, "group": group_of.get(ticker),
                           "intensity_change": math.log(intensity / prior)}
            series = sorted(bars[ticker])
            start = next((date for date in series if date >= event_date), None)
            if start is None:
                continue
            start_index = series.index(start)
            for horizon in HORIZONS:
                if start_index + horizon >= len(series):
                    continue
                end = series[start_index + horizon]
                own = bars[ticker][end] / bars[ticker][start] - 1
                peer_returns = []
                for member in groups[observation["group"]]["series"]:
                    member = member["ticker"]
                    if member == ticker or member not in bars:
                        continue
                    member_series = sorted(bars[member])
                    member_start = next((date for date in member_series if date >= event_date), None)
                    if member_start is None:
                        continue
                    member_index = member_series.index(member_start)
                    if member_index + horizon >= len(member_series):
                        continue
                    peer_returns.append(bars[member][member_series[member_index + horizon]]
                                        / bars[member][member_start] - 1)
                if len(peer_returns) >= 2:
                    observation[f"excess_{horizon}"] = own - statistics.mean(peer_returns)
            observations.append(observation)
    return observations


def segment_test(rows: list[dict], key: str, seed: int) -> dict:
    by_quarter: dict[str, list[tuple[float, float]]] = collections.defaultdict(list)
    for row in rows:
        if key in row:
            by_quarter[row["quarter"]].append((row["intensity_change"], row[key]))
    quarters = [(quarter, pairs) for quarter, pairs in by_quarter.items() if len(pairs) >= MIN_NAMES]
    if not quarters:
        return {"n": 0, "status": "insufficient"}
    values = []
    for _, pairs in quarters:
        value = spearman([a for a, _ in pairs], [b for _, b in pairs])
        if value == value:
            values.append((value, len(pairs)))
    if not values:
        return {"n": 0, "status": "insufficient"}
    weight = sum(count for _, count in values)
    observed = sum(value * count for value, count in values) / weight
    random.seed(seed)
    null = []
    for _ in range(DRAWS):
        draws = []
        for _, pairs in quarters:
            xs = [a for a, _ in pairs]
            ys = [b for _, b in pairs]
            random.shuffle(xs)
            value = spearman(xs, ys)
            if value == value:
                draws.append((value, len(pairs)))
        if draws:
            total = sum(count for _, count in draws)
            null.append(sum(value * count for value, count in draws) / total)
    upper = (1 + sum(1 for value in null if value >= observed)) / (1 + len(null))
    lower = (1 + sum(1 for value in null if value <= observed)) / (1 + len(null))
    ordered = sorted([(row["intensity_change"], row[key]) for row in rows if key in row])
    third = max(1, len(ordered) // 3)
    bottom = statistics.mean([value for _, value in ordered[:third]])
    top = statistics.mean([value for _, value in ordered[-third:]])
    names = len({row["ticker"] for row in rows if key in row})
    return {"n": len([row for row in rows if key in row]), "names": names, "quarters": len(quarters),
            "mean_within_quarter_rho": round(observed, 4),
            "two_sided_permutation_p": round(min(1.0, 2 * min(upper, lower)), 4),
            "tercile_spread": round(top - bottom, 4)}


def main() -> int:
    observations = load_observations()
    report = {"status": "development only; declared second look at one dataset; protocol docs/plan/intensity-segment-study.md",
              "observations": len(observations), "segments": {}}
    for segment, groups in (("owned_capital", OWNED), ("leased_or_regulated", LEASED)):
        rows = [row for row in observations if row["group"] in groups]
        report["segments"][segment] = {"groups": sorted(groups), "names": len({row["ticker"] for row in rows}),
                                       "horizons": {}}
        for horizon in HORIZONS:
            key = f"excess_{horizon}"
            report["segments"][segment]["horizons"][str(horizon)] = segment_test(rows, key, SEED + horizon)
    OUT.write_text(json.dumps(report, indent=1) + "\n")
    print(f"observations {len(observations)}")
    for segment, block in report["segments"].items():
        print(f"{segment}: {block['names']} names")
        for horizon, stats in block["horizons"].items():
            if stats.get("status") == "insufficient":
                print(f"  h={horizon}: insufficient")
            else:
                print(f"  h={horizon}: n {stats['n']}, names {stats['names']}, rho {stats['mean_within_quarter_rho']:+.3f} "
                      f"(p {stats['two_sided_permutation_p']}), tercile {stats['tercile_spread']:+.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
