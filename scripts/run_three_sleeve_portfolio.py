#!/usr/bin/env python3
"""Three sleeves in one portfolio: revenue surprise, capex surprise, and the gated intensity charge.

The two expectation-gap sleeves and the charge expression read different objects: what the issuer
disclosed, and how hard it is spending against what it earns. If their daily returns are not
correlated, holding all three raises the risk-adjusted result without needing a better signal.

Weights are equal gross by default, with an inverse-volatility variant over trailing 60 sessions.
Every sleeve keeps its own events and its own clock; only the daily return series are combined.

    python3 scripts/run_three_sleeve_portfolio.py
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
import numpy as np  # noqa: E402
from filing_specialist.portfolio_stats import month_blocked_interval, portfolio_metrics  # noqa: E402
from run_intensity_gate_test import CORRECTED, VINTAGES, gate_for, surprises  # noqa: E402
from run_intensity_strategy import BASE, load_adv, load_prices, load_signals, run  # noqa: E402
from run_sleeve_portfolio import (COSTS, apply_vol_target, capacity_report,  # noqa: E402
                                  sleeve_daily, sleeve_events)

COMPLEX = ROOT / "results" / "market-panel.json"


def gated_intensity_daily(cost_mult: float, split: float) -> tuple[list[dict], dict]:
    dates, prices = load_prices()
    adv = load_adv()
    panel = json.loads(COMPLEX.read_text())
    group_of = {series["ticker"]: group for group, payload in panel["groups"].items()
                for series in payload["series"]}
    signals = load_signals(CORRECTED["capex"], CORRECTED["revenue"])
    revenue, revenue_split = surprises(VINTAGES["revenue"], split)
    capex, _ = surprises(VINTAGES["capex"], split)
    window_start = max(revenue_split["test_from"], VINTAGES["capex"] and
                       surprises(VINTAGES["capex"], split)[1]["test_from"])[:10]
    window = [date for date in dates if date >= window_start]
    gate = gate_for(revenue, signals, centre=2.0)
    result = run({**BASE, "cost_mult": cost_mult, "target_vol": None}, signals, window, prices, adv,
                 group_of, gate=gate)
    return [{"date": row["date"], "net": row["net"], "gross": row["gross"]} for row in result["daily"]], {
        "window_from": window_start, "cohorts": result["cohorts"], "events": len(gate),
        "gate_coverage": len(gate) / max(1, len(signals))}


def align(series_list: list[list[dict]]) -> tuple[list[str], list[list[float]]]:
    calendars = [{row["date"] for row in series} for series in series_list]
    common = sorted(set.intersection(*calendars))
    values = []
    for series in series_list:
        lookup = {row["date"]: row["net"] for row in series}
        values.append([lookup[date] for date in common])
    return common, values


def weighted_daily(dates: list[str], values: list[list[float]], weights: list[list[float]]) -> list[dict]:
    rows = []
    for position, date in enumerate(dates):
        total = sum(weight[position] for weight in weights)
        gross = sum(weight[position] * value[position] for weight, value in zip(weights, values))
        rows.append({"date": date, "net": gross / total if total else 0.0,
                     "gross": gross / total if total else 0.0})
    return rows


def inverse_vol_weights(values: list[list[float]], window: int = 60) -> list[list[float]]:
    count = len(values)
    length = len(values[0])
    weights = [[0.0] * length for _ in range(count)]
    for position in range(length):
        inverses = []
        for sleeve in range(count):
            start = max(0, position - window)
            history = values[sleeve][start:position]
            deviation = statistics.pstdev(history) if len(history) > 5 else 0.0
            inverses.append(1.0 / deviation if deviation > 1e-9 else 0.0)
        total = sum(inverses)
        if total <= 1e-12:
            inverses, total = [1.0] * count, float(count)   # no volatility yet means equal weights
        for sleeve in range(count):
            weights[sleeve][position] = inverses[sleeve] / total
    return weights


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revenue", type=Path, default=ROOT / "results" / "revenue-vintages-pit.csv")
    parser.add_argument("--capex", type=Path, default=ROOT / "results" / "capex-vintages-pit.csv")
    parser.add_argument("--cache", type=Path, default=ROOT / "results" / "bar-cache")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "three-sleeve-portfolio.json")
    parser.add_argument("--split", type=float, default=0.7)
    args = parser.parse_args()

    report = {"schema": "three-sleeve-portfolio-v1", "scope": "development_only",
              "protocol": "docs/plan/alpha-build.md", "sleeves": {}, "portfolios": {},
              "ready_for_performance_claim": False,
              "limitations": [
                  "development only; both sealed windows are spent",
                  "complex names only; the two expectation sleeves are frozen out-of-sample models",
                  "flat costs; capacity from 60-session median dollar volume",
                  "the sleeves' calendars differ, so the combined window is their intersection",
              ]}
    series = {}
    for name, path, direction in (("revenue", args.revenue, 1.0), ("capex", args.capex, -1.0)):
        events = sleeve_events(path, direction=direction, split=args.split)
        daily, info = sleeve_daily(events, args.cache, COSTS["base"])
        series[name] = daily
        report["sleeves"][name] = {"events": info, "metrics": portfolio_metrics(daily),
                                   "capacity": capacity_report(events)}
    intensity_base, intensity_info = gated_intensity_daily(COSTS["base"] / 20.0, args.split)
    report["sleeves"]["intensity_gated"] = {"events": intensity_info,
                                            "metrics": portfolio_metrics(intensity_base)}
    series["intensity_gated"] = intensity_base

    dates, values = align([series["revenue"], series["capex"], series["intensity_gated"]])
    names = ["revenue", "capex", "intensity_gated"]
    equal = [[1 / 3] * len(dates) for _ in names]
    inverse = inverse_vol_weights(values)
    report["common_window"] = {"from": dates[0], "to": dates[-1], "sessions": len(dates)}
    report["correlations"] = {}
    for left in range(len(names)):
        for right in range(left + 1, len(names)):
            pair = np.corrcoef(values[left], values[right])[0, 1]
            report["correlations"][f"{names[left]}|{names[right]}"] = float(pair)
    for label, weights in (("equal_gross", equal), ("inverse_vol", inverse)):
        combined = weighted_daily(dates, values, weights)
        report["portfolios"][label] = {"metrics": portfolio_metrics(combined),
                                       "weights_mean": [round(statistics.mean(w), 3) for w in weights]}
        report["portfolios"][label + "_vol_target"] = {
            "metrics": portfolio_metrics(apply_vol_target(combined, 0.10))}
        if label == "equal_gross":
            best_sleeve = max(names, key=lambda name: portfolio_metrics(series[name])["sharpe"] or -9)
            report["best_sleeve"] = best_sleeve
            best_daily = [{"date": date, "net": value}
                          for date, value in zip(dates, values[names.index(best_sleeve)])]
            two_sleeve = weighted_daily(dates, values, [[0.5] * len(dates), [0.5] * len(dates),
                                                        [0.0] * len(dates)])
            report["intervals"] = {
                "three_sleeve_minus_best_sleeve": month_blocked_interval(combined, best_daily),
                "three_sleeve_minus_two_sleeve": month_blocked_interval(combined, two_sleeve),
            }
    args.output.write_text(json.dumps(report, indent=1) + "\n")

    print("sleeve metrics (own calendar)")
    for name in names:
        m = report["sleeves"][name]["metrics"]
        print("  %-16s days %4d net %+7.2f%% vol %6.1f%% sharpe %+6.3f maxDD %+7.1f%%" % (
            name, m["days"], m["annual_return"] * 100, m["annual_vol"] * 100,
            m["sharpe"] or float("nan"), m["max_drawdown"] * 100))
    print("common window", report["common_window"], "correlations:",
          json.dumps(report["correlations"], indent=0))
    for label in ("equal_gross", "inverse_vol"):
        m = report["portfolios"][label]["metrics"]
        v = report["portfolios"][label + "_vol_target"]["metrics"]
        print("  %-14s net %+7.2f%% vol %6.1f%% sharpe %+6.3f maxDD %+7.1f%% | vol-targeted net %+7.2f%% vol %6.1f%% sharpe %+6.3f maxDD %+7.1f%%" % (
            label, m["annual_return"] * 100, m["annual_vol"] * 100, m["sharpe"] or float("nan"),
            m["max_drawdown"] * 100, v["annual_return"] * 100, v["annual_vol"] * 100,
            v["sharpe"] or float("nan"), v["max_drawdown"] * 100))
    print("best sleeve", report["best_sleeve"], "intervals:", json.dumps(report["intervals"], indent=0))
    print("written", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
