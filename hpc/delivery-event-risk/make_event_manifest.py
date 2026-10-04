#!/usr/bin/env python3
"""Freeze a reviewed, development-only event CSV with its source-document hashes."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date
from pathlib import Path

REQUIRED = {
    "event_id", "event_cluster_id", "ticker", "metric_key", "unit", "available_at_utc",
    "expectation_available_at_utc", "expectation_type", "prior_expectation", "current_value",
    "review_status", "exposure_status", "sector_symbol", "document_sha256", "in_sealed_window",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--development-start", type=date.fromisoformat, required=True)
    parser.add_argument("--sealed-start", type=date.fromisoformat, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.development_start >= args.sealed_start:
        parser.error("development start must precede sealed start")
    raw = args.events.read_bytes()
    with args.events.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        missing = sorted(REQUIRED - set(fields))
        if missing:
            parser.error("event CSV missing columns: " + ", ".join(missing))
        rows = list(reader)
    if not rows:
        parser.error("event CSV is empty")
    if any(row["in_sealed_window"].strip().lower() in {"true", "1", "yes"} for row in rows):
        parser.error("event CSV must contain development events only; sealed rows cannot be staged")
    hashes = sorted({row["document_sha256"].strip() for row in rows if row["document_sha256"].strip()})
    if not hashes or any(len(value) != 64 or any(c not in "0123456789abcdef" for c in value) for value in hashes):
        parser.error("every included event must have a lowercase SHA-256 source-document hash")
    for row in rows:
        stamp = row["available_at_utc"].strip()
        if len(stamp) < 20 or stamp[10] != "T" or not (stamp.endswith("Z") or "+" in stamp[10:] or "-" in stamp[10:]):
            parser.error("each event needs a timezone-aware ISO-8601 available_at_utc")
        if date.fromisoformat(stamp[:10]) >= args.sealed_start:
            parser.error("event CSV contains a sealed-date event")
    manifest = {
        "schema_version": 1,
        "study_role": "development",
        "development_start": args.development_start.isoformat(),
        "sealed_start": args.sealed_start.isoformat(),
        "events_file": args.events.name,
        "events_sha256": hashlib.sha256(raw).hexdigest(),
        "event_rows": len(rows),
        "columns": fields,
        "source_document_sha256": hashes,
        "note": "Integrity and declared role only; the manifest does not certify review or exposure decisions.",
    }
    if args.out.exists():
        parser.error(f"refusing to overwrite {args.out}")
    args.out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.out} ({len(rows)} development events)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
