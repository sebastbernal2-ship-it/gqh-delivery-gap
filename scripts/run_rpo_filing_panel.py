#!/usr/bin/env python3
"""Does what a firm filed add anything to what it already disclosed?

Protocol: docs/plan/rpo-filing-join.md. Two models on the same rows and the same chronological
split: the disclosure history alone, and the history plus the latest filing's features.

    python3 scripts/run_rpo_filing_panel.py
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
from filing_specialist.rpo_model import FEATURES, prepare_rows  # noqa: E402
from filing_specialist.rpo_panel import FILING_FEATURES, augment_rows, load_filings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vintages", type=Path, default=ROOT / "results" / "rpo-vintages.csv")
    parser.add_argument("--filings", type=Path,
                        default=ROOT / "results" / "filings-register-rpo.csv")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results" / "rpo-filing-panel-scores.json")
    parser.add_argument("--split", type=float, default=0.7)
    args = parser.parse_args()

    prepared, drops = prepare_rows(list(csv.DictReader(args.vintages.open())))
    filings = load_filings(list(csv.DictReader(args.filings.open())))
    augmented, join_drops = augment_rows(prepared, filings)
    history_only = compare(augmented, FEATURES, fraction=args.split)
    with_filings = compare(augmented, FEATURES + FILING_FEATURES, fraction=args.split)
    covered = sum(1 for row in augmented if row["has_filing"] == 1.0)
    report = {
        "schema": "rpo-filing-join-v1",
        "scope": "development_only",
        "protocol": "docs/plan/rpo-filing-join.md",
        "rows": len(augmented),
        "issuers": len({row["ticker"] for row in augmented}),
        "rows_with_a_filing": covered,
        "drops": {**drops, **join_drops},
        "history_only": history_only,
        "with_filings": with_filings,
        "ready_for_performance_claim": False,
        "limitations": [
            "the filing join is metadata only; no document text in this comparison",
            "one filing per decision: the latest strictly before the disclosure",
            "no returns, no costs, no trading claim",
        ],
    }
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({
        "rows": report["rows"], "issuers": report["issuers"],
        "rows_with_a_filing": covered,
        "history_only": {"log_loss": history_only["softmax"]["log_loss"],
                         "brier": history_only["softmax"]["brier"],
                         "accuracy": history_only["softmax"]["accuracy"]},
        "with_filings": {"log_loss": with_filings["softmax"]["log_loss"],
                         "brier": with_filings["softmax"]["brier"],
                         "accuracy": with_filings["softmax"]["accuracy"]},
        "prevalence": {"log_loss": with_filings["prevalence"]["log_loss"],
                       "brier": with_filings["prevalence"]["brier"],
                       "accuracy": with_filings["prevalence"]["accuracy"]},
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
