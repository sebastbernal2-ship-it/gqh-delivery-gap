#!/usr/bin/env python3
"""Build point-in-time revision events from EIA capacity vintages."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from edgar.filings import sealed_start  # noqa: E402

FIELDS = ["event_id", "source", "source_receipt", "entity_key", "vintage", "observed_at",
          "available_at", "usable_at", "unit", "evidence_status", "expectation_kind",
          "prior_value", "current_value", "missingness_reason", "in_sealed_window"]


def previous_vintage(vintage: str) -> str:
    year, month = (int(part) for part in vintage.split("-"))
    return f"{year - 1:04d}-{month:02d}"


def build_events(rows: list[dict], history_start: dt.date, history_end: dt.date) -> list[dict]:
    values: dict[tuple[str, int], float] = {}
    receipts: dict[str, str] = {}
    available: dict[str, str] = {}
    for row in rows:
        vintage = row["vintage"]
        key = (vintage, int(row["promised_year"]))
        values[key] = float(row["capacity_mw"])
        receipts[vintage] = row.get("source_receipt", "")
        available[vintage] = row["available_from"]
    boundary = sealed_start(history_start, history_end)
    events = []
    for (vintage, target_year), current in sorted(values.items()):
        prior_vintage = previous_vintage(vintage)
        prior = values.get((prior_vintage, target_year))
        if prior is None or prior <= 0:
            continue
        stamp = available[vintage] + "T23:59:59+00:00"
        events.append({
            "event_id": f"eia-capacity:{vintage}:{target_year}",
            "source": "eia:860m",
            "source_receipt": receipts[vintage],
            "entity_key": "grid:planned-capacity",
            "vintage": vintage,
            "observed_at": stamp,
            "available_at": stamp,
            "usable_at": stamp,
            "unit": "MW",
            "evidence_status": "downloaded",
            "expectation_kind": "public_plan",
            "prior_value": prior,
            "current_value": current,
            "missingness_reason": "",
            "in_sealed_window": vintage >= boundary.isoformat(),
        })
    return events


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="results/capacity-expectations.csv")
    parser.add_argument("--history-start", default="2015-01-01")
    parser.add_argument("--history-end", default=dt.date.today().isoformat())
    parser.add_argument("--out", default="results/capacity-event-ledger.csv")
    args = parser.parse_args(argv)
    with (ROOT / args.input).open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    events = build_events(rows, dt.date.fromisoformat(args.history_start),
                          dt.date.fromisoformat(args.history_end))
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(events)
    print(f"wrote {args.out} ({len(events)} events; {sum(not e['in_sealed_window'] for e in events)} development)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
