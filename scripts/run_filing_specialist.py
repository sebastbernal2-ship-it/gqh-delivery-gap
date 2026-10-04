#!/usr/bin/env python3
"""Run the declared filing specialist comparison: prevalence against the fitted baseline.

Protocol: docs/plan/filing-specialist.md. Development only; both sealed windows are spent and
the label count is small, so nothing here supports a performance claim.
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
from filing_specialist.panel import FLAG_FEATURES, FEATURES  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, default=ROOT / "results" / "filing-specialist-events.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "filing-specialist-scores.json")
    parser.add_argument("--split", type=float, default=0.7)
    args = parser.parse_args()

    rows = list(csv.DictReader(args.panel.open()))
    if not rows:
        raise SystemExit("the panel is empty")
    report = compare(rows, FEATURES + FLAG_FEATURES, fraction=args.split)
    report.update({
        "schema": "filing-specialist-comparison-v1",
        "scope": "development_only",
        "protocol": "docs/plan/filing-specialist.md",
        "panel": str(args.panel.relative_to(ROOT)),
        "ready_for_performance_claim": False,
        "limitations": [
            "84 obligation revisions, one issuer dominates, three of four candidate firms have no obligations",
            "metadata-only features; the filing text and the JevLike scorer are the declared next step",
            "no filled orders, no costs, no trading claim",
        ],
    })
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({
        "split": report["split"],
        "prevalence": report["prevalence"],
        "softmax": report["softmax"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
