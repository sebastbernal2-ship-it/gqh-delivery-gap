#!/usr/bin/env python3
"""Compare filing decisions labelled by the next point-in-time obligation surprise.

Protocol: docs/plan/filing-obligation-panel.md. Two views of the same labels: the deciding filing
per disclosure (the primary metric) and every filing before it (a robustness row whose rows share
labels, so its distinct-label count travels with it).

    python3 scripts/run_filing_obligation_panel.py
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

FEATURES = ("prior_count", "last_change_rel", "trailing_mean_change_rel",
            "days_since_last_obligation", "missing_last_obligation", "form_is_8k",
            "has_item_101", "has_item_202", "has_item_701", "concept_is_rpo")


def prepare(row: dict) -> dict:
    items = row.get("filing_items") or ""
    prepared = {name: (row.get(name) if row.get(name) not in ("", None) else None)
                for name in ("prior_count", "last_change_rel", "trailing_mean_change_rel",
                             "days_since_last_obligation", "missing_last_obligation")}
    prepared.update({
        "form_is_8k": 1.0 if row["filing_form"].startswith("8-K") else 0.0,
        "has_item_101": 1.0 if "1.01" in items else 0.0,
        "has_item_202": 1.0 if "2.02" in items else 0.0,
        "has_item_701": 1.0 if "7.01" in items else 0.0,
        "concept_is_rpo": 1.0 if row["concept"].endswith("RevenueRemainingPerformanceObligation") else 0.0,
        "label_bin": int(row["label_bin"]),
        "label_available": row["label_available"],
        "disclosure_id": row["disclosure_id"],
    })
    return prepared


def summary(report: dict, rows: list[dict]) -> dict:
    return {
        "rows": len(rows),
        "distinct_labels": len({row["disclosure_id"] for row in rows}),
        "split": report["split"],
        "prevalence": report["prevalence"],
        "softmax": report["softmax"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path,
                        default=ROOT / "results" / "filing-obligation-decisions.csv")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results" / "filing-obligation-scores.json")
    parser.add_argument("--split", type=float, default=0.7)
    args = parser.parse_args()

    rows = list(csv.DictReader(args.panel.open()))
    deciding = [prepare(row) for row in rows if row["is_deciding"] == "1"]
    every = [prepare(row) for row in rows]
    if len(deciding) < 20:
        raise SystemExit("not enough deciding rows")
    report = {
        "schema": "filing-obligation-comparison-v1",
        "scope": "development_only",
        "protocol": "docs/plan/filing-obligation-panel.md",
        "features": list(FEATURES),
        "deciding_filing": summary(compare(deciding, FEATURES, fraction=args.split), deciding),
        "every_filing": summary(compare(every, FEATURES, fraction=args.split), every),
        "limitations": [
            "PWR and ETN only; EME and DLR file no measured obligation facts",
            "the deciding view has 87 rows over about 50 distinct disclosure periods",
            "the every-filing view reuses each label many times, so its rows are not independent",
            "no document text in this comparison, no returns, no costs",
        ],
        "ready_for_performance_claim": False,
    }
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    for name in ("deciding_filing", "every_filing"):
        block = report[name]
        print(name, "rows", block["rows"], "distinct", block["distinct_labels"],
              "| prevalence log %.4f acc %.3f | softmax log %.4f acc %.3f" % (
                  block["prevalence"]["log_loss"], block["prevalence"]["accuracy"],
                  block["softmax"]["log_loss"], block["softmax"]["accuracy"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
