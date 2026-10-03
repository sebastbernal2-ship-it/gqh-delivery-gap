#!/usr/bin/env python3
"""Build the promised-versus-realized delivery panel from monthly EIA-860M inventory vintages.

This is the chain's state variable, measured: for every generator, what date the inventory promised,
when the promise moved, and when the generator actually ran.

What it refuses to do:

- It does not pool fields or firms. Every row is one generator, and the summaries are counts.
- It does not touch the sealed window. A vintage whose conservative availability date falls on or after
  the sealed boundary is excluded and counted, never summarised.
- It does not call a moved promise an economic event. A slipped schedule is a change in what was
  published. Whether it moves cash is a later question with its own test.

Usage:
    python scripts/build_delivery_panel.py --years 2015-2023
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from edgar.filings import sealed_start  # noqa: E402
from eia.vintages import (  # noqa: E402
    availability, fetch_vintage, operating, promised, read_vintage, realizations, revisions,
)

REVISION_FIELDS = ["pair", "plant_id", "generator_id", "entity_name", "plant_name", "state",
                   "technology", "capacity_mw", "promised_before", "promised_after",
                   "revision_months", "change", "available_before", "available_after"]
REALIZATION_FIELDS = ["first_vintage", "plant_id", "generator_id", "entity_name", "plant_name", "state",
                      "technology", "capacity_mw", "promised_first", "realized", "late_months",
                      "available_from"]


def months_in_range(text: str) -> list[tuple[int, int]]:
    """A year range becomes that November of each year: one vintage per year, same month, comparable."""
    start, _, end = text.partition("-")
    return [(year, 11) for year in range(int(start), int(end or start) + 1)]


def summarise(revisions_rows: list[dict], realization_rows: list[dict], sealed: list[str]) -> str:
    lines = []
    lines.append(f"revisions: {len(revisions_rows)}   realizations: {len(realization_rows)}")
    lines.append(f"sealed vintages excluded and not summarised: {len(sealed)} {sealed if sealed else ''}")
    if revisions_rows:
        slips = [r["revision_months"] for r in revisions_rows
                 if isinstance(r.get("revision_months"), int)]
        later = [s for s in slips if s > 0]
        earlier = [s for s in slips if s < 0]
        lines.append(f"promises that moved: {len(slips)}   later: {len(later)}   earlier: {len(earlier)}")
        if later:
            lines.append(f"slipped by months: median {statistics.median(later):.0f}, "
                         f"mean {statistics.mean(later):.1f}, max {max(later)}")
        lines.append("changes that were not a shift: " +
                     ", ".join(f"{k} {v}" for k, v in
                               Counter(r["change"] for r in revisions_rows
                                       if not isinstance(r.get("revision_months"), int)).items()))
        modal = Counter(s for s in slips if s > 0).most_common(4)
        if modal:
            lines.append("most common slips in months: " +
                         ", ".join(f"{months} ({count} cases)" for months, count in modal))
        by_tech = Counter(r["technology"] for r in revisions_rows
                          if isinstance(r.get("revision_months"), int) and r["revision_months"] > 0)
        for tech, count in by_tech.most_common(6):
            lines.append(f"  {count:5d}  {tech or '(blank)'}")
    if realization_rows:
        lags = [r["late_months"] for r in realization_rows if isinstance(r.get("late_months"), int)]
        late = [x for x in lags if x > 0]
        if not lags:
            lines.append("generators that ran: no comparable promise, so no lag is reported")
            return "\n".join(lines)
        lines.append(f"generators that ran: {len(lags)}   later than promised: {len(late)}"
                     f" ({len(late) / len(lags):.0%})")
        if lags:
            lines.append(f"months late: median {statistics.median(lags):.0f}, "
                         f"mean {statistics.mean(lags):.1f}, worst {max(lags)}")
    lines.append("")
    lines.append("A revision is a published schedule that changed. It is not an economic event, and no")
    lines.append("generator, firm or technology is pooled into a single delay score.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", default="2015-2023")
    parser.add_argument("--history-start", default="2015-01-01")
    parser.add_argument("--history-end", default=dt.date.today().isoformat())
    parser.add_argument("--out-dir", default="results")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args(argv)

    months = months_in_range(args.years)
    boundary = sealed_start(dt.date.fromisoformat(args.history_start),
                            dt.date.fromisoformat(args.history_end))
    kept, sealed = [], []
    for year, month in months:
        if availability(dt.date(year, month, 1)) >= boundary:
            sealed.append(f"{year}-{month:02d}")
        else:
            kept.append((year, month))
    if not kept:
        raise SystemExit("every vintage fell in the sealed window. Widen the range or check the rule")

    parsed: list[tuple[str, dict]] = []
    for year, month in kept:
        path = fetch_vintage(year, month)
        vintage = read_vintage(path, year, month)
        parsed.append((f"{year}-{month:02d}", vintage))
        print(f"read {path.name}: {sum(len(v) for v in vintage.values())} generator rows")

    revision_rows: list[dict] = []
    for (label_a, before), (label_b, after) in zip(parsed, parsed[1:]):
        for row in revisions(before, after):
            row["pair"] = f"{label_a}->{label_b}"
            revision_rows.append(row)

    first_label, first_vintage = parsed[0]
    last_label, last_vintage = parsed[-1]
    realization_rows = []
    for row in realizations(promised(first_vintage), operating(last_vintage)):
        row["first_vintage"] = first_label
        realization_rows.append(row)

    if not args.summary:
        out_dir = ROOT / args.out_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        for name, fields, rows in (("delivery-revisions.csv", REVISION_FIELDS, revision_rows),
                                   ("delivery-realizations.csv", REALIZATION_FIELDS, realization_rows)):
            with (out_dir / name).open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)
            print(f"wrote {name} ({len(rows)} rows)")
    print(summarise(revision_rows, realization_rows, sealed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
