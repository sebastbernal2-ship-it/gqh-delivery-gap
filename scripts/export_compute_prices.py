#!/usr/bin/env python3
"""Produce the monthly compute price aggregate from the TigerData table.

Whoever holds the connection runs this once:

    export TIGERDATA_URL="postgres://..."     # never paste it into a file that Git tracks
    ./<project environment>/bin/python scripts/export_compute_prices.py

It writes `results/compute-price-monthly.csv`, which is small enough to commit and contains no
credentials, only months, families, counts and medians. The connection string is read from the
environment, never printed, and never written anywhere.

If you would rather not hand over any connection at all, run the SQL in `src/scan/compute.py` in your own
client and drop the CSV in the same place. Both routes produce the same file.
"""
from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from scan.compute import AGGREGATE_SQL, ENV_VARIABLE, EXPORT  # noqa: E402

FIELDS = ["month", "family", "quotes", "median_usd_per_instance_hour", "zones"]


def main() -> int:
    url = os.environ.get(ENV_VARIABLE)
    if not url:
        print(f"{ENV_VARIABLE} is not set. Nothing to do.")
        print("Either export it in your shell for one command, or run the SQL in src/scan/compute.py")
        print(f"yourself and place the result at {EXPORT.relative_to(ROOT)}.")
        return 1
    try:
        import psycopg  # type: ignore
    except ImportError:
        print("psycopg is not installed in this interpreter. Install it into the project environment,")
        print("not the system one: <project environment>/bin/python -m pip install 'psycopg[binary]'")
        return 1
    try:
        with psycopg.connect(url, connect_timeout=20) as connection:
            with connection.cursor() as cursor:
                cursor.execute(AGGREGATE_SQL)
                rows = cursor.fetchall()
    except Exception as exc:
        # Type only: driver messages can quote the connection string.
        print(f"the query failed with {type(exc).__name__}. Nothing was written.")
        return 1

    EXPORT.parent.mkdir(parents=True, exist_ok=True)
    with EXPORT.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(FIELDS)
        for month, family, quotes, median, zones in rows:
            if month is None or family is None or median is None:
                continue
            writer.writerow([str(month)[:10], str(family).lower(), quotes, median, zones])
    months = sorted({str(row[0])[:7] for row in rows if row[0] is not None})
    families = sorted({str(row[1]).lower() for row in rows if row[1] is not None})
    print(f"wrote {EXPORT.relative_to(ROOT)}: {len(rows)} rows, {len(families)} families, "
          f"{months[0] if months else 'n/a'} to {months[-1] if months else 'n/a'}")
    print("This file contains no credentials and can be committed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
