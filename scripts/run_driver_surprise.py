#!/usr/bin/env python3
"""Does a quarterly driver's expectation gap predict its own surprise, and its return?

The RPO panel proved the machinery on a concept most issuers do not report. This runs the same
pipeline on the strategy's own drivers, capex and revenue, so the expectation gap covers the
universe the intensity strategy trades. Out-of-sample rows only, corrected disclosure clocks.

    python3 scripts/run_driver_surprise.py --vintages results/revenue-vintages-pit.csv \
        --output results/revenue-surprise.json
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.event_returns import (HORIZONS, attach_returns, blocked_spread_ci,  # noqa: E402
                                             entry_month, group_means, long_short, neutralise, rank_ic)
from filing_specialist.market_state import load_series  # noqa: E402
from repair_unadjusted_bars import suspicious  # noqa: E402

CLOSE_CACHE = ROOT / "results" / "bar-cache"
from filing_specialist.model import chronological_split, fit_and_forecast  # noqa: E402
from filing_specialist.rpo_model import FEATURES, prepare_rows  # noqa: E402

GROUPS = ("datacenter", "equipment", "utility", "contractor")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vintages", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=ROOT / "results" / "bar-cache")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--split", type=float, default=0.7)
    parser.add_argument("--scale", choices=("raw", "zscore"), default="raw",
                        help="zscore reads the standardized surprise and change columns")
    parser.add_argument("--label", default="")
    parser.add_argument("--complex-panel", type=Path,
                        default=ROOT / "results" / "market-panel.json")
    args = parser.parse_args()

    vintages = list(csv.DictReader(args.vintages.open()))
    if args.scale == "zscore":
        rows, drops = prepare_rows(vintages, surprise_column="relative_surprise_z",
                                   change_column="change_relative_z")
    else:
        rows, drops = prepare_rows(vintages)
    dirty = set()
    for ticker in {str(row["ticker"]) for row in rows}:
        series = load_series(ticker, args.cache)
        if series and suspicious({str(day): float(value) for day, value in series.items()}):
            dirty.add(ticker)
    dropped_rows = sum(1 for row in rows if str(row["ticker"]) in dirty)
    if dirty:
        rows = [row for row in rows if str(row["ticker"]) not in dirty]
    train, test = chronological_split(rows, args.split)
    fitted = fit_and_forecast(rows, tuple(FEATURES), fraction=args.split)
    classes = list(fitted["classes"])
    probabilities = fitted["softmax_probabilities"]
    if not (len(test) == len(fitted["test_labels"]) == len(probabilities)):
        raise SystemExit("split and forecast rows disagree")

    cache = {ticker: load_series(ticker, args.cache) for ticker in {str(r["ticker"]) for r in test}}
    coverage = attach_returns(test, cache, HORIZONS)
    for row, values in zip(test, probabilities):
        order = int(values.argmax())
        row["predicted_bin"] = classes[order]
        row["confidence"] = float(values[order])
        row["expected_bin"] = float(sum(k * float(p) for k, p in zip(classes, values)))
        row["entry_month"] = entry_month(row)
        flag = next((g for g in GROUPS if float(row.get(f"group_{g}") or 0.0) >= 0.5), None)
        row["peer_group"] = flag or str(row.get("group_name") or row.get("group") or "").strip() or "other"
    winsor = 0.50
    for horizon in HORIZONS:
        for row in test:
            value = row.get(f"fwd_ret_{horizon}", float("nan"))
            row[f"winsor_{horizon}"] = (float("nan") if value != value
                                        else max(-winsor, min(winsor, value)))
        for variant, keys in (("month_neutral", ("entry_month",)),
                              ("month_group_neutral", ("entry_month", "peer_group"))):
            for row, value in zip(test, neutralise(test, horizon, keys)):
                row[f"{variant}_{horizon}"] = value

    top, bottom = classes[-1], classes[0]
    report = {
        "schema": "driver-surprise-v1", "scope": "development_only",
        "protocol": "docs/plan/driver-surprise.md",
        "vintages": str(args.vintages),
        "panel": {"rows": len(rows), "train_rows": len(train), "test_rows": len(test),
                  "issuers": len({row["ticker"] for row in test}), "drops": drops,
                  "return_coverage": coverage, "series_with_unexplained_drops": sorted(dirty),
                  "rows_dropped_for_dirty_series": dropped_rows},
        "classes": classes,
        "scores": {"prevalence": fitted and None, "log_loss": None},
        "variants": {},
        "ready_for_performance_claim": False,
        "limitations": [
            "development only; the sealed windows are spent",
            "one price source; no borrow, no capacity model",
            "quarterly windows overlap; the traded bins hold few independent issuers",
        ],
    }
    from filing_specialist.model import prevalence, score
    import numpy as np
    labels = np.array([int(row["label_bin"]) for row in test], dtype=int)
    prior = np.tile(prevalence(train, tuple(classes)), (len(labels), 1))
    report["scores"] = {"prevalence": score(prior, labels, tuple(classes)),
                        "softmax": score(probabilities, labels, tuple(classes)),
                        "rows": len(labels)}
    complex_tickers = set()
    if args.complex_panel.exists():
        panel = json.loads(args.complex_panel.read_text())
        complex_tickers = {series["ticker"] for group, payload in panel.get("groups", {}).items()
                           for series in payload.get("series", [])}
    for row in test:
        row["scope"] = "complex" if str(row["ticker"]) in complex_tickers else "rest"
    for variant in ("raw", "winsor", "month_neutral", "month_group_neutral"):
        report["variants"][variant] = {}
        for horizon in HORIZONS:
            key = (f"fwd_ret_{horizon}" if variant == "raw"
                   else f"{variant}_{horizon}")
            report["variants"][variant][str(horizon)] = {
                "by_predicted_bin": group_means(test, "predicted_bin", key),
                "information_coefficient": rank_ic([row["expected_bin"] for row in test],
                                                   [row[key] for row in test]),
                "long_short": [long_short(test, horizon, top, bottom, cost, value_key=key)
                               for cost in (0.0, 20.0)],
                "long_short_interval_20bps": blocked_spread_ci(test, horizon, top, bottom,
                                                               cost_bps=20.0, value_key=key),
                "by_scope": {
                    scope: {
                        "rows": sum(1 for row in test if row["scope"] == scope
                                    and row[key] == row[key]),
                        "long_short": [long_short([row for row in test if row["scope"] == scope],
                                                  horizon, top, bottom, cost, value_key=key)
                                       for cost in (0.0, 20.0)],
                        "long_short_interval_20bps": blocked_spread_ci(
                            [row for row in test if row["scope"] == scope], horizon, top, bottom,
                            cost_bps=20.0, value_key=key),
                    }
                    for scope in ("complex", "rest")
                },
            }
    report["label"] = args.label
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    print(f"--- {args.vintages.name}: rows {len(rows)} | test {len(test)} | issuers {report['panel']['issuers']}"
          f" | coverage {coverage['share']}")
    print(f"   prevalence log loss {report['scores']['prevalence']['log_loss']:.4f} | "
          f"model {report['scores']['softmax']['log_loss']:.4f} | accuracy "
          f"{report['scores']['softmax']['accuracy']:.3f}")
    for variant in ("raw", "winsor", "month_neutral", "month_group_neutral"):
        block = report["variants"][variant]["20"]
        spread = block["long_short"][1]
        interval = block["long_short_interval_20bps"]
        for scope, scoped in block["by_scope"].items():
            scoped_spread = scoped["long_short"][1]
            scoped_interval = scoped["long_short_interval_20bps"]
            print("     20d %-13s %-8s rows %4d spread %s net20 %s CI [%s, %s]" % (
                variant, scope, scoped["rows"],
                f"{scoped_spread['spread']:+.4f}" if scoped_spread.get("spread") is not None else "  n/a ",
                f"{scoped_spread['net']:+.4f}" if scoped_spread.get("net") is not None else "  n/a ",
                f"{scoped_interval['lower']:+.4f}" if scoped_interval.get('lower') is not None else 'n/a',
                f"{scoped_interval['upper']:+.4f}" if scoped_interval.get('upper') is not None else 'n/a'))
        print("   20d %-19s IC %+.4f | spread %+.4f | net(20bps) %+.4f | interval [%s, %s]" % (
            variant, block["information_coefficient"],
            spread.get("spread") if spread.get("spread") is not None else float("nan"),
            spread.get("net") if spread.get("net") is not None else float("nan"),
            f"{interval['lower']:+.4f}" if interval.get("lower") is not None else "n/a",
            f"{interval['upper']:+.4f}" if interval.get("upper") is not None else "n/a"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
