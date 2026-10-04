#!/usr/bin/env python3
"""Stage 2: score the broad RPO panel and check the per-event edge at breadth.

The panel is 11,031 measured events across 929 issuers, built from cached XBRL frames with accession
acceptance clocks. The falsifier of this stage is that breadth degrades the per-event edge beyond its
interval, so the same long-short measurement is repeated here, with a declared coverage report for
the price data.

    python3 scripts/run_universe_surprise.py
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.event_returns import (HORIZONS, attach_returns, blocked_spread_ci,  # noqa: E402
                                             entry_month, group_means, long_short, neutralise, rank_ic)
from filing_specialist.market_state import load_series  # noqa: E402
from filing_specialist.model import (chronological_split, fit_and_forecast, prevalence,  # noqa: E402
                                     score)
from filing_specialist.rpo_model import FEATURES, prepare_rows  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vintages", type=Path,
                        default=ROOT / "results" / "rpo-universe-vintages.csv")
    parser.add_argument("--cache", type=Path, default=ROOT / "results" / "bar-cache")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results" / "rpo-universe-scores.json")
    parser.add_argument("--split", type=float, default=0.7)
    args = parser.parse_args()

    rows, drops = prepare_rows(list(csv.DictReader(args.vintages.open())))
    train, test = chronological_split(rows, args.split)
    fitted = fit_and_forecast(rows, tuple(FEATURES), fraction=args.split)
    classes = list(fitted["classes"])
    probabilities = fitted["softmax_probabilities"]
    if not (len(test) == len(fitted["test_labels"]) == len(probabilities)):
        raise SystemExit("the split and the forecast rows disagree")

    labels = np.array([int(row["label_bin"]) for row in test], dtype=int)
    prior = np.tile(prevalence(train, tuple(classes)), (len(labels), 1))
    scores = {"prevalence": score(prior, labels, tuple(classes)),
              "softmax": score(probabilities, labels, tuple(classes)), "rows": len(labels),
              "issuers": len({row["ticker"] for row in test})}

    cache = {ticker: load_series(ticker, args.cache) for ticker in {str(r["ticker"]) for r in test}}
    coverage = attach_returns(test, cache, HORIZONS)
    for row, values in zip(test, probabilities):
        order = int(values.argmax())
        row["predicted_bin"] = classes[order]
        row["confidence"] = float(values[order])
        row["expected_bin"] = float(sum(k * float(p) for k, p in zip(classes, values)))
        row["entry_month"] = entry_month(row)
    for horizon in HORIZONS:
        for row, value in zip(test, neutralise(test, horizon, ("entry_month",))):
            row[f"month_neutral_{horizon}"] = value

    top, bottom = classes[-1], classes[0]
    report = {
        "schema": "rpo-universe-scores-v1", "scope": "development_only",
        "protocol": "docs/plan/alpha-build.md",
        "panel": {"rows": len(rows), "train_rows": len(train), "test_rows": len(test),
                  "issuers": len({row["ticker"] for row in rows}), "drops": drops,
                  "return_coverage": coverage},
        "scores": scores, "variants": {}, "ready_for_performance_claim": False,
        "limitations": [
            "development only; the sealed windows are spent",
            "price coverage is thin: most broad-universe filers have no cached bars",
            "no borrow cost, no capacity model, no sector neutralisation (groups are empty here)",
            "frame coverage starts in 2018 for most filers, so the panel is shorter than the frames",
        ],
    }
    for variant in ("raw", "month_neutral"):
        report["variants"][variant] = {}
        for horizon in HORIZONS:
            key = f"fwd_ret_{horizon}" if variant == "raw" else f"month_neutral_{horizon}"
            report["variants"][variant][str(horizon)] = {
                "information_coefficient": rank_ic([row["expected_bin"] for row in test],
                                                   [row[key] for row in test]),
                "long_short": [long_short(test, horizon, top, bottom, cost, value_key=key)
                               for cost in (0.0, 20.0)],
                "long_short_interval_20bps": blocked_spread_ci(test, horizon, top, bottom,
                                                               cost_bps=20.0, value_key=key),
                "by_predicted_bin": group_means(test, "predicted_bin", key),
            }
    args.output.write_text(json.dumps(report, indent=1) + "\n")

    print(f"panel {len(rows)} rows | train {len(train)} | test {len(test)} | issuers {report['panel']['issuers']}")
    print(f"log loss: prevalence {scores['prevalence']['log_loss']:.4f} | model {scores['softmax']['log_loss']:.4f} "
          f"| accuracy {scores['softmax']['accuracy']:.3f} vs {scores['prevalence']['accuracy']:.3f}")
    print(f"return coverage {coverage['share']} ({coverage['rows_with_the_longest_horizon']} of {coverage['rows']})")
    for variant in ("raw", "month_neutral"):
        for horizon in ("1", "5", "20"):
            block = report["variants"][variant][horizon]
            spread = block["long_short"][1]
            interval = block["long_short_interval_20bps"]
            print("  %-13s h%-3s IC %+.4f | n %4d/%-4d | spread %s | net20 %s | CI [%s, %s]" % (
                variant, horizon, block["information_coefficient"],
                spread["n_long"], spread["n_short"],
                f"{spread['spread']:+.4f}" if spread["spread"] is not None else "  n/a ",
                f"{spread['net']:+.4f}" if spread["net"] is not None else "  n/a ",
                f"{interval['lower']:+.4f}" if interval.get("lower") is not None else "n/a",
                f"{interval['upper']:+.4f}" if interval.get("upper") is not None else "n/a"))
    print("written", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
