#!/usr/bin/env python3
"""Build point-in-time expectation vintages for the RPO panel.

Protocol: docs/plan/filing-specialist.md, label section. Every expectation uses only
observations public strictly before the one it describes; the history count and span are
recorded, and a missing history is a missing status, never a filled value.

    python3 scripts/build_rpo_vintages.py
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.vintages import COLUMNS, MINIMUM_HISTORY, build_vintages  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, default=ROOT / "results" / "rpo-events.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "rpo-vintages.csv")
    parser.add_argument("--minimum-history", type=int, default=MINIMUM_HISTORY)
    args = parser.parse_args()

    rows = list(csv.DictReader(args.panel.open()))
    vintages, drops = build_vintages(rows, args.minimum_history)
    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(COLUMNS), extrasaction="ignore")
        writer.writeheader()
        for record in vintages:
            writer.writerow(record)

    counts: dict[str, int] = {}
    for record in vintages:
        counts[record["expectation_kind"] or "missing"] = \
            counts.get(record["expectation_kind"] or "missing", 0) + 1
    relative = [float(record["relative_surprise_pit"]) for record in vintages
                if record["relative_surprise_pit"] != ""]
    summary = {
        "input_rows": len(rows),
        "usable_rows": len(vintages),
        "drops": drops,
        "kinds": counts,
        "relative_surprises": len(relative),
        "sealed_flagged": sum(1 for record in vintages if str(record.get("in_sealed_window")) == "True"),
        "minimum_history": args.minimum_history,
        "output": str(args.output.relative_to(ROOT)),
    }
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
