#!/usr/bin/env python3
"""Aggregate the open EIA-930 six-month files into one daily regional load panel.

Every hourly row is a balancing authority. The panel keeps, per balancing authority and local date:
the mean and peak demand, the mean net generation, and the mean solar, wind, gas and nuclear output.
No key, no rate limit, and the source files are the grid monitor's published six-month balance files.

    python3 scripts/build_eia930_load_panel.py
"""
from __future__ import annotations

import argparse
import csv
import gzip
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ("authority", "date", "hours", "demand_mean", "demand_peak", "demand_min",
          "demand_ramp_mean", "net_generation_mean", "solar_mean", "wind_mean", "gas_mean",
          "nuclear_mean")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=ROOT / "results" / "eia-raw")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "eia-load-daily.csv.gz")
    args = parser.parse_args()

    buckets: dict[tuple[str, str], dict] = {}
    files = sorted(args.raw.glob("EIA930_BALANCE_*.csv"))
    if not files:
        raise SystemExit(f"no source files under {args.raw}")
    for path in files:
        with path.open(newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader)
            index = {name: position for position, name in enumerate(header)}

            def column(*names):
                for name in names:
                    if name in index:
                        return index[name]
                return None

            demand = column("Demand (MW)")
            generation = column("Net Generation (MW)")
            solar = column("Net Generation (MW) from Solar without Integrated Battery Storage")
            solar_battery = column("Net Generation (MW) from Solar with Integrated Battery Storage")
            wind = column("Net Generation (MW) from Wind without Integrated Battery Storage")
            wind_battery = column("Net Generation (MW) from Wind with Integrated Battery Storage")
            gas = column("Net Generation (MW) from Natural Gas")
            nuclear = column("Net Generation (MW) from Nuclear")
            for row in reader:
                if len(row) <= max(filter(None, (demand, generation))):
                    continue
                authority = row[0].strip()
                day = row[1].strip()
                if not authority or not day:
                    continue
                key = (authority, day)
                bucket = buckets.setdefault(key, {"hours": 0, "demand": [], "generation": [],
                                                  "solar": [], "wind": [], "gas": [], "nuclear": [],
                                                  "ramps": [], "previous": None})

                def value(position, sink):
                    if position is None:
                        return
                    raw = row[position].strip() if position < len(row) else ""
                    if raw:
                        try:
                            sink.append(float(raw))
                        except ValueError:
                            pass

                before = len(bucket["demand"])
                value(demand, bucket["demand"])
                if len(bucket["demand"]) > before:          # an hour-to-hour ramp needs the lag
                    current = bucket["demand"][-1]
                    if bucket["previous"] is not None:
                        bucket["ramps"].append(abs(current - bucket["previous"]))
                    bucket["previous"] = current
                value(generation, bucket["generation"])
                for position in (solar, solar_battery):
                    value(position, bucket["solar"])
                for position in (wind, wind_battery):
                    value(position, bucket["wind"])
                value(gas, bucket["gas"])
                value(nuclear, bucket["nuclear"])
                bucket["hours"] += 1
        print("parsed", path.name, "| buckets so far", len(buckets), file=sys.stderr)

    def mean(values):
        return round(statistics.mean(values), 1) if values else ""

    with gzip.open(args.output, "wt", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(FIELDS))
        writer.writeheader()
        for (authority, day), bucket in sorted(buckets.items()):
            writer.writerow({
                "authority": authority, "date": day, "hours": bucket["hours"],
                "demand_mean": mean(bucket["demand"]),
                "demand_peak": max(bucket["demand"]) if bucket["demand"] else "",
                "demand_min": min(bucket["demand"]) if bucket["demand"] else "",
                "demand_ramp_mean": mean(bucket["ramps"]),
                "net_generation_mean": mean(bucket["generation"]),
                "solar_mean": mean(bucket["solar"]), "wind_mean": mean(bucket["wind"]),
                "gas_mean": mean(bucket["gas"]), "nuclear_mean": mean(bucket["nuclear"])})
    size = args.output.stat().st_size
    authorities = len({key[0] for key in buckets})
    dates = sorted({key[1] for key in buckets})
    print("wrote %s | %d rows | %d authorities | %s .. %s | %.1f MB" % (
        args.output, len(buckets), authorities, dates[0] if dates else "n/a",
        dates[-1] if dates else "n/a", size / 1e6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
