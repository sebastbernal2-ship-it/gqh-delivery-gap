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
from filing_specialist.model import compare  # noqa: E402
from filing_specialist.rpo_model import BIN_LABELS, FEATURES, prepare_rows  # noqa: E402


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
