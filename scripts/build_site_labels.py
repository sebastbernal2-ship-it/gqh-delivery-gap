#!/usr/bin/env python3
"""Pick sites with a known promise and a known outcome, and record where they are.

The imagery direction needs labelled examples: a project that was promised for one date, published as
operating in another vintage, and whose location is known. EIA carries latitude and longitude, so the labels
come from data already held rather than from a search.

Selection rule, declared before any imagery is fetched: generators that appear in the **operating** sheet of
a later development vintage and were in the **planned** sheet of an earlier one, with a promised month at
least three months away from the realised month, with usable coordinates, taking the largest by capacity.
The three month gap is there because a measure that cannot separate a six month slip is not worth building.

Usage:
    python scripts/build_site_labels.py --pairs 8
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from eia.vintages import fetch_vintage, read_vintage  # noqa: E402

FIELDS = ["plant_id", "generator_id", "plant_name", "entity_name", "technology", "state",
          "capacity_mw", "latitude", "longitude", "promised", "realized", "slip_months",
          "promise_vintage", "realized_vintage"]


def month_index(stamp: str) -> int:
    return int(stamp[:4]) * 12 + int(stamp[5:7])


def coordinates(path) -> dict:
    """Latitude and longitude by plant, from the operating sheet of one vintage.

    Rows can be shorter than the header, so every field is read through the guarded helper rather than by
    position, which is the same mistake that blanked the early vintages once already.
    """
    from eia.vintages import cell
    from eia.xlsx import find_header, read_sheet
    sheet = read_sheet(path, "Operating")
    header = sheet[find_header(sheet)]
    out = {}
    for row in sheet[find_header(sheet) + 1:]:
        plant = cell(row, header, "Plant ID").strip()
        if not plant or plant in out:
            continue
        try:
            lat = float(cell(row, header, "Latitude"))
            lon = float(cell(row, header, "Longitude"))
        except ValueError:
            continue
        out[plant] = (lat, lon)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--promise", default="2019-11", help="vintage whose promise is compared")
    parser.add_argument("--realized", default="2022-09", help="vintage that reports the outcome")
    parser.add_argument("--pairs", type=int, default=8)
    parser.add_argument("--out", default="results/site-labels.csv")
    args = parser.parse_args(argv)

    promise_year, promise_month = (int(p) for p in args.promise.split("-"))
    realized_year, realized_month = (int(p) for p in args.realized.split("-"))
    promised_vintage = read_vintage(fetch_vintage(promise_year, promise_month),
                                   promise_year, promise_month)
    realized_path = fetch_vintage(realized_year, realized_month)
    realized_vintage = read_vintage(realized_path, realized_year, realized_month)
    where = coordinates(realized_path)

    promised = {(g.plant_id, g.generator_id): g for g in promised_vintage.get("Planned", [])}
    running = {(g.plant_id, g.generator_id): g for g in realized_vintage.get("Operating", [])}

    candidates = []
    for key, promise in promised.items():
        actual = running.get(key)
        if actual is None or not promise.statement or not actual.realized:
            continue
        if promise.plant_id not in where:
            continue
        slip = month_index(actual.realized) - month_index(promise.statement)
        if abs(slip) < 3:
            continue
        try:
            capacity = float(promise.capacity_mw)
        except ValueError:
            capacity = 0.0
        latitude, longitude = where[promise.plant_id]
        candidates.append({"plant_id": promise.plant_id, "generator_id": promise.generator_id,
                           "plant_name": promise.plant_name, "entity_name": promise.entity_name,
                           "technology": promise.technology, "state": promise.state,
                           "capacity_mw": capacity, "latitude": latitude, "longitude": longitude,
                           "promised": promise.statement, "realized": actual.realized,
                           "slip_months": slip, "promise_vintage": args.promise,
                           "realized_vintage": args.realized})

    candidates.sort(key=lambda row: -row["capacity_mw"])
    chosen = candidates[:args.pairs]
    out = ROOT / args.out
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(chosen)
    print(f"wrote {args.out}: {len(chosen)} labelled sites of {len(candidates)} candidates")
    for row in chosen:
        print(f"  {row['plant_name'][:30]:30s} {row['state']:3s} {row['capacity_mw']:6.0f} MW "
              f"promised {row['promised']} realized {row['realized']} ({row['slip_months']:+d} months) "
              f"at {row['latitude']:.4f},{row['longitude']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
