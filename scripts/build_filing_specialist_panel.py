#!/usr/bin/env python3
"""Build the filing specialist panel: one row per obligation revision.

Protocol: docs/plan/filing-specialist.md. Every feature is known strictly before the decision
time, the decision is the latest filing strictly before the revision's availability, and the
label is the revision's surprise relative to its own previous value.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.panel import (BIN_LABELS, FLAG_FEATURES, build_panel, load_filings,  # noqa: E402
                                     load_obligations, load_revisions)

COLUMNS = (
    "ticker", "concept", "decision_time", "filing_accession", "filing_form",
    "decision_clock_coarse", "form_is_8k", "has_item_101", "has_item_202", "has_item_701",
    "filings_last_90d", "days_since_last_filing", "last_change_rel", "trailing_mean_change_rel",
    "prior_revision_count", "last_surprise_rel", "days_since_last_obligation", "concept_is_rpo",
    "missing_last_change_rel", "missing_last_surprise_rel", "missing_last_obligation",
    "prior_revision_period_end", "label_period_end", "label_available", "label_change",
    "label_typical_change", "label_surprise", "label_relative_surprise", "label_bin",
    "label_bin_label", "candidate_filings",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--filings", type=Path, default=ROOT / "results" / "filings-register.csv")
    parser.add_argument("--obligations", type=Path, default=ROOT / "results" / "obligation-panel.csv")
    parser.add_argument("--revisions", type=Path, default=ROOT / "results" / "revision-events.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "filing-specialist-events.csv")
    args = parser.parse_args()

    filings = load_filings(args.filings)
    obligations = load_obligations(args.obligations)
    revisions = load_revisions(args.revisions)
    panel = build_panel(filings, obligations, revisions)
    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(COLUMNS), extrasaction="ignore")
        writer.writeheader()
        for row in panel.rows:
            writer.writerow(row)

    bins = {}
    for row in panel.rows:
        bins[row["label_bin_label"]] = bins.get(row["label_bin_label"], 0) + 1
    print(json.dumps({
        "rows": len(panel.rows),
        "drops": panel.drops,
        "bins": {label: bins.get(label, 0) for label in BIN_LABELS},
        "filings": len(filings),
        "obligations": len(obligations),
        "revisions": len(revisions),
        "flag_columns": list(FLAG_FEATURES),
        "output": str(args.output.relative_to(ROOT)),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
