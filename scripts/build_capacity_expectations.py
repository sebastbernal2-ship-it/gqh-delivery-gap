#!/usr/bin/env python3
"""Reduce every monthly vintage to one row per promised year, cached so this runs once.

Downloading and parsing a hundred and seventeen spreadsheets is the slow part, so each vintage is
reduced to a small JSON file and the panel is rebuilt from those in seconds.

Usage:
    python scripts/build_capacity_expectations.py --start 2016-01 --end 2024-09
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from eia.aggregate import availability, months, promised_capacity_by_year  # noqa: E402
from eia.vintages import fetch_vintage, vintage_url  # noqa: E402

REDUCED = ROOT / "results" / "vintage-aggregates"
FIELDS = ["vintage", "available_from", "promised_year", "capacity_mw", "source_receipt"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2016-01")
    parser.add_argument("--end", default="2024-09")
    parser.add_argument("--out", default="results/capacity-expectations.csv")
    args = parser.parse_args(argv)

    start_year, start_month = (int(part) for part in args.start.split("-"))
    end_year, end_month = (int(part) for part in args.end.split("-"))
    REDUCED.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    failures: list[str] = []
    for year, month in months(start_year, start_month, end_year, end_month):
        stamp = f"{year:04d}-{month:02d}"
        reduced = REDUCED / f"{stamp}.json"
        if reduced.exists():
            totals = {int(k): v for k, v in json.loads(reduced.read_text()).items()}
        else:
            try:
                path = fetch_vintage(year, month)
                totals = promised_capacity_by_year(path, year, month)
            except Exception as exc:  # a network fault on one month must not cost the whole run
                failures.append(f"{stamp}: {type(exc).__name__}")
                print(f"{stamp}: FAILED, continuing ({type(exc).__name__})")
                continue
            reduced.write_text(json.dumps({str(k): v for k, v in totals.items()}))
            print(f"{stamp}: {len(totals)} promised years, "
                  f"{sum(totals.values()):,.0f} MW total")
        for promised_year, capacity in sorted(totals.items()):
            rows.append({"vintage": stamp, "available_from": availability(year, month),
                         "promised_year": promised_year, "capacity_mw": round(capacity, 1),
                         "source_receipt": vintage_url(year, month)})

    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {args.out} ({len(rows)} rows, {len({r['vintage'] for r in rows})} vintages)")

    vintages = sorted({r["vintage"] for r in rows})
    print(f"vintages: {vintages[0]} to {vintages[-1]}")
    if failures:
        print(f"months that failed and can be retried: {len(failures)} {failures[:8]}")
    total = sum(float(r["capacity_mw"]) for r in rows if r["vintage"] == vintages[-1])
    print(f"latest vintage promises {total:,.0f} MW in total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
