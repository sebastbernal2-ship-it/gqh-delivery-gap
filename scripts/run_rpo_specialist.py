#!/usr/bin/env python3
"""Run the declared RPO surprise comparison on the point-in-time vintages.

Protocol: docs/plan/rpo-specialist.md. Development only: the labels come from measured
point-in-time vintages, and both competition windows are spent.

    python3 scripts/run_rpo_specialist.py
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "hpc" / "probabilistic-council"))
from filing_specialist.model import chronological_split, compare  # noqa: E402
from filing_specialist.rpo_model import BIN_LABELS, FEATURES, prepare_rows  # noqa: E402
from rpo_specialist import disclosure_window, fit_rpo_specialist  # noqa: E402


def example_forecasts(rows: list[dict], split: float, count: int = 5) -> list[dict]:
    """Council-shaped forecasts for the first test rows, emitted for inspection."""
    train_rows, test_rows = chronological_split(rows, split)
    fitted = fit_rpo_specialist(train_rows, FEATURES, "rpo-softmax-v1", "rpo-vintages-20261004")
    out = []
    for row in test_rows[:count]:
        cutoff, forecast_time, valid_until = disclosure_window(row, None)
        forecast = fitted.forecast(row, f"{row['ticker']}:{row['period_end']}",
                                   cutoff, forecast_time, valid_until)
        out.append({
            "context": forecast.context,
            "specialist_id": forecast.specialist_id,
            "outcome_space": list(forecast.outcome_space),
            "probabilities": [round(value, 6) for value in forecast.probabilities],
            "information_cutoff": forecast.information_cutoff,
            "forecast_time": forecast.forecast_time,
            "valid_until": forecast.valid_until,
            "abstain": forecast.abstain,
            "model_version": forecast.model_version,
            "data_version": forecast.data_version,
            "label_bin": int(row["label_bin"]),
        })
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vintages", type=Path, default=ROOT / "results" / "rpo-vintages.csv")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results" / "rpo-specialist-scores.json")
    parser.add_argument("--split", type=float, default=0.7)
    args = parser.parse_args()

    rows, drops = prepare_rows(list(csv.DictReader(args.vintages.open())))
    if not rows:
        raise SystemExit("no usable rows in the vintages")
    report = compare(rows, FEATURES, fraction=args.split)
    bins: dict[str, int] = {}
    for row in rows:
        bins[row["label_bin_label"]] = bins.get(row["label_bin_label"], 0) + 1
    report.update({
        "schema": "rpo-specialist-comparison-v1",
        "scope": "development_only",
        "protocol": "docs/plan/rpo-specialist.md",
        "rows": len(rows),
        "drops": drops,
        "bins": {label: bins.get(label, 0) for label in BIN_LABELS},
        "issuers": len({row["ticker"] for row in rows}),
        "example_forecasts": example_forecasts(rows, args.split),
        "ready_for_performance_claim": False,
        "limitations": [
            "point-in-time vintages only; the legacy column is not used",
            "availability is end-of-day for most disclosures, so intraday timing is not resolved",
            "ticker identity is the current ticker; no historical ticker map",
            "no returns, no costs, no trading claim",
        ],
    })
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"rows": report["rows"], "issuers": report["issuers"],
                      "drops": report["drops"], "bins": report["bins"],
                      "split": report["split"], "prevalence": report["prevalence"],
                      "softmax": report["softmax"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
