#!/usr/bin/env python3
"""The clock A/B for the intensity strategy: latest-filed panels against earliest-filed panels.

The published panels date every quarter by the latest filing that reported it, a ten-K comparative,
so the median availability lag is 401 days. The corrected panels, same rows and same tickers, date
each quarter by the earliest filing that reported it, a median lag of 34 days. This runs the
declared base configuration on both and reports the difference.

    python3 scripts/run_intensity_pit_clock_test.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from run_intensity_strategy import BASE, load_adv, load_prices, load_signals, run  # noqa: E402

ORIGINAL = {"capex": ROOT / "results" / "complex-capex-quarterly.csv",
            "revenue": ROOT / "results" / "complex-revenue-quarterly.csv"}
CORRECTED = {"capex": ROOT / "results" / "complex-capex-quarterly-pit.csv",
             "revenue": ROOT / "results" / "complex-revenue-quarterly-pit.csv"}


def summarise(result: dict) -> dict:
    return {
        "cohorts": result["cohorts"],
        "annual_return": result["metrics"]["annual_return"],
        "annual_vol": result["metrics"]["annual_vol"],
        "sharpe": result["metrics"]["sharpe"],
        "max_drawdown": result["metrics"]["max_drawdown"],
        "hit_rate": result["metrics"]["hit_rate"],
        "profit_factor": result["metrics"]["profit_factor"],
        "early_annual_return": result["early"]["annual_return"],
        "early_sharpe": result["early"]["sharpe"],
        "late_annual_return": result["late"]["annual_return"],
        "late_sharpe": result["late"]["sharpe"],
        "capacity_1pct_median": result["capacity_1pct_median"],
        "capacity_1pct_p10": result["capacity_1pct_p10"],
        "median_entry_cost_bps": result["entry_cost_bps_median"],
        "window": {"from": result["dates"][0] if result.get("dates") else None},
    }


def main() -> int:
    dates, prices = load_prices()
    adv = load_adv()
    panel = json.loads((ROOT / "results" / "market-panel.json").read_text())
    group_of = {series["ticker"]: group
                for group, payload in panel["groups"].items()
                for series in payload["series"]}
    report = {"schema": "intensity-clock-test-v1", "scope": "development_only",
              "protocol": "docs/plan/intensity-clock-test.md", "runs": {}}
    for label, paths in (("latest_filed", ORIGINAL), ("earliest_filed", CORRECTED)):
        signals = load_signals(paths["capex"], paths["revenue"])
        for cost_label, cost_mult in (("base", 1.0), ("doubled", 2.0)):
            config = {**BASE, "cost_mult": cost_mult, "target_vol": None}
            result = run(config, signals, dates, prices, adv, group_of)
            report["runs"][f"{label}_{cost_label}"] = {
                "config": config, "signals": len(signals),
                "first_filed": min(signal["filed"] for signal in signals),
                "last_filed": max(signal["filed"] for signal in signals),
                **summarise(result),
            }
            print(f"{label:15s} {cost_label:7s} net {result['metrics']['annual_return']*100:+5.2f}% "
                  f"vol {result['metrics']['annual_vol']*100:4.1f}% sharpe {result['metrics']['sharpe']:.3f} "
                  f"maxDD {result['metrics']['max_drawdown']*100:+6.1f}% cohorts {result['cohorts']} "
                  f"capacity1 {result['capacity_1pct_median']:.0f}/{result['capacity_1pct_p10']:.0f}")
    output = ROOT / "results" / "intensity-clock-test.json"
    output.write_text(json.dumps(report, indent=1) + "\n")
    print("written", output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
