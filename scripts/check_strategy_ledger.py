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


CROSSWALK_FIELDS = ("entity_name", "ticker", "cik", "direction", "weight",
                    "evidence", "identity_vintage", "source_receipt")


def validate_crosswalk(rows: list[dict[str, str]], require_verified: bool = False) -> int:
    """Validate issuer identity evidence and return the verified row count."""
    verified = 0
    for number, row in enumerate(rows, start=2):
        if row.get("status", "").strip() != "verified":
            continue
        verified += 1
        missing = [field for field in CROSSWALK_FIELDS if not row.get(field, "").strip()]
        if missing:
            raise ValueError(f"crosswalk row {number}: missing {', '.join(missing)}")
        try:
            weight = float(row["weight"])
        except ValueError as exc:
            raise ValueError(f"crosswalk row {number}: weight is not numeric") from exc
        if not 0 <= weight <= 1:
            raise ValueError(f"crosswalk row {number}: weight must be between zero and one")
    if require_verified and not verified:
        raise ValueError("crosswalk has no verified mappings")
    return verified


def validate_package(files: dict[str, Path], crosswalk: Path | None = None,
                     require_verified: bool = False) -> dict[str, int]:
    """Validate all supplied typed packages before a promotion decision."""
    counts = {kind: len(read_typed_csv(path, kind)) for kind, path in files.items()}
    if crosswalk is not None:
        with crosswalk.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        counts["crosswalk_verified"] = validate_crosswalk(rows, require_verified)
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    for kind in ("events", "primary_events", "exposures", "physical", "trades"):
        parser.add_argument(f"--{kind}", type=Path)
    parser.add_argument("--crosswalk", type=Path)
    parser.add_argument("--require-verified", action="store_true")
    args = parser.parse_args(argv)
    files = {kind: getattr(args, kind) for kind in ("events", "primary_events", "exposures", "physical", "trades")
             if getattr(args, kind) is not None}
    if not files and args.crosswalk is None:
        parser.error("provide at least one typed strategy CSV or --crosswalk")
    counts = validate_package(files, args.crosswalk, args.require_verified)
    for kind, count in counts.items():
        if kind != "crosswalk_verified":
            print(f"{kind}: {count} rows valid")
    if args.crosswalk is not None:
        with args.crosswalk.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        print(f"crosswalk: {len(rows)} rows, {counts['crosswalk_verified']} verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
