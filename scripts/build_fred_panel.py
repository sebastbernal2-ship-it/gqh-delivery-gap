#!/usr/bin/env python3
"""One daily rates and macro panel from the open FRED CSV endpoint, with a one-day publication lag.

FRED serves every series as a CSV with no key. A value dated t is published after t, so using it at t
would be a look-ahead: the panel shifts each series by one observation and records that choice. The wide
credit spread series is served with a short rolling window on the free endpoint, so the panel keeps it
only where it exists and never fills it backwards.

    python3 scripts/build_fred_panel.py
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERIES = ("DGS10", "DGS2", "DFII10", "T10Y2Y", "T10YIE", "BAA10Y", "BAMLH0A0HYM2", "DHHNGSP",
          "DCOILWTICO", "VIXCLS", "APU000072610")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=ROOT / "results" / "fred-raw")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "fred-panel.csv.gz")
    args = parser.parse_args()

    rows: dict[str, dict[str, float]] = {}
    coverage = {}
    for series in SERIES:
        path = args.raw / f"{series}.csv"
        if not path.exists():
            coverage[series] = {"rows": 0, "note": "missing locally"}
            continue
        values = []
        with path.open() as handle:
            for record in csv.reader(handle):
                if len(record) < 2 or record[0] in ("DATE", "observation_date"):
                    continue
                raw = record[1].strip()
                if raw in ("", "."):
                    continue
                try:
                    values.append((record[0], float(raw)))
                except ValueError:
                    continue
        values.sort()
        coverage[series] = {"rows": len(values),
                            "from": values[0][0] if values else None,
                            "to": values[-1][0] if values else None}
        for index in range(1, len(values)):                 # the one-observation lag
            day, value = values[index]
            rows.setdefault(day, {})[series] = value
    days = sorted(rows)
    columns = ["date", *SERIES]
    with gzip.open(args.output, "wt", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for day in days:
            writer.writerow({"date": day, **rows[day]})
    (ROOT / "results" / "fred-panel-coverage.json").write_text(
        json.dumps({"schema": "fred-panel-coverage-v1", "coverage": coverage,
                    "lag": "one observation, declared"}, indent=1, sort_keys=True) + "\n")
    print("panel: %d days, %s .. %s, %.1f KB" % (
        len(days), days[0] if days else "n/a", days[-1] if days else "n/a",
        args.output.stat().st_size / 1e3))
    for series, block in coverage.items():
        print("  %-14s rows %6s  %s .. %s" % (series, block["rows"], block.get("from"),
                                              block.get("to")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
