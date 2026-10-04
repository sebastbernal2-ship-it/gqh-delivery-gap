#!/usr/bin/env python3
"""Provider capex intensity and the capex to revenue gap.

Protocol: docs/plan/capex-revenue-gap.md. Development only. Writes results/capex-revenue-gap.json.

    python3 scripts/build_capex_revenue_gap.py
"""
from __future__ import annotations

import collections
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAPEX = ROOT / "results" / "provider-capex-quarterly.csv"
REVENUE = ROOT / "results" / "provider-revenue-quarterly.csv"
OUT = ROOT / "results" / "capex-revenue-gap.json"
PREFERRED = "RevenueFromContractWithCustomerExcludingAssessedTax"
SHIFTS = 36


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


def autocorr(values: list[float]) -> float:
    if len(values) < 3:
        return float("nan")
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values)
    if variance == 0:
        return float("nan")
    return sum((values[i] - mean) * (values[i + 1] - mean) for i in range(len(values) - 1)) / variance


def main() -> int:
    capex: dict[str, dict[str, float]] = collections.defaultdict(dict)
    for row in csv.DictReader(CAPEX.open()):
        capex[row["ticker"]][row["period_end"]] = float(row["value_usd"])
    revenue_rows: dict[tuple[str, str], dict] = {}
    for row in csv.DictReader(REVENUE.open()):
        key = (row["ticker"], row["period_end"])
        current = revenue_rows.get(key)
        if current is None or (row["concept"] == PREFERRED and current["concept"] != PREFERRED):
            revenue_rows[key] = row
    revenue: dict[str, dict[str, float]] = collections.defaultdict(dict)
    for (ticker, period_end), row in revenue_rows.items():
        revenue[ticker][period_end] = float(row["value_usd"])

    def aligned(ticker: str) -> list[tuple[str, float, float]]:
        pairs = []
        for period_end, cap in sorted(capex[ticker].items()):
            for rev_end, rev in revenue[ticker].items():
                if rev > 0 and abs(month_gap(rev_end, period_end)) <= 20:
                    pairs.append((period_end, cap, rev))
                    break
        return pairs

    def month_gap(a: str, b: str) -> int:
        return (int(a[:4]) - int(b[:4])) * 12 + (int(a[5:7]) - int(b[5:7]))

    per_provider = {}
    pooled_intensity, pooled_gap = [], []
    lead_pairs = []
    for ticker in sorted(set(capex) & set(revenue)):
        pairs = aligned(ticker)
        if len(pairs) < 6:
            per_provider[ticker] = {"quarters": len(pairs), "status": "insufficient"}
            continue
        intensity = [cap / rev for _, cap, rev in pairs]
        trend_rho = spearman(list(range(len(intensity))), intensity)
        growth_gaps = []
        for index in range(len(pairs)):
            year_ago = None
            for other in pairs:
                if abs(month_gap(other[0], pairs[index][0]) - 12) <= 1:
                    year_ago = other
                    break
            if year_ago and year_ago[1] > 0 and year_ago[2] > 0:
                cap_growth = math.log(pairs[index][1] / year_ago[1])
                rev_growth = math.log(pairs[index][2] / year_ago[2])
                growth_gaps.append((pairs[index][0], cap_growth, rev_growth))
        gap_values = [cap_growth - rev_growth for _, cap_growth, rev_growth in growth_gaps]
        for index in range(len(growth_gaps) - 1):
            lead_pairs.append((growth_gaps[index][1], growth_gaps[index + 1][2]))
        pooled_intensity.extend(intensity)
        pooled_gap.extend(gap_values)
        per_provider[ticker] = {
            "quarters": len(pairs),
            "status": "tested",
            "intensity_mean": round(sum(intensity) / len(intensity), 3),
            "intensity_last": round(intensity[-1], 3),
            "intensity_trend_rho": round(trend_rho, 3),
            "gap_mean": round(sum(gap_values) / len(gap_values), 3) if gap_values else None,
            "gap_autocorr": round(autocorr(gap_values), 3) if len(gap_values) >= 3 else None,
        }
    lead_rho = spearman([a for a, _ in lead_pairs], [b for _, b in lead_pairs])
    shifts = []
    xs_all = [a for a, _ in lead_pairs]
    for shift in range(1, min(SHIFTS, max(1, len(xs_all) - 3)) + 1):
        shifted = xs_all[shift:] + xs_all[:shift]
        shifts.append(spearman(shifted, [b for _, b in lead_pairs]))
    shifts = [value for value in shifts if value == value]
    p_value = (1 + sum(1 for value in shifts if value >= lead_rho)) / (1 + len(shifts)) if shifts else None
    report = {
        "status": "development only; both sealed windows spent; protocol docs/plan/capex-revenue-gap.md",
        "providers": per_provider,
        "pooled_intensity_mean": round(sum(pooled_intensity) / len(pooled_intensity), 3) if pooled_intensity else None,
        "pooled_gap_mean": round(sum(pooled_gap) / len(pooled_gap), 3) if pooled_gap else None,
        "pooled_gap_autocorr": round(autocorr(pooled_gap), 3) if len(pooled_gap) >= 3 else None,
        "capex_leads_revenue_rho": round(lead_rho, 4),
        "capex_leads_revenue_p": round(p_value, 4) if p_value is not None else None,
        "lead_observations": len(lead_pairs),
        "caveats": ["ten providers", "capex concepts differ across filers", "development only"],
    }
    OUT.write_text(json.dumps(report, indent=1) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"pooled intensity mean {report['pooled_intensity_mean']}, gap mean {report['pooled_gap_mean']}, "
          f"gap autocorr {report['pooled_gap_autocorr']}")
    print(f"capex leads revenue rho {report['capex_leads_revenue_rho']} (p {report['capex_leads_revenue_p']}, "
          f"n {report['lead_observations']})")
    for ticker, entry in per_provider.items():
        if entry.get("status") == "tested":
            print(f"  {ticker}: intensity {entry['intensity_mean']} (last {entry['intensity_last']}), "
                  f"trend {entry['intensity_trend_rho']}, gap {entry['gap_mean']}, autocorr {entry['gap_autocorr']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
