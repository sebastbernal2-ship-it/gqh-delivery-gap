#!/usr/bin/env python3
"""Calibration of the surviving sleeve models, and the tails of the sleeve return series.

Two questions the architecture document requires and nobody had answered:

1. Are the probabilities honest? Out-of-sample predictions from the revenue model are pooled across
   the rolling origins, then binned into a reliability table with an expected calibration error, a
   maximum error, a resampled interval, and an extreme-bin check.
2. How bad are the tails? The stitched walk-forward series of the revenue sleeve, the gated intensity
   sleeve and their combination get value at risk, expected shortfall and the worst rolling window.

    python3 scripts/run_calibration_report.py
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
from filing_specialist.calibration_diagnostics import (bootstrap_ece, expected_calibration_error,  # noqa: E402
                                                       extreme_bin_check, maximum_calibration_error,
                                                       reliability, tail_statistics)
from filing_specialist.rpo_model import prepare_rows  # noqa: E402
from run_sleeve_portfolio import COSTS, apply_vol_target as sleeve_vol_target, sleeve_daily  # noqa: E402
from run_three_sleeve_portfolio import align, inverse_vol_weights, weighted_daily  # noqa: E402
from run_walk_forward import blocks, fit_at, intensity_walk_forward, sleeve_walk_forward  # noqa: E402


def pooled_predictions(panel: Path) -> tuple[list[list[float]], list[int], list[int]]:
    """Out-of-sample probabilities and labels pooled across the rolling origins."""
    rows, _ = prepare_rows(list(csv.DictReader(panel.open())))
    probabilities, labels, classes = [], [], None
    for start, end in blocks():
        fitted = fit_at(rows, start)
        if fitted["probabilities"] is None:
            continue
        classes = list(fitted["classes"])
        for row, values in zip(fitted["later"], fitted["probabilities"]):
            decision = str(row["label_available"])[:10]
            if start <= decision < end:
                probabilities.append([float(p) for p in values])
                labels.append(int(row["label_bin"]))
    return probabilities, labels, classes or []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revenue", type=Path, default=ROOT / "results" / "revenue-vintages-pit.csv")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results" / "calibration-report.json")
    args = parser.parse_args()

    probabilities, labels, classes = pooled_predictions(args.revenue)
    position = {value: index for index, value in enumerate(classes)}
    confidences = [max(row) for row in probabilities]
    correct = [1 if classes[row.index(max(row))] == label else 0
               for row, label in zip(probabilities, labels)]
    table = reliability(confidences, correct, bins=10)
    report = {
        "schema": "calibration-report-v1", "scope": "development_only",
        "protocol": "docs/plan/open-work.md",
        "model": {"panel": str(args.revenue), "rows": len(probabilities),
                  "classes": classes, "distinct_confidences": len({round(value, 4) for value in confidences})},
        "reliability": table,
        "expected_calibration_error": expected_calibration_error(table),
        "maximum_calibration_error": maximum_calibration_error(table),
        "expected_calibration_error_interval": bootstrap_ece(confidences, correct, resamples=1000),
        "extreme_bins": extreme_bin_check(probabilities, labels, tuple(classes)),
        "sharpness": statistics.mean(confidences),
        "ready_for_performance_claim": False,
        "limitations": [
            "development only; the revenue panel is the surviving sleeve's model",
            "pooled across rolling origins, so blocks are not independent",
            "bins are coarse with five classes and a few hundred rows per block",
        ],
    }

    revenue_events, _, _ = sleeve_walk_forward(args.revenue, 1.0)
    revenue_daily, _ = sleeve_daily(revenue_events, ROOT / "results" / "bar-cache", COSTS["base"])
    intensity, _ = intensity_walk_forward(1.0)
    intensity_daily = [{"date": row["date"], "net": row["net"]} for row in intensity]
    dates, values = align([revenue_daily, intensity_daily])
    weights = inverse_vol_weights(values)
    combined = weighted_daily(dates, values, weights)
    report["tails"] = {
        "revenue": tail_statistics([row["net"] for row in revenue_daily]),
        "intensity_gated": tail_statistics([row["net"] for row in intensity_daily]),
        "combined_inverse_vol": tail_statistics([row["net"] for row in combined]),
        "combined_vol_target": tail_statistics([row["net"] for row in sleeve_vol_target(combined, 0.10)]),
    }
    args.output.write_text(json.dumps(report, indent=1) + "\n")

    print(f"rows {len(probabilities)} | classes {classes} | distinct confidences {report['model']['distinct_confidences']}")
    print("reliability bins:")
    print("  range        n   confidence  accuracy   gap")
    for row in table:
        print("  %.1f-%.1f  %4d    %.3f      %.3f   %+.3f" % (
            row["lower"], row["upper"], row["n"], row["mean_confidence"], row["accuracy"], row["gap"]))
    print("ECE %.4f | MCE %.4f | ECE interval [%.4f, %.4f] | sharpness %.3f" % (
        report["expected_calibration_error"], report["maximum_calibration_error"],
        report["expected_calibration_error_interval"]["lower"],
        report["expected_calibration_error_interval"]["upper"], report["sharpness"]))
    print("extreme bins:", json.dumps(report["extreme_bins"]))
    for name, stats in report["tails"].items():
        print("  tails %-22s var5 %+.4f cvar5 %+.4f worst day %+.4f worst %d-session %+.1f%%" % (
            name, stats["var_5pct"], stats["cvar_5pct"], stats["worst_day"],
            stats["worst_window"]["length"], stats["worst_window"]["return"] * 100))
    print("written", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
