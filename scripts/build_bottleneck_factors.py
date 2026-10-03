#!/usr/bin/env python3
"""Build the bottleneck factor series from the shared tables, with declared publication lags.

These are the factors that pass the relevance gate: they name a payer. Construction spending in data centres,
power and electrical equipment says who is trying to build and how fast. The supply chain pressure index and
delivery times say how long they wait. Rates say what waiting costs.

Read from the shared TigerData tables rather than from the original publishers, because that is where the
team's verified landings live, and every value carries the source identifier it came from.

Values are used from two months before the decision month, which is conservative for all three publishers.

Usage:
    python scripts/build_bottleneck_factors.py
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "bottleneck-factors.csv"
FIELDS = ["month", "dc_construction_musd", "power_construction_musd", "equipment_construction_musd",
          "gscpi", "delivery_times", "ten_year", "sources"]
PUBLICATION_LAG_MONTHS = 2


def query(sql: str) -> list[dict]:
    """One read only query through the Tiger CLI, which holds the connection and the read only setting."""
    result = subprocess.run(["tiger", "db", "query", "-o", "json", "--command", sql],
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"query failed: {result.stderr.strip()[:200]}")
    payload = json.loads(result.stdout)
    out = []
    for result_set in payload.get("result_sets", []):
        columns = [c["name"] for c in result_set["columns"]]
        for row in result_set["rows"]:
            out.append(dict(zip(columns, row)))
    return out


def load_c30() -> dict[str, dict[str, float]]:
    rows = query("SELECT event_time_text, payload_json FROM public.gqh_source_records "
                 "WHERE source_id = 'census_c30'")
    out = {}
    for row in rows:
        payload = row["payload_json"] if isinstance(row["payload_json"], dict) else json.loads(row["payload_json"])
        try:
            out[row["event_time_text"][:7]] = {
                "dc_construction_musd": float(payload.get("data_center_musd", "nan")),
                "power_construction_musd": float(payload.get("power_gas_oil_musd", "nan")),
                "equipment_construction_musd": float(payload.get("computer_electronic_electrical_musd", "nan")),
            }
        except (TypeError, ValueError):
            continue
    return out


def load_gscpi() -> dict[str, float]:
    rows = query("SELECT event_time_text, payload_json FROM public.gqh_source_records "
                 "WHERE source_id = 'nyfed_gscpi'")
    out = {}
    for row in rows:
        payload = row["payload_json"] if isinstance(row["payload_json"], dict) else json.loads(row["payload_json"])
        try:
            out[str(payload.get("observation_date"))[:7]] = float(payload["gscpi"])
        except (KeyError, TypeError, ValueError):
            continue
    return out


def load_delivery_times() -> dict[str, float]:
    """The Philadelphia Fed survey's delivery times diffusion index, current, seasonally adjusted."""
    rows = query("SELECT event_time_text, payload_json FROM public.gqh_source_records "
                 "WHERE source_id = 'philly_delivery_times'")
    out = {}
    months = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8,
              "sep": 9, "oct": 10, "nov": 11, "dec": 12}
    for row in rows:
        payload = row["payload_json"] if isinstance(row["payload_json"], dict) else json.loads(row["payload_json"])
        stamp = str(payload.get("DATE", ""))
        if "-" not in stamp:
            continue
        name, year = stamp.split("-")
        month = months.get(name.strip().lower()[:3])
        if month is None:
            continue
        year_number = int(year) + (1900 if int(year) > 50 else 2000)
        try:
            # dtcdsa is the current, diffusion, seasonally adjusted delivery times index: positive means
            # deliveries are taking longer than the month before.
            out[f"{year_number:04d}-{month:02d}"] = float(payload["dtcdsa"])
        except (KeyError, TypeError, ValueError):
            continue
    return out


def load_ten_year() -> dict[str, float]:
    rows = query("SELECT event_time_text, payload_json FROM public.gqh_source_records "
                 "WHERE source_id = 'fred_rates' AND payload_json::text ILIKE '%ten_year%' LIMIT 4000")
    out: dict[str, list[float]] = {}
    for row in rows:
        payload = row["payload_json"] if isinstance(row["payload_json"], dict) else json.loads(row["payload_json"])
        value = payload.get("value") or payload.get("DGS10")
        stamp = str(payload.get("observation_date") or row["event_time_text"])[:10]
        if value in (None, "", "."):
            continue
        try:
            out.setdefault(stamp[:7], []).append(float(value))
        except (TypeError, ValueError):
            continue
    return {month: sum(values) / len(values) for month, values in out.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(OUT.relative_to(ROOT)))
    args = parser.parse_args(argv)

    c30 = load_c30()
    gscpi = load_gscpi()
    delivery = load_delivery_times()
    ten_year = load_ten_year()
    print(f"c30 months {len(c30)} | gscpi {len(gscpi)} | delivery times {len(delivery)} | "
          f"ten year {len(ten_year)}")

    months = sorted(set(c30) | set(gscpi) | set(delivery) | set(ten_year))
    rows = []
    for month in months:
        if month < "2014-01" or month > "2022-09":
            continue
        record = {"month": month, "gscpi": gscpi.get(month), "delivery_times": delivery.get(month),
                  "ten_year": ten_year.get(month), "sources": "census_c30;nyfed_gscpi;"
                  "philly_delivery_times;fred_rates"}
        record.update(c30.get(month, {"dc_construction_musd": None, "power_construction_musd": None,
                                      "equipment_construction_musd": None}))
        rows.append(record)

    out = ROOT / args.out
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {args.out}: {len(rows)} months, {rows[0]['month']} to {rows[-1]['month']}")
    print(f"declared publication lag for use: {PUBLICATION_LAG_MONTHS} months")
    for name in ("dc_construction_musd", "power_construction_musd", "equipment_construction_musd",
                 "gscpi", "delivery_times", "ten_year"):
        filled = sum(1 for row in rows if row[name] is not None)
        print(f"  {name:28s} {filled:>4d} of {len(rows)} months")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
