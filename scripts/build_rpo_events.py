#!/usr/bin/env python3
"""Pass two: turn the industry universe into timestamped revisions with an expectation.

For each selected company: the reported value of remaining performance obligations per period, the
change against the previous report, and a surprise measured against that company's own typical change.

Where the timestamp comes from, stated plainly:

- an **acceptance timestamp** when the filings register holds that accession (the four pilot firms)
- otherwise the **filing date at end of day**, flagged in ``availability_resolution``

The second is coarser, and mixing resolutions is visible in the data rather than hidden in a default.

Usage:
    python scripts/build_rpo_events.py --include-placebo
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_rpo_universe import CACHE, CONCEPT, fetch_json, frame_rows, quarters  # noqa: E402
from edgar.filings import sealed_start  # noqa: E402
from edgar.xbrl import facts_url  # noqa: E402

FIELDS = ["cik", "name", "ticker", "sic", "group", "period_end", "value", "previous_value", "change",
          "typical_change", "surprise", "form", "accession", "earliest_availability_utc",
          "availability_resolution", "in_sealed_window", "source_receipt"]


def facts_by_cik(period_list: list[str]) -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = defaultdict(list)
    for period in period_list:
        for row in frame_rows(period, CACHE):
            out[int(row["cik"])].append(row)
    for rows in out.values():
        rows.sort(key=lambda r: (r["end"], r["accn"]))
    return out


def filed_dates(cik: int) -> dict[str, tuple[str, str]]:
    payload = fetch_json(facts_url(cik), CACHE)
    out: dict[str, tuple[str, str]] = {}
    for entries in (payload.get("facts") or {}).values():
        for name, body in entries.items():
            if name != CONCEPT:
                continue
            for facts in (body.get("units") or {}).values():
                for fact in facts:
                    accession = fact.get("accn")
                    if accession and accession not in out:
                        out[accession] = (fact.get("filed", ""), fact.get("form", ""))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe", default="results/rpo-universe.csv")
    parser.add_argument("--register", default="results/filings-register.csv")
    parser.add_argument("--start-quarter", default="2015Q1")
    parser.add_argument("--end-quarter", default="2024Q3")
    parser.add_argument("--history-start", default="2015-01-01")
    parser.add_argument("--history-end", default=dt.date.today().isoformat())
    parser.add_argument("--include-placebo", action="store_true",
                        help="also process the group that is not in a declared industry")
    parser.add_argument("--limit", type=int, default=0, help="stop early, for a smoke test")
    parser.add_argument("--out", default="results/rpo-events.csv")
    args = parser.parse_args(argv)

    boundary = sealed_start(dt.date.fromisoformat(args.history_start),
                           dt.date.fromisoformat(args.history_end))
    with (ROOT / args.universe).open() as handle:
        universe = [row for row in csv.DictReader(handle)
                    if args.include_placebo or row["group"] != "other"]
    if args.limit:
        universe = universe[:args.limit]

    register = {}
    register_path = ROOT / args.register
    if register_path.exists():
        with register_path.open() as handle:
            register = {row["accession"]: row["acceptance_utc"] for row in csv.DictReader(handle)}

    by_cik = facts_by_cik(quarters(args.start_quarter, args.end_quarter))
    print(f"processing {len(universe)} companies")

    events: list[dict] = []
    for index, company in enumerate(universe, start=1):
        cik = int(company["cik"])
        rows = by_cik.get(cik, [])
        if not rows:
            continue
        filed = filed_dates(cik)
        values: list[float] = []
        changes: list[float] = []
        for row in rows:
            if not isinstance(row.get("val"), (int, float)):
                continue
            value = float(row["val"])
            acceptance = register.get(row["accn"], "")
            filed_date, form = filed.get(row["accn"], ("", ""))
            availability = acceptance or (f"{filed_date}T23:59:59+00:00" if filed_date else "")
            change = value - values[-1] if values else None
            typical = statistics.median(changes) if changes else None
            events.append({
                "cik": cik, "name": company["name"], "ticker": company["ticker"],
                "sic": company["sic"], "group": company["group"], "period_end": row["end"],
                "value": value, "previous_value": values[-1] if values else "",
                "change": change if change is not None else "",
                "typical_change": typical if typical is not None else "",
                "surprise": (change - typical) if (change is not None and typical is not None) else "",
                "form": form, "accession": row["accn"],
                "earliest_availability_utc": availability,
                "availability_resolution": ("acceptance timestamp" if acceptance
                                            else "filing date, end of day" if filed_date
                                            else "unknown"),
                "in_sealed_window": bool(availability and availability[:10] >= boundary.isoformat()),
                "source_receipt": facts_url(cik),
            })
            values.append(value)
            if change is not None:
                changes.append(change)
        if index % 50 == 0:
            print(f"  {index}/{len(universe)} companies, {len(events)} events")

    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(events)
    print(f"wrote {args.out} ({len(events)} events)")

    sealed = [e for e in events if e["in_sealed_window"]]
    usable = [e for e in events if not e["in_sealed_window"] and e["surprise"] != ""]
    by_group: dict[str, dict] = defaultdict(lambda: {"companies": set(), "events": 0, "usable": 0,
                                                     "acceptance": 0})
    for event in events:
        bucket = by_group[event["group"]]
        bucket["companies"].add(event["cik"])
        bucket["events"] += 1
        if event["availability_resolution"] == "acceptance timestamp":
            bucket["acceptance"] += 1
        if not event["in_sealed_window"] and event["surprise"] != "":
            bucket["usable"] += 1
    print("")
    print(f"{'group':11s} {'companies':>9s} {'events':>7s} {'with surprise':>13s} {'acceptance':>10s}")
    for group, bucket in sorted(by_group.items(), key=lambda kv: -kv[1]["usable"]):
        print(f"{group:11s} {len(bucket['companies']):>9d} {bucket['events']:>7d} "
              f"{bucket['usable']:>13d} {bucket['acceptance']:>10d}")
    print(f"\nsealed events flagged and excluded from every summary: {len(sealed)}")
    print(f"events usable in the development window: {len(usable)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
