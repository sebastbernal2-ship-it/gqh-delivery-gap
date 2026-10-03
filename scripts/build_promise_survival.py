#!/usr/bin/env python3
"""Turn the modal twelve month slip into a survival curve.

The earlier measurement reported how often a promise moved and by how much. This one asks a sharper
question: **how long does a published promise live before it is revised, and does that depend on age.** The
answer is a hazard rate, which is a better object than a mean, and it is measurable on data already held.

Declared before estimation:

- **Event**: the first vintage in which a generator's promised operation month differs from its previous
  observed promise.
- **Duration**: months from the generator's first appearance in a vintage to that vintage.
- **Censoring**: a generator still carrying its original promise when it leaves the planned sheet is
  right censored at its last appearance, rather than being counted as revised or dropped.
- **Window**: development vintages only, July 2015 to September 2022, because the mechanism study's holdout
  starts in October 2022 and nothing here may read it.
- **Falsifier**: if the hazard is flat in duration within a technology, then promises are memoryless and
  there is no schedule structure worth modelling.

Usage:
    python scripts/build_promise_survival.py
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from eia.vintages import fetch_vintage, read_vintage  # noqa: E402
from scan.windows import MECHANISM  # noqa: E402

FIELDS = ["plant_id", "generator_id", "technology", "state", "capacity_mw", "vintages_observed",
          "duration_months", "revised", "first_promise", "last_promise", "slip_months"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2015-07")
    parser.add_argument("--end", default="2022-09")
    parser.add_argument("--out", default="results/promise-survival.csv")
    args = parser.parse_args(argv)

    start_year, start_month = (int(p) for p in args.start.split("-"))
    end_year, end_month = (int(p) for p in args.end.split("-"))
    if f"{end_year:04d}-{end_month:02d}" > MECHANISM.development_end:
        raise SystemExit("refusing to read past the declared development window")

    # One pass per vintage, cached, because the survival question needs ninety of them.
    cache_dir = ROOT / "data" / "promise-series"
    cache_dir.mkdir(parents=True, exist_ok=True)
    observed: dict[tuple[str, str], list[tuple[str, str, str, str, str, str]]] = defaultdict(list)
    months: list[str] = []
    year, month = start_year, start_month
    while (year, month) <= (end_year, end_month):
        stamp = f"{year:04d}-{month:02d}"
        cached = cache_dir / f"{stamp}.jsonl"
        if cached.exists():
            rows_for_month = [json.loads(line) for line in cached.read_text().splitlines() if line.strip()]
        else:
            path = fetch_vintage(year, month)
            vintage = read_vintage(path, year, month)
            rows_for_month = [{"plant_id": g.plant_id, "generator_id": g.generator_id,
                               "statement": g.statement, "technology": g.technology, "state": g.state,
                               "capacity_mw": g.capacity_mw, "entity_name": g.entity_name}
                              for g in vintage.get("Planned", [])]
            cached.write_text("\n".join(json.dumps(r) for r in rows_for_month) + "\n")
        for row in rows_for_month:
            observed[(row["plant_id"], row["generator_id"])].append(
                (stamp, row["statement"], row["technology"], row["state"], row["capacity_mw"],
                 row["entity_name"]))
        months.append(stamp)
        print(f"{stamp}: {len(rows_for_month)} planned generators tracked")
        month += 1
        if month == 13:
            year, month = year + 1, 1

    def month_index(stamp: str) -> int:
        return int(stamp[:4]) * 12 + int(stamp[5:7])

    def readable(statement: str) -> bool:
        """A promise with no month is missing, not changed. It is skipped rather than compared."""
        return bool(statement) and len(str(statement)) == 7 and str(statement)[4] == "-"

    rows = []
    for (plant_id, generator_id), sightings in observed.items():
        sightings.sort()
        first_stamp, first_promise, technology, state, capacity, _entity = sightings[0]
        durations, revised, slip = 0, 0, 0
        baseline = next((s for _stamp, s, *_rest in sightings if readable(s)), "")
        last_promise = baseline
        for stamp, promise, *_rest in sightings:
            if not readable(promise):
                continue
            if promise != last_promise:
                durations = month_index(stamp) - month_index(first_stamp)
                revised = 1
                slip = month_index(promise) - month_index(last_promise)
                last_promise = promise
                break
        if not revised:
            durations = month_index(sightings[-1][0]) - month_index(first_stamp)
        rows.append({"plant_id": plant_id, "generator_id": generator_id, "technology": technology,
                     "state": state, "capacity_mw": capacity, "vintages_observed": len(sightings),
                     "duration_months": durations, "revised": revised,
                     "first_promise": first_promise, "last_promise": last_promise, "slip_months": slip})

    out = ROOT / args.out
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {args.out} ({len(rows)} generators, window {months[0]} to {months[-1]})")

    revised_rows = [r for r in rows if r["revised"]]
    print("")
    print(f"generators tracked: {len(rows)}   revised inside the window: {len(revised_rows)} "
          f"({len(revised_rows) / len(rows):.0%})")
    durations = sorted(r["duration_months"] for r in revised_rows)
    if durations:
        print(f"months to first revision: median {statistics.median(durations):.0f}, "
              f"quartiles {durations[len(durations)//4]} and {durations[3*len(durations)//4]}")
    print("")
    print("hazard by age bucket, over generators still carrying their original promise:")
    buckets = [(0, 6), (6, 12), (12, 24), (24, 36), (36, 999)]
    for low, high in buckets:
        at_risk = [r for r in rows if r["duration_months"] >= low]
        events = [r for r in revised_rows if low <= r["duration_months"] < high]
        rate = len(events) / len(at_risk) if at_risk else float("nan")
        print(f"  {low:2d} to {high if high < 999 else '+':>3} months: at risk {len(at_risk):6d}, "
              f"revised {len(events):5d}, rate {rate:.3f}")
    print("")
    print("by technology, median months to revision:")
    by_tech: dict[str, list[int]] = defaultdict(list)
    for row in revised_rows:
        by_tech[row["technology"]].append(row["duration_months"])
    for technology, values in sorted(by_tech.items(), key=lambda kv: -len(kv[1]))[:8]:
        print(f"  {technology[:44]:44s} n={len(values):5d} median {statistics.median(values):.0f}")
    print("")
    print("If the rate rises with age, promises do not become safer as they age, which is the opposite of")
    print("what a naive reading of a completion date would suggest. A flat rate would falsify that reading.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
