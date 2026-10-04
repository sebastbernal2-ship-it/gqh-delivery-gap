#!/usr/bin/env python3
"""Run the declared compute lead study, exactly as docs/plan/compute-lead-study.md states it.

Development only. The protocol was committed before the capex data was fetched. Tests: the aggregate
cross-family median change against next-quarter provider capex growth, the same per family, and the
same by provider group, with permutation p-values from shuffling the provider-quarter pairing within
each provider.

Writes results/compute-lead-study.json.

    python3 scripts/build_compute_lead_study.py
"""
from __future__ import annotations

import collections
import csv
import json
import random
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRICES = ROOT / "results" / "compute-price-monthly.csv"
CAPEX = ROOT / "results" / "provider-capex-quarterly.csv"
OUT = ROOT / "results" / "compute-lead-study.json"
DRAWS = 5000
SEED = 42
GROUPS = {
    "hyperscalers": ["MSFT", "AMZN", "GOOGL", "META", "ORCL"],
    "hosts": ["CRWV", "IREN", "HUT", "CORZ", "APLD"],
    "reits": ["EQIX", "DLR"],
}


def quarter_of(month: str) -> str:
    year, month_number = month.split("-")
    return f"{year}Q{(int(month_number) - 1) // 3 + 1}"


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


def main() -> int:
    # Feature: quarterly log change per compute family.
    monthly: dict[str, dict[str, list[float]]] = collections.defaultdict(lambda: collections.defaultdict(list))
    for row in csv.DictReader(PRICES.open()):
        try:
            value = float(row["median_usd_per_instance_hour"])
        except (KeyError, ValueError):
            continue
        monthly[row["family"]][row["month"]].append(value)
    family_quarters: dict[str, dict[str, float]] = {}
    for family, months in monthly.items():
        quarter_values: dict[str, list[float]] = collections.defaultdict(list)
        for month, values in months.items():
            quarter_values[quarter_of(month)].extend(values)
        series = {quarter: statistics.median(values) for quarter, values in quarter_values.items()}
        family_quarters[family] = {quarter: (series[quarter] / series[prev] - 1)
                                   for prev, quarter in zip(sorted(series), sorted(series)[1:])
                                   if series[prev] > 0}
    quarters = sorted({quarter for series in family_quarters.values() for quarter in series})
    aggregate = {quarter: statistics.median([series[quarter] for series in family_quarters.values()
                                             if quarter in series]) for quarter in quarters}

    # Outcome: quarterly log growth of provider capex.
    capex: dict[str, dict[str, float]] = collections.defaultdict(dict)
    for row in csv.DictReader(CAPEX.open()):
        try:
            capex[row["ticker"]][quarter_of(row["period_end"][:7])] = float(row["value_usd"])
        except ValueError:
            continue
    capex_growth: dict[str, dict[str, float]] = {}
    for ticker, series in capex.items():
        ordered = sorted(series)
        capex_growth[ticker] = {quarter: (series[quarter] / series[prev] - 1)
                                for prev, quarter in zip(ordered, ordered[1:])
                                if series[prev] > 0}

    def pairs_for(feature: dict[str, float]) -> list[tuple[str, str, float, float]]:
        """(ticker, quarter, feature change, next quarter capex growth)."""
        result = []
        for ticker, growth in capex_growth.items():
            ordered = sorted(feature)
            for quarter in ordered:
                next_quarter = f"{int(quarter[:4]) + (1 if quarter[4:] == 'Q4' else 0)}Q{int(quarter[5]) % 4 + 1}"
                if next_quarter in growth and quarter in feature:
                    result.append((ticker, quarter, feature[quarter], growth[next_quarter]))
        return result

    def test(feature: dict[str, float]) -> dict:
        pairs = pairs_for(feature)
        if len(pairs) < 8:
            return {"n": len(pairs), "rho": None, "p_value": None, "note": "too few pairs"}
        xs = [pair[2] for pair in pairs]
        ys = [pair[3] for pair in pairs]
        observed = spearman(xs, ys)
        by_provider: dict[str, list[int]] = collections.defaultdict(list)
        for position, pair in enumerate(pairs):
            by_provider[pair[0]].append(position)
        random.seed(SEED)
        null = []
        for _ in range(DRAWS):
            shuffled_x = list(xs)
            for positions in by_provider.values():
                values = [xs[position] for position in positions]
                random.shuffle(values)
                for position, value in zip(positions, values):
                    shuffled_x[position] = value
            null.append(spearman(shuffled_x, ys))
        p_value = (1 + sum(1 for value in null if abs(value) >= abs(observed))) / (1 + len(null))
        return {"n": len(pairs), "rho": round(observed, 4), "p_value": round(p_value, 4),
                "null_median": round(statistics.median([value for value in null if value == value]), 4)}

    report = {
        "status": "development only; both sealed windows spent; declared protocol docs/plan/compute-lead-study.md",
        "window": {"compute": f"{min(monthly['g3'])} to {max(monthly['g3'])}",
                   "capex_quarters": len(quarters)},
        "providers": {ticker: len(growth) for ticker, growth in sorted(capex_growth.items())},
        "tests": {},
    }
    report["tests"]["aggregate_cross_family"] = test(aggregate)
    family_tests = {}
    for family, series in sorted(family_quarters.items()):
        result = test(series)
        if result["rho"] is not None:
            family_tests[family] = result
    report["tests"]["families"] = family_tests
    significant = [family for family, result in family_tests.items() if result["p_value"] < 0.05]
    report["tests"]["families_summary"] = {
        "families_tested": len(family_tests),
        "significant_at_5pct": len(significant),
        "expected_under_null": round(0.05 * len(family_tests), 2),
        "names": significant,
        "note": "18 families were permuted; the count of nominal survivors is compared with the null expectation, not read as discovery.",
    }
    for group, tickers in GROUPS.items():
        group_growth = {ticker: capex_growth[ticker] for ticker in tickers if ticker in capex_growth}
        if not group_growth:
            continue
        saved = capex_growth
        capex_growth = group_growth  # noqa: F841 - scoped for the group test
        report["tests"][f"group_{group}"] = test(aggregate)
        capex_growth = saved
    OUT.write_text(json.dumps(report, indent=1) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    for name, result in report["tests"].items():
        if isinstance(result, dict) and "rho" in result:
            print(f"  {name}: n={result['n']} rho={result['rho']} p={result['p_value']}")
    summary = report["tests"].get("families_summary", {})
    print(f"  families: {summary.get('families_tested')} tested; "
          f"{summary.get('significant_at_5pct')} nominal survivors against "
          f"{summary.get('expected_under_null')} expected under the null; "
          f"names {summary.get('names')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
