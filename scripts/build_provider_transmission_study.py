#!/usr/bin/env python3
"""Test the weak link inside the provider family: does the compute rental change reach provider revenue?

Protocol: docs/plan/provider-transmission-study.md. Development only. Writes
results/provider-transmission-study.json.

    python3 scripts/build_provider_transmission_study.py
"""
from __future__ import annotations

import collections
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPUTE = ROOT / "results" / "compute-price-monthly.csv"
REVENUE = ROOT / "results" / "provider-revenue-quarterly.csv"
OUT = ROOT / "results" / "provider-transmission-study.json"
PREFERRED = "RevenueFromContractWithCustomerExcludingAssessedTax"


def month_index(month: str) -> int:
    return int(month[:4]) * 12 + int(month[5:7]) - 1


def month_label(index: int) -> str:
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


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
    if len(xs) < 3:
        return float("nan")
    rx, ry = rank(xs), rank(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    numerator = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    denominator = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return numerator / denominator if denominator else float("nan")


def main() -> int:
    prices: dict[str, dict[int, float]] = collections.defaultdict(dict)
    for row in csv.DictReader(COMPUTE.open()):
        prices[row["family"]][month_index(row["month"])] = float(row["median_usd_per_instance_hour"])

    def aggregate_change(end_index: int) -> float | None:
        changes = []
        for family, series in prices.items():
            if end_index - 2 in series and end_index in series and series[end_index - 2] > 0:
                changes.append(math.log(series[end_index] / series[end_index - 2]))
        return statistics_median(changes) if len(changes) >= 3 else None

    def statistics_median(values: list[float]) -> float:
        ordered = sorted(values)
        middle = len(ordered) // 2
        return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2

    revenue: dict[tuple[str, str], dict] = {}
    for row in csv.DictReader(REVENUE.open()):
        key = (row["ticker"], row["period_end"])
        current = revenue.get(key)
        if current is None or (row["concept"] == PREFERRED and current["concept"] != PREFERRED):
            revenue[key] = row
    by_ticker: dict[str, dict[str, float]] = collections.defaultdict(dict)
    for (ticker, period_end), row in revenue.items():
        by_ticker[ticker][period_end] = float(row["value_usd"])

    panel = []
    for ticker, series in sorted(by_ticker.items()):
        for period_end, value in sorted(series.items()):
            if value <= 0:
                continue
            previous = series.get(f"{int(period_end[:4]) - 1}{period_end[4:]}")
            if previous is None or previous <= 0:
                continue
            end_month = month_index(period_end[:7])
            lagged = aggregate_change(end_month - 4)
            forward = aggregate_change(end_month + 2)
            if lagged is None:
                continue
            panel.append({"ticker": ticker, "period_end": period_end,
                          "yoy_growth": math.log(value / previous), "lagged_change": lagged,
                          "forward_change": forward})
    observed = spearman([row["lagged_change"] for row in panel],
                        [row["yoy_growth"] for row in panel])
    forward_pairs = [row for row in panel if row["forward_change"] is not None]
    reverse = spearman([row["forward_change"] for row in forward_pairs],
                       [row["yoy_growth"] for row in forward_pairs])

    shifts = []
    for shift in range(1, 61):
        xs, ys = [], []
        for row in panel:
            end_month = month_index(row["period_end"][:7])
            shifted = aggregate_change(end_month - 4 + shift)
            if shifted is not None:
                xs.append(shifted)
                ys.append(row["yoy_growth"])
        if len(xs) >= 10:
            shifts.append(spearman(xs, ys))
    p_value = (1 + sum(1 for value in shifts if value >= observed)) / (1 + len(shifts))

    family_rhos = {}
    for family, series in prices.items():
        if len(series) < 24:
            continue
        xs, ys = [], []
        for row in panel:
            end_month = month_index(row["period_end"][:7])
            base = end_month - 4
            if base - 2 in series and base in series and series[base] > 0:
                xs.append(math.log(series[base] / series[base - 2]))
                ys.append(row["yoy_growth"])
        if len(xs) >= 10:
            family_rhos[family] = round(spearman(xs, ys), 3)

    report = {
        "status": "development only; both sealed windows spent; protocol docs/plan/provider-transmission-study.md",
        "providers": sorted(by_ticker),
        "observations": len(panel),
        "lagged_rho": round(observed, 4),
        "shift_null_p": round(p_value, 4),
        "shift_null_median": round(statistics_median(shifts), 4) if shifts else None,
        "reverse_control_rho": round(reverse, 4),
        "reverse_observations": len(forward_pairs),
        "family_rhos": dict(sorted(family_rhos.items(), key=lambda item: -item[1])),
        "caveats": ["ten providers, short revenue history", "aggregate rental change is a median across families",
                    "development only, this does not open a sealed window"],
    }
    OUT.write_text(json.dumps(report, indent=1) + "\n")
    print(f"observations {len(panel)} across {len(by_ticker)} providers")
    print(f"lagged rho {observed:+.4f} (shift null p {p_value:.4f}, null median {report['shift_null_median']})")
    print(f"reverse control rho {reverse:+.4f} on {len(forward_pairs)} observations")
    print("family rhos:", json.dumps(report["family_rhos"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
