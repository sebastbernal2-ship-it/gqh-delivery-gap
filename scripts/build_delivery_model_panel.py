#!/usr/bin/env python3
"""Build the panel: one row per project month at risk, with factors known before that month.

The object is the thing itself, not a price. A promise is at risk from the month it first appears until the
month it first moves, and every month in between is a row. The outcome is whether it moved in that month.

Every factor is lagged to what was knowable. Weather enters the project state through its declared publication
lag. Drought, fuel, rates, market wide lead time and the state congestion proxy enter at t-1. Project controls
are technology, size, age and start year.

Nothing here reads a return, and the panel covers the mechanism study development window only.

Usage:
    python scripts/build_delivery_model_panel.py --out results/delivery-model-panel.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from factors.backlog import monthly_group_readings, trailing_growth  # noqa: E402
from factors.drought import severity  # noqa: E402
from factors.market import known_at as market_known_at, levels  # noqa: E402
from factors.queue import state_panel  # noqa: E402
from factors.weather import known_at as weather_known_at, monthly_series, state_anomaly, state_codes  # noqa: E402

CACHE = ROOT / "data" / "promise-series"
ENVIRONMENT_FACTORS = ["precip_anomaly", "drought_severity", "gas_level", "rate_level",
                       "lead_time_share_negative", "lead_time_growth", "pipeline_momentum",
                       "promise_horizon_months"]
# The bottleneck set passes the relevance gate: every one of these names a payer. Construction spending says
# who is trying to build, supply chain pressure and delivery times say how long they wait.
BOTTLENECK_FACTORS = ["dc_construction_musd", "power_construction_musd", "equipment_construction_musd",
                      "gscpi", "delivery_times", "promise_horizon_months", "pipeline_momentum"]
FACTORS = ENVIRONMENT_FACTORS
FIELDS = ["month", "state", "technology", "capacity", "log_capacity", "age_months", "start_year",
          "event", "event_large", "event_withdraw", "slip_months"] + FACTORS

# The tail definition, declared in docs/plan/object-redefinition.md: a revision of six months or more is the
# part of the outcome that carries information, because 36 percent of first revisions are one month nudges.
LARGE_SLIP_MONTHS = 6


def month_index(stamp: str) -> int:
    return int(stamp[:4]) * 12 + int(stamp[5:7])


def shift_month(stamp: str, months: int) -> str:
    total = month_index(stamp) + months
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def load_generators() -> dict[tuple[str, str], list[tuple[str, str, str, str, str]]]:
    observed: dict[tuple[str, str], list[tuple[str, str, str, str, str]]] = defaultdict(list)
    for path in sorted(CACHE.glob("*.jsonl")):
        stamp = path.stem
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            observed[(row["plant_id"], row["generator_id"])].append(
                (stamp, row.get("statement") or "", row.get("technology") or "",
                 row.get("state") or "", row.get("capacity_mw") or ""))
    for sightings in observed.values():
        sightings.sort()
    return observed


def mean_of(values: list) -> float | None:
    present = [v for v in values if v is not None and v == v]
    return statistics.mean(present) if present else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="results/delivery-model-panel.csv")
    parser.add_argument("--outcomes", action="store_true",
                        help="add the large revision and suspected withdrawal columns")
    parser.add_argument("--end", default="2022-09")
    parser.add_argument("--factor-set", choices=("environment", "bottleneck"), default="environment")
    args = parser.parse_args(argv)
    factors = BOTTLENECK_FACTORS if args.factor_set == "bottleneck" else ENVIRONMENT_FACTORS
    fields = ["month", "state", "technology", "capacity", "log_capacity", "age_months", "start_year",
              "event", "event_large", "event_withdraw", "slip_months"] + factors

    observed = load_generators()
    vintage_stamps = sorted(path.stem for path in CACHE.glob("*.jsonl"))
    print(f"generators in the cache: {len(observed)}, vintages: {len(vintage_stamps)}")

    codes = state_codes()
    states = sorted({sightings[0][3] for sightings in observed.values() if sightings[0][3]})
    print(f"states in the panel: {len(states)}")
    precip = {state: state_anomaly(monthly_series(state, "pcp", 2015, 2024, codes=codes)) for state in states}
    drought = {state: severity(state) for state in states}
    print(f"  weather available for {sum(1 for s in states if precip.get(s))} states, "
          f"drought for {sum(1 for s in states if drought.get(s))}")
    market = levels()
    backlog = monthly_group_readings()
    lead_share = {g: {m: v["share_negative"] for m, v in r.items()} for g, r in backlog.items()}
    lead_growth = {g: trailing_growth(r) for g, r in backlog.items()}
    congestion = state_panel()
    bottleneck: dict[str, dict[str, float]] = {}
    if args.factor_set == "bottleneck":
        import csv as _csv
        source = ROOT / "results" / "bottleneck-factors.csv"
        if not source.exists():
            raise SystemExit("run scripts/build_bottleneck_factors.py first")
        with source.open() as handle:
            for row in _csv.DictReader(handle):
                bottleneck[row["month"]] = row
        print(f"bottleneck months available: {len(bottleneck)}")

    rows: list[dict] = []
    events = 0
    large_events = 0
    withdraw_events = 0
    technologies: dict[str, int] = defaultdict(int)
    for sightings in observed.values():
        readable = [(stamp, promise) for stamp, promise, *_ in sightings if len(promise) == 7]
        if len(readable) < 2:
            continue
        first_stamp, baseline = readable[0]
        technology, state = sightings[0][2], sightings[0][3]
        try:
            capacity = float(sightings[0][4])
        except (TypeError, ValueError):
            capacity = 0.0
        technologies[technology] += 1
        event_month = next((stamp for stamp, promise in readable[1:] if promise != baseline), None)
        moved_to = next((promise for stamp, promise in readable[1:] if promise != baseline), None)
        slip = (month_index(moved_to) - month_index(baseline)) if moved_to else None
        # Suspected withdrawal: the generator stops appearing while its promise was still in the future, and it
        # is absent again in the next available vintage. An early completion also removes a unit from the
        # planned sheet, so the share is reported rather than assumed away.
        withdraw_month = None
        last_stamp, last_promise = readable[-1]
        if event_month is None and month_index(last_promise) > month_index(last_stamp):
            later = [stamp for stamp in vintage_stamps if stamp > last_stamp]
            if len(later) >= 2:
                withdraw_month = later[0]
        final_month = event_month or withdraw_month or sightings[-1][0]
        if final_month > args.end:
            final_month = args.end
        month = first_stamp
        while month <= final_month:
            previous = shift_month(month, -1)
            congestion_row = congestion.get((state, previous), {})
            record = {
                "month": month, "state": state, "technology": technology, "capacity": capacity,
                "log_capacity": round(math.log1p(capacity), 4),
                "age_months": month_index(month) - month_index(first_stamp),
                "start_year": int(first_stamp[:4]),
                "event": 1 if month == event_month else 0,
                "event_large": 1 if (event_month and month == event_month
                                     and slip is not None and slip >= LARGE_SLIP_MONTHS) else 0,
                "event_withdraw": 1 if month == withdraw_month else 0,
                "slip_months": slip if month == event_month else "",
                "precip_anomaly": weather_known_at(month, precip.get(state, {})),
                "drought_severity": drought.get(state, {}).get(previous),
                "gas_level": market_known_at(month, market.get("gas", {})),
                "rate_level": market_known_at(month, market.get("ten_year", {})),
                "lead_time_share_negative": mean_of([lead_share.get(g, {}).get(previous)
                                                     for g in ("contractor", "equipment")]),
                "lead_time_growth": mean_of([lead_growth.get(g, {}).get(previous)
                                             for g in ("contractor", "equipment")]),
                "pipeline_momentum": congestion_row.get("pipeline_momentum"),
                "promise_horizon_months": congestion_row.get("promise_horizon_months"),
            }
            if args.factor_set == "bottleneck":
                # Two months of lag, declared as conservative for all three publishers.
                source_month = shift_month(month, -2)
                source_row = bottleneck.get(source_month, {})
                for factor in BOTTLENECK_FACTORS:
                    raw = source_row.get(factor)
                    try:
                        record[factor] = float(raw) if raw not in (None, "") else None
                    except (TypeError, ValueError):
                        record[factor] = None
                record["promise_horizon_months"] = congestion_row.get("promise_horizon_months")
                record["pipeline_momentum"] = congestion_row.get("pipeline_momentum")
            rows.append(record)
            events += record["event"]
            large_events += record["event_large"]
            withdraw_events += record["event_withdraw"]
            month = shift_month(month, 1)

    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"wrote {args.out}: {len(rows)} project months, {events} revision months "
          f"({events / len(rows):.1%})")
    print(f"  large revisions (six months or more): {large_events} ({large_events / len(rows):.2%})")
    print(f"  suspected withdrawals: {withdraw_events} ({withdraw_events / len(rows):.2%})")
    print("factor coverage:")
    for factor in factors:
        present = sum(1 for row in rows if row[factor] is not None and row[factor] == row[factor])
        print(f"  {factor:26s} {present:7d} of {len(rows)} ({present / len(rows):5.1%})")
    print("technologies:", dict(sorted(technologies.items(), key=lambda kv: -kv[1])[:6]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
