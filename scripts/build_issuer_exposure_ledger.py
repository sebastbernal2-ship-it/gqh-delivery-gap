#!/usr/bin/env python3
"""Build verified direct-issuer exposure rows from the PWR SEC obligation panel."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ["event_id", "issuer", "security", "segment", "direction", "weight", "status",
          "evidence", "source_receipt", "identity_vintage"]


def build_rows(rows: list[dict]) -> list[dict]:
    output = []
    for row in rows:
        if str(row.get("in_sealed_window", "")).lower() in {"true", "1", "yes"}:
            continue
        if not row.get("change") or row.get("ticker") != "PWR":
            continue
        change = float(row["change"])
        output.append({
            "event_id": f"sec:{row['accession']}:{row['concept']}:{row['period_end']}",
            "issuer": "QUANTA SERVICES, INC.",
            "security": "PWR",
            "segment": "corporate",
            "direction": "positive" if change > 0 else "negative" if change < 0 else "neutral",
            "weight": "1.0",
            "status": "verified",
            "evidence": f"SEC accession {row['accession']}; {row['concept']}",
            "source_receipt": row["source_receipt"],
            "identity_vintage": row["filed"],
        })
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="results/obligation-panel.csv")
    parser.add_argument("--out", default="results/issuer-exposure-ledger.csv")
    args = parser.parse_args(argv)
    with (ROOT / args.input).open(newline="") as handle:
        rows = build_rows(list(csv.DictReader(handle)))
    out = ROOT / args.out
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    print(f"wrote {args.out} ({len(rows)} verified direct-issuer exposures)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
