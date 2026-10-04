#!/usr/bin/env python3
"""Test the provider to family map, family by family, with a placebo contrast.

Protocol: docs/plan/provider-family-tests.md. Development only. Writes
results/provider-family-tests.json.

    python3 scripts/build_provider_family_tests.py
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPUTE = ROOT / "results" / "compute-price-monthly.csv"
REVENUE = ROOT / "results" / "provider-revenue-quarterly.csv"
MAP = ROOT / "docs" / "scan" / "provider-family-map.jsonl"
OUT = ROOT / "results" / "provider-family-tests.json"
OUT_RELATIVE = ROOT / "results" / "provider-family-tests-relative.json"
PREFERRED = "RevenueFromContractWithCustomerExcludingAssessedTax"
MIN_OBS = 10
SHIFTS = 48


def month_index(month: str) -> int:
    return int(month[:4]) * 12 + int(month[5:7]) - 1


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
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["raw", "relative"], default="raw")
    args = parser.parse_args()
    prices: dict[str, dict[int, float]] = collections.defaultdict(dict)
    for row in csv.DictReader(COMPUTE.open()):
        prices[row["family"]][month_index(row["month"])] = float(row["median_usd_per_instance_hour"])
    families = sorted(family for family, series in prices.items() if len(series) >= 24)

    revenue: dict[tuple[str, str], dict] = {}
    for row in csv.DictReader(REVENUE.open()):
        key = (row["ticker"], row["period_end"])
        current = revenue.get(key)
        if current is None or (row["concept"] == PREFERRED and current["concept"] != PREFERRED):
            revenue[key] = row
    by_ticker: dict[str, dict[str, float]] = collections.defaultdict(dict)
    for (ticker, period_end), row in revenue.items():
        by_ticker[ticker][period_end] = float(row["value_usd"])

    mapped: dict[str, list[str]] = {}
    for line in MAP.open():
        if line.strip():
            entry = json.loads(line)
            mapped[entry["provider"]] = entry["families"]

    def median_change(base: int) -> float | None:
        changes = []
        for series in prices.values():
            if base - 2 in series and base in series and series[base - 2] > 0 and series[base] > 0:
                changes.append(math.log(series[base] / series[base - 2]))
        if len(changes) < 3:
            return None
        ordered = sorted(changes)
        middle = len(ordered) // 2
        return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2

    def change(series: dict[int, float], base: int) -> float | None:
        if base - 2 in series and base in series and series[base - 2] > 0 and series[base] > 0:
            raw = math.log(series[base] / series[base - 2])
            if args.mode == "relative":
                market = median_change(base)
                return None if market is None else raw - market
            return raw
        return None

    def pair_for(ticker: str, family: str, shift: int = 0) -> list[tuple[float, float]]:
        pairs = []
        series = prices[family]
        for period_end, value in sorted(by_ticker[ticker].items()):
            if value <= 0:
                continue
            previous = by_ticker[ticker].get(f"{int(period_end[:4]) - 1}{period_end[4:]}")
            if previous is None or previous <= 0:
                continue
            base = month_index(period_end[:7]) - 4 + shift
            moved = change(series, base)
            if moved is not None:
                pairs.append((moved, math.log(value / previous)))
        return pairs

    results = {}
    mapped_rhos, unmapped_rhos = [], []
    for ticker in sorted(by_ticker):
        wanted = set(mapped.get(ticker, []))
        entry = {"mapped_families": sorted(wanted), "pairs": []}
        for family in families + sorted(wanted - set(families)):
            if family not in families:
                entry["pairs"].append({"family": family, "status": "no_series",
                                       "detail": "no rental price series held for this family"})
                continue
            pairs = pair_for(ticker, family)
            if len(pairs) < MIN_OBS:
                entry["pairs"].append({"family": family, "status": "insufficient",
                                       "n": len(pairs), "mapped": family in wanted})
                continue
            observed = spearman([a for a, _ in pairs], [b for _, b in pairs])
            shifts = [spearman([a for a, _ in pair_for(ticker, family, shift)],
                               [b for _, b in pair_for(ticker, family, shift)])
                      for shift in range(1, SHIFTS + 1)]
            shifts = [value for value in shifts if value == value]
            p_value = (1 + sum(1 for value in shifts if value >= observed)) / (1 + len(shifts)) if shifts else None
            record = {"family": family, "status": "tested", "n": len(pairs),
                      "rho": round(observed, 4), "shift_p": round(p_value, 4) if p_value is not None else None,
                      "mapped": family in wanted}
            entry["pairs"].append(record)
            (mapped_rhos if record["mapped"] else unmapped_rhos).append(observed)
        tested = [pair for pair in entry["pairs"] if pair.get("status") == "tested"]
        entry["mapped_mean_rho"] = round(sum(p["rho"] for p in tested if p["mapped"]) /
                                        max(1, sum(1 for p in tested if p["mapped"])), 4)
        entry["unmapped_mean_rho"] = round(sum(p["rho"] for p in tested if not p["mapped"]) /
                                          max(1, sum(1 for p in tested if not p["mapped"])), 4)
        results[ticker] = entry

    survivors_mapped = [pair for entry in results.values() for pair in entry["pairs"]
                        if pair.get("status") == "tested" and pair["mapped"] and pair["shift_p"] is not None
                        and pair["shift_p"] <= 0.05]
    survivors_unmapped = [pair for entry in results.values() for pair in entry["pairs"]
                          if pair.get("status") == "tested" and not pair["mapped"] and pair["shift_p"] is not None
                          and pair["shift_p"] <= 0.05]
    report = {
        "mode": args.mode,
        "status": "development only; both sealed windows spent; protocol docs/plan/provider-family-tests.md",
        "providers": len(results),
        "mapped_pairs": len(mapped_rhos),
        "unmapped_pairs": len(unmapped_rhos),
        "mapped_mean_rho": round(sum(mapped_rhos) / len(mapped_rhos), 4) if mapped_rhos else None,
        "unmapped_mean_rho": round(sum(unmapped_rhos) / len(unmapped_rhos), 4) if unmapped_rhos else None,
        "mapped_positive_share": round(sum(1 for rho in mapped_rhos if rho > 0) / len(mapped_rhos), 3) if mapped_rhos else None,
        "unmapped_positive_share": round(sum(1 for rho in unmapped_rhos if rho > 0) / len(unmapped_rhos), 3) if unmapped_rhos else None,
        "survivors_mapped": [{"pair": f"{ticker}:{pair['family']}", "rho": pair["rho"], "p": pair["shift_p"]}
                             for ticker, entry in results.items() for pair in entry["pairs"]
                             if pair.get("status") == "tested" and pair["mapped"] and pair["shift_p"] is not None
                             and pair["shift_p"] <= 0.05],
        "survivors_unmapped_count": len(survivors_unmapped),
        "results": results,
        "caveats": ["short revenue history", "providers share family series, so counts are descriptive",
                    "EQIX has no rental family series and is recorded as such"],
    }
    (OUT_RELATIVE if args.mode == "relative" else OUT).write_text(json.dumps(report, indent=1) + "\n")
    print(f"providers {len(results)}; mapped pairs {len(mapped_rhos)} mean rho {report['mapped_mean_rho']}")
    print(f"unmapped pairs {len(unmapped_rhos)} mean rho {report['unmapped_mean_rho']}")
    print(f"shift survivors: mapped {len(report['survivors_mapped'])} "
          f"({[s['pair'] for s in report['survivors_mapped']][:6]}), unmapped {len(survivors_unmapped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
