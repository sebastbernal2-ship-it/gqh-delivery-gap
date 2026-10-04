#!/usr/bin/env python3
"""Point-in-time seasonal vintages for the strategy's own quarterly drivers.

The RPO panel proved the machinery; this runs it on the capex and revenue panels the intensity
strategy already trades, so the expectation gap covers the same universe instead of 17 overlapping
names. Availability is the filing date recorded on the fact, at end of day, which is the clock the
strategy already uses.

    python3 scripts/build_driver_vintages.py --panel results/complex-capex-quarterly.csv \
        --preferred PaymentsToAcquirePropertyPlantAndEquipment --output results/capex-vintages-pit.csv
"""
from __future__ import annotations

import argparse
import collections
import csv
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.vintages import COLUMNS, build_vintages  # noqa: E402


def build_input_rows(rows: list[dict], preferred: str, group_of: dict[str, str],
                     level: bool = False) -> tuple[list[dict], dict]:
    """One input row per (ticker, period) with the prior value, the change and the filing clock."""
    chosen: dict[tuple[str, str], dict] = {}
    drops: dict[str, int] = collections.Counter()
    for row in rows:
        ticker = (row.get("ticker") or "").strip()
        period_end = (row.get("period_end") or "").strip()
        filed = (row.get("filed") or "").strip()
        try:
            value = float(row["value_usd"])
        except (KeyError, TypeError, ValueError):
            drops["no_value"] += 1
            continue
        if not ticker or not period_end or not filed or value <= 0:
            drops["no_clock_or_value"] += 1
            continue
        # a change is only meaningful between like periods: keep durations near one quarter, so a
        # ten-K annual column can never be compared against a ten-Q quarter. Balance-sheet levels
        # have no duration: there the quarterly cadence is enforced by the prior-observation gap.
        if not level:
            try:
                import datetime
                start = datetime.date.fromisoformat(row["period_start"])
                end = datetime.date.fromisoformat(period_end)
                duration = (end - start).days
            except (KeyError, TypeError, ValueError):
                drops["no_duration"] += 1
                continue
            if not 80 <= duration <= 100:
                drops["not_a_quarter"] += 1
                continue
        key = (ticker, period_end)
        current = chosen.get(key)
        if current is None or (row.get("concept") == preferred and current["concept"] != preferred):
            chosen[key] = {**row, "value": value}

    by_ticker: dict[str, list[dict]] = collections.defaultdict(list)
    for (ticker, _), row in chosen.items():
        by_ticker[ticker].append(row)

    out = []
    for ticker, items in sorted(by_ticker.items()):
        items.sort(key=lambda item: item["period_end"])
        for position, row in enumerate(items):
            previous = items[position - 1]["value"] if position else None
            if previous is None or previous <= 0:
                drops["no_previous_value"] += 1
                continue
            out.append({
                "ticker": ticker,
                "concept": row.get("concept", ""),
                "group": group_of.get(ticker, ""),
                "period_end": row["period_end"],
                "earliest_availability_utc": f"{row['filed']}T23:59:59+00:00",
                "value": row["value"],
                "previous_value": previous,
                "change": row["value"] - previous,
                "availability_resolution": "filing date, end of day",
                "source_receipt": f"results/complex-quarterly/{ticker}/{row['period_end']}",
            })
    return out, dict(drops)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--preferred", default="")
    parser.add_argument("--level", action="store_true",
                        help="balance-sheet level: no period_start, cadence from the observation gap")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--group-panel", type=Path, default=ROOT / "results" / "market-panel.json")
    args = parser.parse_args()

    import json
    group_of = {}
    if args.group_panel.exists():
        panel = json.loads(args.group_panel.read_text())
        for group, payload in panel.get("groups", {}).items():
            for series in payload.get("series", []):
                group_of[series["ticker"]] = group

    rows = list(csv.DictReader(args.panel.open()))
    prepared, drops = build_input_rows(rows, args.preferred, group_of, level=args.level)
    records, vintage_drops = build_vintages(prepared)

    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(COLUMNS), extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow(record)

    lags = []
    for row in prepared:
        period = row["period_end"]
        filed = row["earliest_availability_utc"][:10]
        import datetime
        days = (datetime.date.fromisoformat(filed) - datetime.date.fromisoformat(period)).days
        lags.append(days)
    measured = [r for r in records if r.get("relative_surprise_pit") not in (None, "")]
    print(json.dumps({
        "panel": str(args.panel), "rows_in": len(rows), "prepared": len(prepared),
        "build_drops": drops, "vintage_drops": vintage_drops,
        "vintages": len(records), "measured": len(measured),
        "tickers": len({r["ticker"] for r in records}),
        "median_filing_lag_days": statistics.median(lags) if lags else None,
        "share_lag_over_300_days": round(sum(1 for lag in lags if lag > 300) / max(1, len(lags)), 3),
        "output": str(args.output),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
