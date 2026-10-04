#!/usr/bin/env python3
"""Matched-universe test: the same names across eras, so composition and era can be told apart.

The question this answers: is the recent record the mechanism, or the fact that the recent cross
section is the AI buildout? Two arms on one name set.

1. **Matched names, extended origins.** Only companies whose prices reach back before 2017, with
   origins from 2011, so every block trades the same names.
2. **Recent era, matched against full.** The same recent window run on the matched names and on the
   full complex, which isolates the composition effect directly.

Costs are flat twenty basis points on the sleeve: volume does not exist before 2017, and pretending
otherwise would be the silent change this test exists to avoid.

    python3 scripts/run_matched_universe.py
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
from filing_specialist.portfolio_stats import (month_blocked_interval,  # noqa: E402
                                               portfolio_metrics)
from run_sleeve_portfolio import COSTS, sleeve_daily  # noqa: E402
from run_walk_forward import ORIGINS, sleeve_walk_forward  # noqa: E402

EXTENDED = ("2011-01-01", "2012-01-01", "2013-01-01", "2014-01-01", "2015-01-01", "2016-01-01",
            "2017-01-01", "2018-01-01", "2019-01-01", "2020-01-01", "2021-01-01", "2022-01-01",
            "2023-01-01", "2024-01-01", "2025-01-01", "2026-01-01")
ERAS = (("2011-2014", "2011-01-01", "2015-01-01"), ("2015-2018", "2015-01-01", "2019-01-01"),
        ("2019-2022", "2019-01-01", "2023-01-01"), ("2023-2026", "2023-01-01", "2030-01-01"))
PANEL = ROOT / "results" / "revenue-vintages-pit.csv"


def matched_tickers(cache: Path, cutoff: str = "2017-01-01") -> set[str]:
    """Complex operating companies whose price series begin before the cutoff."""
    panel = json.loads((ROOT / "results" / "market-panel.json").read_text())
    companies = {series["ticker"] for group, payload in panel.get("groups", {}).items()
                 for series in payload.get("series", [])
                 if not series["ticker"].startswith("^") and "=" not in series["ticker"]}
    matched = set()
    for path in cache.glob("*.json"):
        if path.stem not in companies:
            continue
        try:
            days = sorted(json.loads(path.read_text()))
        except (OSError, ValueError):
            continue
        if days and days[0] < cutoff:
            matched.add(path.stem)
    return matched


def era_metrics(daily: list[dict]) -> dict:
    out = {}
    for name, start, end in ERAS:
        rows = [row for row in daily if start <= row["date"] < end]
        if len(rows) < 60:
            out[name] = {"days": len(rows)}
            continue
        out[name] = {"days": len(rows), **portfolio_metrics(rows)}
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / "results" / "bar-cache")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "matched-universe.json")
    args = parser.parse_args()

    matched = matched_tickers(args.cache)
    report = {"schema": "matched-universe-v1", "scope": "development_only",
              "protocol": "docs/plan/alpha-build.md", "matched_names": sorted(matched),
              "cost_basis": "flat 20 basis points; volume does not exist before 2017",
              "ready_for_performance_claim": False,
              "limitations": [
                  "development only; both sealed windows are spent",
                  "pre-2017 the cross section is rates and utilities, so the matched set still differs "
                  "in composition from the recent one, only the names are constant",
                  "the revenue sleeve only; the intensity sleeve's signals begin in 2017",
              ]}

    events, _, digests = sleeve_walk_forward(PANEL, 1.0, tickers=matched, origins=EXTENDED)
    daily, info = sleeve_daily(events, args.cache, COSTS["base"])
    report["matched_extended"] = {"events": len(events), "origins": list(EXTENDED),
                                  "training_rows_by_origin": digests,
                                  "metrics": portfolio_metrics(daily), "eras": era_metrics(daily)}

    full_events, _, _ = sleeve_walk_forward(PANEL, 1.0, origins=ORIGINS)
    full_daily, _ = sleeve_daily(full_events, args.cache, COSTS["base"])
    matched_recent = [row for row in daily if row["date"] >= "2019-01-01"]
    full_recent = [row for row in full_daily if row["date"] >= "2019-01-01"]
    report["recent_era"] = {
        "matched": {"days": len(matched_recent), "metrics": portfolio_metrics(matched_recent)},
        "full": {"days": len(full_recent), "metrics": portfolio_metrics(full_recent)},
        "difference_interval": month_blocked_interval(matched_recent, full_recent),
    }
    args.output.write_text(json.dumps(report, indent=1) + "\n")

    print(f"matched names: {len(matched)} of the complex companies")
    stitched = report["matched_extended"]["metrics"]
    print("  matched, extended origins: days %d net %+.2f%% vol %.1f%% sharpe %+.3f maxDD %+.1f%%" % (
        stitched["days"], stitched["annual_return"] * 100, stitched["annual_vol"] * 100,
        stitched["sharpe"] or float("nan"), stitched["max_drawdown"] * 100))
    print("  era            days   net      vol     sharpe   maxDD")
    for name, block in report["matched_extended"]["eras"].items():
        if block.get("sharpe") is None and "annual_return" not in block:
            print("    %-12s %4d  (too few sessions)" % (name, block.get("days", 0)))
            continue
        print("    %-12s %4d %+7.2f%% %6.1f%% %+7.3f %+7.1f%%" % (
            name, block["days"], block["annual_return"] * 100, block["annual_vol"] * 100,
            block["sharpe"] or float("nan"), block["max_drawdown"] * 100))
    recent = report["recent_era"]
    print("  recent era on matched names: net %+.2f%% sharpe %+.3f | on the full complex: net %+.2f%% sharpe %+.3f" % (
        recent["matched"]["metrics"]["annual_return"] * 100, recent["matched"]["metrics"]["sharpe"] or float("nan"),
        recent["full"]["metrics"]["annual_return"] * 100, recent["full"]["metrics"]["sharpe"] or float("nan")))
    print("  matched minus full, recent era:", json.dumps(recent["difference_interval"]))
    print("written", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
