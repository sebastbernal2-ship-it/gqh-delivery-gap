#!/usr/bin/env python3
"""Build an evidence-backed review of the largest slipped entities.

The script never promotes candidate matches. A row is verified only when the
crosswalk already contains a verified source-backed mapping.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from strategy.ownership import build_review, review_fields  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exposure", default="results/exposure-panel.csv")
    parser.add_argument("--crosswalk", default="docs/entity-crosswalk.csv")
    parser.add_argument("--out", default="results/ownership-crosswalk.csv")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args(argv)
    if args.limit < 1:
        raise SystemExit("--limit must be positive")

    with (ROOT / args.exposure).open(newline="") as handle:
        exposure = list(csv.DictReader(handle))
    with (ROOT / args.crosswalk).open(newline="") as handle:
        crosswalk = list(csv.DictReader(handle))
    review = build_review(exposure, crosswalk, limit=args.limit)

    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=review_fields(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(review)

    verified = sum(row["attribution_status"] == "verified" for row in review)
    print(f"wrote {args.out} ({len(review)} rows); verified={verified}; unresolved={len(review) - verified}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
