#!/usr/bin/env python3
"""Does the equity market price the capex intensity rise?

Protocol: docs/plan/intensity-pricing-study.md. Development only. Reads the reviewed bar cache and the
XBRL panels. Writes results/intensity-pricing-study.json.

    python3 scripts/build_intensity_pricing_study.py
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
CAPEX = ROOT / "results" / "provider-capex-quarterly.csv"
REVENUE = ROOT / "results" / "provider-revenue-quarterly.csv"
PANEL = ROOT / "results" / "market-panel.json"
CACHE = ROOT / "results" / "bar-cache"
OUT = ROOT / "results" / "intensity-pricing-study.json"
PREFERRED = "RevenueFromContractWithCustomerExcludingAssessedTax"
HORIZONS = (5, 20, 60)
DRAWS = 5000
SEED = 42


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

    groups = json.loads((ROOT / "results" / "market-panel.json").read_text())["groups"]
    group_of = {}
    group_tickers = {}
    for group, payload in groups.items():
        tickers = [series["ticker"] for series in payload["series"]]
        group_tickers[group] = tickers
        for ticker in tickers:
            group_of[ticker] = group

    bars: dict[str, dict[str, float]] = {}
    for ticker in sorted(set(group_of)):
        path = CACHE / f"{ticker}.json"
        if path.exists():
            bars[ticker] = json.loads(path.read_text())
    def forward(date: str, horizon: int) -> float | None:
        return None

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
            year_ago_cap = year_ago_rev = None
            year_ago = f"{int(period_end[:4]) - 1}{period_end[4:]}"
            for cand_end, candidate in quarters.items():
                if abs(month_gap(cand_end, year_ago)) <= 1:
                    year_ago_cap = candidate
                    break
            for cand_end, candidate in revenue_by_ticker[ticker].items():
                if abs(month_gap(cand_end, year_ago)) <= 1:
                    year_ago_rev = candidate
                    break
            if not year_ago_cap or not year_ago_rev:
                continue
            if float(year_ago_cap["value_usd"]) <= 0 or float(year_ago_rev["value_usd"]) <= 0:
                continue
            intensity = float(cap_row["value_usd"]) / float(rev_row["value_usd"])
            prior_intensity = float(year_ago_cap["value_usd"]) / float(year_ago_rev["value_usd"])
            if intensity <= 0 or prior_intensity <= 0:
                continue
            event_date = max(cap_row.get("filed", ""), rev_row.get("filed", ""))
            if not event_date:
                continue
            observations.append({"ticker": ticker, "period_end": period_end, "event_date": event_date,
                                 "intensity_change": math.log(intensity / prior_intensity),
                                 "group": group_of.get(ticker)})
    # Forward excess returns per horizon.
    for observation in observations:
        ticker, group = observation["ticker"], observation["group"]
        series = sorted(bars.get(ticker, {}))
        start = next((date for date in series if date >= observation["event_date"]), None)
        if start is None:
            continue
        start_index = series.index(start)
        for horizon in HORIZONS:
            if start_index + horizon >= len(series):
                continue
            end = series[start_index + horizon]
            ticker_return = bars[ticker][end] / bars[ticker][start] - 1
            peer_returns = []
            for peer in group_tickers.get(group, []):
                peer_series = bars.get(peer)
                if not peer_series:
                    continue
                peer_start = next((date for date in sorted(peer_series) if date >= observation["event_date"]), None)
                if peer_start is None:
                    continue
                peer_sorted = sorted(peer_series)
                peer_index = peer_sorted.index(peer_start)
                if peer_index + horizon >= len(peer_sorted):
                    continue
                peer_end = peer_sorted[peer_index + horizon]
                peer_returns.append(peer_series[peer_end] / peer_series[peer_start] - 1)
            if len(peer_returns) < 2:
                continue
            observation[f"excess_{horizon}"] = ticker_return - statistics.mean(peer_returns)
        observation["start_date"] = start
    usable = [observation for observation in observations if any(f"excess_{h}" in observation for h in HORIZONS)]

    random.seed(SEED)
    report = {"status": "development only; both sealed windows spent; protocol docs/plan/intensity-pricing-study.md",
              "observations": len(usable), "providers": sorted({o["ticker"] for o in usable}),
              "horizons": {}}
    for horizon in HORIZONS:
        pairs = [(o["intensity_change"], o[f"excess_{horizon}"]) for o in usable if f"excess_{horizon}" in o]
        if len(pairs) < 6:
            report["horizons"][str(horizon)] = {"n": len(pairs), "status": "insufficient"}
            continue
        observed = spearman([a for a, _ in pairs], [b for _, b in pairs])
        null = []
        xs = [a for a, _ in pairs]
        ys = [b for _, b in pairs]
        for _ in range(DRAWS):
            shuffled = list(xs)
            random.shuffle(shuffled)
            value = spearman(shuffled, ys)
            if value == value:
                null.append(value)
        upper = (1 + sum(1 for value in null if value >= observed)) / (1 + len(null))
        lower = (1 + sum(1 for value in null if value <= observed)) / (1 + len(null))
        p_value = min(1.0, 2 * min(upper, lower))
        ordered = sorted(pairs)
        third = max(1, len(ordered) // 3)
        bottom = statistics.mean([value for _, value in ordered[:third]])
        top = statistics.mean([value for _, value in ordered[-third:]])
        per_provider = {}
        for ticker in sorted({o["ticker"] for o in usable}):
            subset = [o[f"excess_{horizon}"] for o in usable
                      if o["ticker"] == ticker and f"excess_{horizon}" in o]
            if subset:
                per_provider[ticker] = {"n": len(subset), "mean_excess": round(statistics.mean(subset), 4)}
        report["horizons"][str(horizon)] = {
            "n": len(pairs), "rho": round(observed, 4),
            "two_sided_permutation_p": round(p_value, 4), "upper_tail_p": round(upper, 4),
            "bottom_third_mean_excess": round(bottom, 4), "top_third_mean_excess": round(top, 4),
            "tercile_spread": round(top - bottom, 4), "per_provider": per_provider}
    report["sample"] = [{"ticker": o["ticker"], "period_end": o["period_end"], "event_date": o["event_date"],
                         "intensity_change": round(o["intensity_change"], 3)} for o in usable[:40]]
    report["caveats"] = ["six providers, short panels", "overlapping return windows",
                         "one free price source", "development only"]
    OUT.write_text(json.dumps(report, indent=1) + "\n")
    print(f"observations {len(usable)} across {len(report['providers'])} providers")
    for horizon in HORIZONS:
        stats = report["horizons"][str(horizon)]
        print(f"h={horizon}: {stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
