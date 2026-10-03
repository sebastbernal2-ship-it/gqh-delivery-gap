#!/usr/bin/env python3
"""Validate typed strategy CSVs before event-study or promotion work."""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from strategy.sources import read_typed_csv  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    for kind in ("events", "primary_events", "exposures", "physical", "trades"):
        parser.add_argument(f"--{kind}", type=Path)
    parser.add_argument("--crosswalk", type=Path)
    parser.add_argument("--require-verified", action="store_true")
    args = parser.parse_args(argv)
    files = [(kind, getattr(args, kind)) for kind in ("events", "primary_events", "exposures", "physical", "trades")
             if getattr(args, kind) is not None]
    if not files and args.crosswalk is None:
        parser.error("provide at least one typed strategy CSV or --crosswalk")
    for kind, path in files:
        count = len(read_typed_csv(path, kind))
        print(f"{kind}: {count} rows valid")
    if args.crosswalk is not None:
        with args.crosswalk.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        verified = 0
        for number, row in enumerate(rows, start=2):
            if row.get("status", "").strip() != "verified":
                continue
            verified += 1
            required = ("entity_name", "ticker", "cik", "direction", "weight",
                        "evidence", "identity_vintage", "source_receipt")
            missing = [field for field in required if not row.get(field, "").strip()]
            if missing:
                raise ValueError(f"crosswalk row {number}: missing {', '.join(missing)}")
            try:
                weight = float(row["weight"])
            except ValueError as exc:
                raise ValueError(f"crosswalk row {number}: weight is not numeric") from exc
            if not 0 <= weight <= 1:
                raise ValueError(f"crosswalk row {number}: weight must be between zero and one")
        if args.require_verified and not verified:
            raise ValueError("crosswalk has no verified mappings")
        print(f"crosswalk: {len(rows)} rows, {verified} verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
