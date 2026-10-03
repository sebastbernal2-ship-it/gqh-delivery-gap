#!/usr/bin/env python3
"""Write a review report for the issuer crosswalk without promoting mappings."""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ("entity_name", "ticker", "cik", "direction", "weight", "evidence",
            "identity_vintage", "source_receipt")
FIELDS = ["status", "rows", "missing_required", "pnl_eligible"]


def review(rows: list[dict]) -> list[dict]:
    if not rows:
        return [{"status": "empty", "rows": 0, "missing_required": 0, "pnl_eligible": 0}]
    counts = Counter(row.get("status", "missing") or "missing" for row in rows)
    report = []
    for status, count in sorted(counts.items()):
        subset = [row for row in rows if (row.get("status", "missing") or "missing") == status]
        missing = sum(1 for row in subset if any(not row.get(field, "").strip() for field in REQUIRED))
        report.append({"status": status, "rows": count, "missing_required": missing,
                       "pnl_eligible": count if status == "verified" and missing == 0 else 0})
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="docs/entity-crosswalk.csv")
    parser.add_argument("--out", default="results/crosswalk-review.csv")
    args = parser.parse_args(argv)
    with (ROOT / args.input).open(newline="") as handle:
        report = review(list(csv.DictReader(handle)))
    out = ROOT / args.out
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader(); writer.writerows(report)
    verified = sum(int(row["pnl_eligible"]) for row in report)
    print(f"wrote {args.out}; verified P&L mappings: {verified}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
