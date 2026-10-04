#!/usr/bin/env python3
"""The capex intensity surprise as a cross-sectional factor across the complex.

Protocol: docs/plan/intensity-factor-study.md. Development only. Writes
results/intensity-factor-study.json.

    python3 scripts/build_intensity_factor_study.py
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
OUT = ROOT / "results" / "intensity-factor-study.json"
PREFERRED = "RevenueFromContractWithCustomerExcludingAssessedTax"
HORIZONS = (5, 20, 60)
DRAWS = 5000
SEED = 42
MIN_QUARTER_NAMES = 5


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


def main() -> int:
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
    group_of, group_members = {}, {}
    for group, payload in groups.items():
        members = [series["ticker"] for series in payload["series"]]
        group_members[group] = members
        for ticker in members:
            group_of.setdefault(ticker, group)
    bars: dict[str, dict[str, float]] = {}
    for ticker in sorted(set(group_of)):
        path = CACHE / f"{ticker}.json"
        if path.exists():
            bars[ticker] = json.loads(path.read_text())
    complex_members = sorted(bars)

    observations = []
    for ticker, quarters in sorted(capex.items()):
        if ticker not in bars or ticker not in revenue_by_ticker:
            continue
        for period_end, cap_row in sorted(quarters.items()):
            rev_row = None
            for rev_end, candidate in revenue_by_ticker[ticker].items():
                if abs(month_gap(rev_end, period_end)) <= 20:
                    rev_row = candidate
                    break
            if not rev_row or float(rev_row["value_usd"]) <= 0 or float(cap_row["value_usd"]) <= 0:
                continue
            year_ago = f"{int(period_end[:4]) - 1}{period_end[4:]}"
            year_cap = next((candidate for cand_end, candidate in quarters.items()
                             if abs(month_gap(cand_end, year_ago)) <= 1), None)
            year_rev = next((candidate for cand_end, candidate in revenue_by_ticker[ticker].items()
                             if abs(month_gap(cand_end, year_ago)) <= 1), None)
            if not year_cap or not year_rev:
                continue
            if float(year_cap["value_usd"]) <= 0 or float(year_rev["value_usd"]) <= 0:
                continue
            intensity = float(cap_row["value_usd"]) / float(rev_row["value_usd"])
            prior = float(year_cap["value_usd"]) / float(year_rev["value_usd"])
            event_date = max(cap_row.get("filed", ""), rev_row.get("filed", ""))
            if intensity <= 0 or prior <= 0 or not event_date:
                continue
            observations.append({"ticker": ticker, "period_end": period_end, "event_date": event_date,
                                 "quarter": period_end[:7], "group": group_of.get(ticker),
                                 "intensity_change": math.log(intensity / prior)})

    for observation in observations:
        ticker = observation["ticker"]
        series = sorted(bars[ticker])
        start = next((date for date in series if date >= observation["event_date"]), None)
        if start is None:
            continue
        start_index = series.index(start)
        for horizon in HORIZONS:
            if start_index + horizon >= len(series):
                continue
            end = series[start_index + horizon]
            own_return = bars[ticker][end] / bars[ticker][start] - 1
            group_returns, complex_returns = [], []
            for member in group_members.get(observation["group"], []):
                if member == ticker or member not in bars:
                    continue
                member_series = sorted(bars[member])
                member_start = next((date for date in member_series if date >= observation["event_date"]), None)
                if member_start is None:
                    continue
                member_index = member_series.index(member_start)
                if member_index + horizon >= len(member_series):
                    continue
                group_returns.append(bars[member][member_series[member_index + horizon]] / bars[member][member_start] - 1)
            for member in complex_members:
                if member == ticker or member not in bars:
                    continue
                member_series = sorted(bars[member])
                member_start = next((date for date in member_series if date >= observation["event_date"]), None)
                if member_start is None:
                    continue
                member_index = member_series.index(member_start)
                if member_index + horizon >= len(member_series):
                    continue
                complex_returns.append(bars[member][member_series[member_index + horizon]] / bars[member][member_start] - 1)
            if len(group_returns) >= 2:
                observation[f"excess_group_{horizon}"] = own_return - statistics.mean(group_returns)
            if len(complex_returns) >= 5:
                observation[f"excess_complex_{horizon}"] = own_return - statistics.mean(complex_returns)

    usable = [observation for observation in observations
              if any(f"excess_complex_{horizon}" in observation for horizon in HORIZONS)]

    def within_quarter(rows: list[dict], key: str) -> tuple[float, int, dict[str, float]]:
        by_quarter: dict[str, list[tuple[float, float]]] = collections.defaultdict(list)
        for row in rows:
            if key in row:
                by_quarter[row["quarter"]].append((row["intensity_change"], row[key]))
        rhos, weights, per_group = {}, 0, collections.defaultdict(list)
        values = []
        for quarter, pairs in sorted(by_quarter.items()):
            if len(pairs) < MIN_QUARTER_NAMES:
                continue
            value = spearman([a for a, _ in pairs], [b for _, b in pairs])
            if value != value:
                continue
            values.append((value, len(pairs)))
            for row in rows:
                if row["quarter"] == quarter and key in row:
                    per_group[row["group"]].append((row["intensity_change"], row[key]))
        if not values:
            return float("nan"), 0, {}
        weight = sum(count for _, count in values)
        return sum(value * count for value, count in values) / weight, weight, {
            group: round(spearman([a for a, _ in pairs], [b for _, b in pairs]), 3)
            for group, pairs in per_group.items() if len(pairs) >= MIN_QUARTER_NAMES}

    random.seed(SEED)
    report = {"status": "development only; both sealed windows spent; protocol docs/plan/intensity-factor-study.md",
              "observations": len(usable), "names": len({o["ticker"] for o in usable}), "horizons": {}}
    for horizon in HORIZONS:
        block = {}
        for benchmark in ("complex", "group"):
            key = f"excess_{benchmark}_{horizon}"
            rows = [row for row in usable if key in row]
            if len(rows) < 10:
                block[benchmark] = {"n": len(rows), "status": "insufficient"}
                continue
            mean_rho, weight, per_group = within_quarter(rows, key)
            pooled = spearman([row["intensity_change"] for row in rows], [row[key] for row in rows])
            by_quarter: dict[str, list[tuple[float, float]]] = collections.defaultdict(list)
            for row in rows:
                by_quarter[row["quarter"]].append((row["intensity_change"], row[key]))
            quarters = [(quarter, pairs) for quarter, pairs in by_quarter.items() if len(pairs) >= MIN_QUARTER_NAMES]
            null = []
            for _ in range(DRAWS):
                values = []
                for _, pairs in quarters:
                    xs = [a for a, _ in pairs]
                    ys = [b for _, b in pairs]
                    random.shuffle(xs)
                    value = spearman(xs, ys)
                    if value == value:
                        values.append((value, len(pairs)))
                if values:
                    total = sum(count for _, count in values)
                    null.append(sum(value * count for value, count in values) / total)
            observed_value = mean_rho
            upper = (1 + sum(1 for value in null if value >= observed_value)) / (1 + len(null)) if null else None
            lower = (1 + sum(1 for value in null if value <= observed_value)) / (1 + len(null)) if null else None
            two_sided = min(1.0, 2 * min(upper, lower)) if upper is not None and lower is not None else None
            ordered = sorted(rows, key=lambda row: row["intensity_change"])
            third = max(1, len(ordered) // 3)
            bottom = statistics.mean([row[key] for row in ordered[:third]])
            top = statistics.mean([row[key] for row in ordered[-third:]])
            block[benchmark] = {"n": len(rows), "quarters": len(quarters),
                                "mean_within_quarter_rho": round(mean_rho, 4),
                                "pooled_rho": round(pooled, 4),
                                "two_sided_permutation_p": round(two_sided, 4) if two_sided is not None else None,
                                "bottom_third_mean": round(bottom, 4), "top_third_mean": round(top, 4),
                                "tercile_spread": round(top - bottom, 4), "per_group_rho": per_group}
        report["horizons"][str(horizon)] = block
    report["caveats"] = ["quarterly fundamentals against daily prices", "overlapping windows",
                         "one free price source", "development only"]
    OUT.write_text(json.dumps(report, indent=1) + "\n")
    print(f"observations {len(usable)} across {report['names']} names")
    for horizon, block in report["horizons"].items():
        for benchmark, stats in block.items():
            if stats.get("status") == "insufficient":
                print(f"h={horizon} {benchmark}: insufficient ({stats['n']})")
            else:
                print(f"h={horizon} {benchmark}: n {stats['n']}, quarters {stats['quarters']}, "
                      f"within-quarter rho {stats['mean_within_quarter_rho']:+.3f} "
                      f"(p {stats['two_sided_permutation_p']}), pooled {stats['pooled_rho']:+.3f}, "
                      f"tercile spread {stats['tercile_spread']:+.3f}")
                if stats["per_group_rho"]:
                    print(f"    per group: {stats['per_group_rho']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
