#!/usr/bin/env python3
"""Does the published infrastructure phase state improve the two-sleeve portfolio as a size overlay?

Aidan's regime audit publishes a monthly phase (results/regime-state-daily.csv, owned by that
workstream) and proposes the safe seam: a size multiplier from zero to one applied after the strategy
has chosen its portfolio, with proposed and adjusted weights kept for attribution. This test is
strictly a development measurement of that seam.

Protocol, declared before the run:
  attribution   the composite's annualised net, volatility, Sharpe and drawdown inside each phase
  selection     the losing phase is chosen on the FIRST half of the window only
  evaluation    a 0.5 multiplier is applied in that phase on the SECOND half only
  decision      month-blocked interval on the daily difference between overlaid and raw
The published caveat travels with any result: the phase labels are not prefix invariant (two to four
labels move when the cutoff moves), so this cannot be a trading input without a refit rule.

    python3 scripts/run_regime_overlay_test.py
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.portfolio_stats import month_blocked_interval, portfolio_metrics  # noqa: E402
from run_three_sleeve_portfolio import apply_vol_target  # noqa: E402

SPLIT = "2023-01-01"


def phase_by_month(path: Path) -> dict[str, str]:
    return {row["month"]: row["phase"] for row in csv.DictReader(path.open())}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--states", type=Path, default=ROOT / "results" / "regime-state-daily.csv")
    parser.add_argument("--baseline", type=Path, default=ROOT / "results" / "walk-forward-baseline.json")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "regime-overlay.json")
    args = parser.parse_args()

    phases = phase_by_month(args.states)
    daily = json.loads(args.baseline.read_text())["portfolio_daily"]["without_capex_inverse_vol"]
    for row in daily:
        row["phase"] = phases.get(row["date"][:7], "unknown")

    attribution = {}
    for name in sorted({row["phase"] for row in daily}):
        subset = [row for row in daily if row["phase"] == name]
        attribution[name] = {"days": len(subset), "metrics": portfolio_metrics(subset)}

    first = [row for row in daily if row["date"] < SPLIT]
    second = [row for row in daily if row["date"] >= SPLIT]
    first_by_phase = {}
    for name in sorted({row["phase"] for row in first}):
        subset = [row for row in first if row["phase"] == name]
        if len(subset) >= 60:
            first_by_phase[name] = portfolio_metrics(subset)["sharpe"]
    losing = min(first_by_phase, key=first_by_phase.get) if first_by_phase else None

    MULTIPLIER = 0.5
    overlaid = [{**row, "net": row["net"] * (MULTIPLIER if row["phase"] == losing else 1.0)}
                for row in second]
    raw_second = [row for row in second]
    comparison = {
        "chosen_on_first_half": losing,
        "first_half_sharpe_by_phase": {name: round(value, 3) for name, value in first_by_phase.items()},
        "second_half_raw": portfolio_metrics(raw_second),
        "second_half_overlaid": portfolio_metrics(overlaid),
        "second_half_vol_targeted_raw": portfolio_metrics(apply_vol_target(raw_second, 0.10)),
        "second_half_vol_targeted_overlaid": portfolio_metrics(apply_vol_target(overlaid, 0.10)),
        "interval_overlaid_minus_raw": month_blocked_interval(overlaid, raw_second),
        "multiplier": MULTIPLIER,
    }
    report = {"schema": "regime-overlay-v1", "scope": "development_only",
              "protocol": "docs/plan/open-work.md", "states": str(args.states),
              "window": {"from": daily[0]["date"], "to": daily[-1]["date"], "split": SPLIT},
              "attribution": attribution, "comparison": comparison,
              "caveat": "the published phases are not prefix invariant (2 to 4 labels move with the "
                        "cutoff), so this is a seam test, not a trading rule",
              "ready_for_performance_claim": False}
    args.output.write_text(json.dumps(report, indent=1) + "\n")

    print("phase attribution, whole window (annualised net, Sharpe, DD):")
    for name, block in attribution.items():
        metrics = block["metrics"]
        print("  %-10s days %4d net %+7.2f%% sharpe %+6.3f dd %+6.1f%%" % (
            name, block["days"], metrics["annual_return"] * 100, metrics["sharpe"],
            metrics["max_drawdown"] * 100))
    print("losing phase chosen on the first half:", losing)
    raw, over = comparison["second_half_raw"], comparison["second_half_overlaid"]
    print("second half raw     : net %+7.2f%% sharpe %+6.3f dd %+6.1f%%" % (
        raw["annual_return"] * 100, raw["sharpe"], raw["max_drawdown"] * 100))
    print("second half overlaid: net %+7.2f%% sharpe %+6.3f dd %+6.1f%%" % (
        over["annual_return"] * 100, over["sharpe"], over["max_drawdown"] * 100))
    interval = comparison["interval_overlaid_minus_raw"]
    print("overlaid minus raw: point %+.4f CI [%+.4f, %+.4f] share+ %.3f months %s" % (
        interval["point"], interval["lower"], interval["upper"], interval["share_positive"],
        interval.get("months")))
    print("written", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
