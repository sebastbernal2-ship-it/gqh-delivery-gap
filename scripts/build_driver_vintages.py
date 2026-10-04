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




Z_EDGES = (-1.5, -0.5, 0.5, 1.5)          # declared edges for the standardized surprise
Z_CLIP = 5.0
VOL_WINDOW = 8                             # prior relative changes used for the trailing volatility
VOL_FLOOR = 0.005                          # a floor keeps the ratio finite for very calm series
VOL_MINIMUM = 4                            # fewer prior changes than this and no z is published


def apply_zscore(records: list[dict]) -> tuple[list[dict], dict]:
    """Scale the surprise and the change by each ticker's own trailing volatility of changes.

    The declared bin edges are calibrated for series that swing by about ten percent a quarter, so a
    balance-sheet level that moves two percent lands in one bin and a series with a tiny denominator
    throws outliers that dominate the fit. Dividing by the trailing volatility of the *change* makes
    the target dimensionless and concept agnostic, and the clip keeps single rows from owning the fit.
    Only vintages available before the row in question enter its volatility, so the clock is intact.
    """
    import statistics

    by_ticker: dict[str, list[dict]] = {}
    for record in records:
        by_ticker.setdefault(record["ticker"], []).append(record)
    published = 0
    dropped = 0
    for ticker, items in by_ticker.items():
        items.sort(key=lambda record: str(record.get("availability") or ""))
        history: list[float] = []
        for record in items:
            try:
                change = float(record["change"])
                previous = float(record["previous_value"])
            except (KeyError, TypeError, ValueError):
                history.append(0.0)
                continue
            relative_change = (change / abs(previous)) if previous else None
            if len(history) >= VOL_MINIMUM:
                volatility = max(statistics.stdev(history[-VOL_WINDOW:]), VOL_FLOOR)
                raw_surprise = record.get("relative_surprise_pit")
                if raw_surprise not in (None, ""):
                    z = float(raw_surprise) / volatility
                    record["relative_surprise_z"] = max(-Z_CLIP, min(Z_CLIP, z))
                    published += 1
                if relative_change is not None:
                    record["change_relative_z"] = max(-Z_CLIP, min(Z_CLIP, relative_change / volatility))
                record["label_edges"] = ",".join(str(edge) for edge in Z_EDGES)
            else:
                dropped += 1
            if relative_change is not None:
                history.append(relative_change)
    return records, {"z_published": published, "z_without_volatility": dropped,
                     "vol_window": VOL_WINDOW, "vol_floor": VOL_FLOOR, "clip": Z_CLIP}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--preferred", default="")
    parser.add_argument("--scale", choices=("raw", "zscore"), default="raw",
                        help="zscore: surprise and change scaled by trailing volatility of changes")
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
    zscored = {}
    if args.scale == "zscore":
        records, zscored = apply_zscore(records)

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
        "vintages": len(records), "measured": len(measured), "zscore": zscored,
        "tickers": len({r["ticker"] for r in records}),
        "median_filing_lag_days": statistics.median(lags) if lags else None,
        "share_lag_over_300_days": round(sum(1 for lag in lags if lag > 300) / max(1, len(lags)), 3),
        "output": str(args.output),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
