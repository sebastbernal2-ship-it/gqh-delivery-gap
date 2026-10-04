#!/usr/bin/env python3
"""Verify event and KDB daily-bar manifests using only the Python standard library."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--event-manifest", type=Path, required=True)
    parser.add_argument("--bars", type=Path, required=True)
    parser.add_argument("--bars-manifest", type=Path, required=True)
    parser.add_argument("--development-start", type=date.fromisoformat, required=True)
    parser.add_argument("--sealed-start", type=date.fromisoformat, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.development_start >= args.sealed_start:
        parser.error("development start must precede sealed start")

    event_meta = json.loads(args.event_manifest.read_text(encoding="utf-8"))
    event_bytes = args.events.read_bytes()
    if event_meta.get("study_role") != "development":
        parser.error("event manifest is not marked development")
    if event_meta.get("events_file") != args.events.name:
        parser.error("event manifest file name does not match input")
    if event_meta.get("events_sha256") != hashlib.sha256(event_bytes).hexdigest():
        parser.error("event CSV SHA-256 does not match its manifest")
    if event_meta.get("development_start") != args.development_start.isoformat() or event_meta.get("sealed_start") != args.sealed_start.isoformat():
        parser.error("event manifest date fences do not match this run")
    with args.events.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        event_fields = reader.fieldnames or []
    if len(rows) != event_meta.get("event_rows"):
        parser.error("event row count does not match manifest")
    if event_fields != event_meta.get("columns"):
        parser.error("event columns do not match manifest")
    if any(row.get("in_sealed_window", "").strip().lower() in {"true", "1", "yes"} for row in rows):
        parser.error("sealed events are forbidden in staged input")
    if any(date.fromisoformat(row["available_at_utc"][:10]) >= args.sealed_start for row in rows):
        parser.error("event file contains sealed-date observations")

    bar_meta = json.loads(args.bars_manifest.read_text(encoding="utf-8"))
    raw = args.bars.read_bytes()
    lines = raw.splitlines(keepends=True)
    if len(lines) < 2:
        parser.error("bars TSV is empty")
    body_digest = hashlib.sha256(b"".join(lines[1:])).hexdigest()
    if bar_meta.get("sha256_tsv_body") != body_digest:
        parser.error("bars TSV body hash does not match exporter manifest")
    if len(lines) - 1 != bar_meta.get("rows"):
        parser.error("bars TSV row count does not match exporter manifest")
    with args.bars.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        fields = reader.fieldnames or []
        bar_rows = list(reader)
    required = {"date", "sym", "source_id", "batch_sha256", "close_px_e8usd", "row_sha256"}
    if not required.issubset(fields):
        parser.error("bars TSV is missing required KDB exporter columns")
    max_date = max(date.fromisoformat(row["date"].replace(".", "-")) for row in bar_rows)
    if max_date >= args.sealed_start:
        parser.error("bars TSV must end before the sealed cutoff")
    symbols = sorted({row["sym"] for row in bar_rows})
    if "SPY" not in symbols:
        parser.error("bars TSV must include SPY")
    required_symbols = {row["ticker"] for row in rows if row.get("ticker")}
    missing_tickers = sorted(required_symbols - set(symbols))
    if missing_tickers:
        parser.error("bars TSV missing event ticker(s): " + ", ".join(missing_tickers))
    sector_symbols = {row["sector_symbol"] for row in rows if row.get("sector_symbol")}
    missing_sectors = sorted(sector_symbols - set(symbols))
    if missing_sectors:
        print("sector-adjusted results unavailable for: " + ", ".join(missing_sectors))
    if bar_meta.get("columns") != fields:
        parser.error("bars columns do not match exporter manifest")
    allowed_batches = {(b["source_id"], b["batch_sha256"]) for b in bar_meta.get("batches", [])}
    if any((row["source_id"], row["batch_sha256"]) not in allowed_batches for row in bar_rows):
        parser.error("bar row provenance is not listed in exporter manifest")
    receipt = {
        "study_role": "development",
        "development_start": args.development_start.isoformat(),
        "sealed_start": args.sealed_start.isoformat(),
        "events_sha256": event_meta["events_sha256"],
        "event_rows": len(rows),
        "bars_body_sha256": body_digest,
        "bar_rows": len(bar_rows),
        "symbols": symbols,
        "batches": bar_meta.get("batches", []),
    }
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"verified development inputs: {len(rows)} events, {len(bar_rows)} bars, {len(symbols)} symbols")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
