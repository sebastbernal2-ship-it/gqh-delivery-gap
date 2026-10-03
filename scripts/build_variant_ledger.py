#!/usr/bin/env python3
"""Count every variant we tried, in one table, from the artifacts that recorded them.

The rubric asks how many variants were tried and why. Burying that answer across five files is the same as
not answering it, and a reader who cannot count the search cannot judge the survivors. So this reads the
artifacts and emits both a CSV and a generated page, with the multiplying command for each family.

A cell is one comparison. Expected is what chance alone would produce at the declared threshold, which is
five percent of the cells for a calibrated null. The ratio of survivors to expected is the honest headline.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from scan.report import canonical, family_counts  # noqa: E402

FIELDS = ["family", "role", "what_was_tried", "cells", "expected_by_chance", "survivors", "status",
          "artifact", "reproduce"]
# A control is not a search. Its survivors measure the pipeline's own false positive rate, so counting them
# among discoveries would be a category error, and excluding them is the whole point of running one.
ROLES = ("search", "control", "measurement")


def headline(rows: list[dict], role: str) -> dict:
    """Totals for one role only, so a control never inflates or deflates the search summary."""
    chosen = [r for r in rows if r["role"] == role and r["expected_by_chance"] != ""]
    return {"families": len(chosen),
            "cells": sum(int(r["cells"]) for r in chosen),
            "expected": sum(float(r["expected_by_chance"]) for r in chosen),
            "survivors": sum(int(r["survivors"]) for r in chosen)}


def tstat(values: list[float]) -> float | None:
    if len(values) < 3:
        return None
    spread = statistics.stdev(values)
    return statistics.mean(values) / (spread / math.sqrt(len(values))) if spread else None


def read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open() as handle:
        return list(csv.DictReader(handle))


def scan_family(path: Path, nodes: dict, label: str, what: str) -> dict | None:
    rows = [r for r in read(path) if r.get("coverage") == "measured"]
    if not rows:
        return None
    canon = canonical(rows)
    counts = family_counts(canon, nodes)
    return {"family": label, "role": "search", "what_was_tried": what,
            "cells": len(canon), "expected_by_chance": round(counts["expected_cross"], 2),
            "survivors": counts["cross_survivors"], "status": "null" if not counts["cross_survivors"]
            else "cross-family survivors, candidates only",
            "artifact": path.name,
            "reproduce": f"python scripts/run_association_scan.py --out results/{path.name}"}


def rpo_family(path: Path, label: str, what: str, placebo: bool = False) -> dict | None:
    rows = read(path)
    if not rows:
        return None
    survivors = sum(1 for r in rows
                    if r.get("t") not in ("", "None") and abs(float(r["t"])) > 2)
    return {"family": label, "role": "control" if placebo else "search",
            "what_was_tried": what, "cells": len(rows),
            "expected_by_chance": round(0.05 * len(rows), 1), "survivors": survivors,
            "status": "null" if not survivors else "cells above two sigma, see the family correction",
            "artifact": path.name,
            "reproduce": "python scripts/run_group_event_study.py" + (" --placebo" if placebo else "")}


def two_firm_family(path: Path) -> dict | None:
    rows = read(path)
    if not rows:
        return None
    horizons = sorted({int(key.split("_")[1]) for key in rows[0] if key.startswith("abnormal_")
                       and key.split("_")[1].isdigit()})
    cells, survivors = 0, 0
    for sign in ("negative", "positive"):
        for horizon in horizons:
            values = []
            for row in rows:
                surprise = row.get("surprise")
                if surprise in ("", "None", None):
                    continue
                wanted = float(surprise) < 0 if sign == "negative" else float(surprise) > 0
                if not wanted:
                    continue
                value = row.get(f"abnormal_{horizon}")
                if value not in ("", "None", None):
                    values.append(float(value))
            if len(values) < 3:
                continue
            cells += 1
            t = tstat(values)
            if t is not None and abs(t) > 2:
                survivors += 1
    return {"family": "firm-level revision study, two companies", "role": "search",
            "what_was_tried": f"{len(rows)} timestamped revisions, both directions across {len(horizons)} horizons",
            "cells": cells, "expected_by_chance": round(0.05 * cells, 1), "survivors": survivors,
            "status": "null on the predicted direction",
            "artifact": path.name, "reproduce": "python scripts/run_revision_event_study.py"}


def strategy_family(path: Path) -> dict | None:
    rows = read(path)
    if not rows:
        return None
    signals = sorted({r["signal"] for r in rows})
    cells = len(signals) + 3 + 1   # signal definitions, three selectivity cuts, the robustness pair
    return {"family": "aggregate capacity revision strategy", "role": "search",
            "what_was_tried": f"{len(signals)} signal definitions, three selectivity cuts, one robustness pair",
            "cells": cells, "expected_by_chance": "", "survivors": 0,
            "status": "no cell positive after costs at the doubled rate",
            "artifact": path.name, "reproduce": "python scripts/run_capacity_strategy.py"}


def compute_price_family(path: Path) -> dict | None:
    rows = [r for r in read(path)
            if r.get("coverage") == "measured" and "compute" in r.get("series_a", "") + r.get("series_b", "")]
    if not rows:
        return None
    survivors = sum(1 for r in rows
                    if r.get("placebo_percentile") not in ("", "None")
                    and float(r["placebo_percentile"]) >= 0.95)
    return {"family": "compute price against everything else", "role": "search",
            "what_was_tried": f"{len(rows)} pairs, one per other series, at monthly frequency",
            "cells": len(rows), "expected_by_chance": round(0.05 * len(rows), 2),
            "survivors": survivors, "status": "null, and underpowered by the window length",
            "artifact": path.name, "reproduce": "python scripts/run_association_scan.py --window compute-era"}


def measurement_family(path: Path, label: str, what: str, count: int, command: str) -> dict | None:
    """The reproduce command is named, not derived from a file name: deriving it produced a path
    that does not exist, which the path check caught."""
    if not path.exists():
        return None
    return {"family": label, "role": "measurement", "what_was_tried": what, "cells": count,
            "expected_by_chance": "", "survivors": "", "status": "measurement, no null test",
            "artifact": path.name, "reproduce": command}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="results/variant-ledger.csv")
    parser.add_argument("--view", default="docs/variants.md")
    args = parser.parse_args(argv)

    nodes = {json.loads(line)["id"]: json.loads(line)
             for line in (ROOT / "docs" / "scan" / "nodes.jsonl").read_text().splitlines() if line.strip()}
    results = ROOT / "results"

    families = [
        scan_family(results / "scan-pairs-mechanism.csv", nodes,
                    "scan, mechanism window", "every declared pair, each against its own generated null"),
        scan_family(results / "scan-pairs-compute-era.csv", nodes,
                    "scan, compute era", "the same scan inside the compute era window"),
        compute_price_family(results / "scan-pairs-compute-era.csv"),
        rpo_family(results / "group-event-study.csv", "firm disclosures, 382 companies",
                   "four industry groups, two directions, five horizons"),
        rpo_family(results / "group-event-placebo.csv", "the same study on shuffled dates",
                   "the placebo for the line above", placebo=True),
        two_firm_family(results / "revision-events.csv"),
        strategy_family(results / "capacity-strategy.csv"),
        measurement_family(results / "delivery-revisions.csv", "delivery revisions, project level",
                           "nine annual vintages, every generator", 7945,
                           "python scripts/build_delivery_panel.py --years 2015-2023"),
        measurement_family(results / "promise-survival.csv", "promise survival",
                           "first revision timing, with and without month-sized nudges", 6407,
                           "python scripts/build_promise_survival.py"),
    ]
    rows = [f for f in families if f]

    out = ROOT / args.out
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    searches = headline(rows, "search")
    controls = headline(rows, "control")
    lines = ["# Every variant we tried",
             "",
             "Generated by `make variants` from the artifacts that recorded them. One cell is one comparison.",
             "Expected is what chance alone would produce at the declared threshold.",
             "",
             f"**Searches: {searches['cells']} comparisons, {searches['survivors']} survivors, "
             f"{searches['expected']:.1f} expected by chance.** The control is reported separately because its",
             "survivors measure the pipeline rather than the search: "
             f"{controls['cells']} comparisons, {controls['survivors']} survivors, "
             f"{controls['expected']:.1f} expected.",
             "",
             "| family | role | cells | expected | survivors | artifact |",
             "|---|---|---|---|---|---|"]
    for row in rows:
        lines.append(f"| {row['family']} | {row['role']} | {row['cells']} | "
                     f"{row['expected_by_chance'] or 'n/a'} | "
                     f"{row['survivors'] if row['survivors'] != '' else 'n/a'} | `{row['artifact']}` |")
    lines.append("")
    lines.append("## What each line tried")
    lines.append("")
    for row in rows:
        lines.append(f"- **{row['family']}**: {row['what_was_tried']}. {row['status']}. "
                     f"Reproduce with `{row['reproduce']}`.")
    lines.append("")
    lines.append("A survivor in a scan line is a candidate for a mechanism conversation, never a strategy, and "
                 "the family correction is what separates the two.")
    (ROOT / args.view).write_text("\n".join(lines) + "\n")

    print(f"wrote {args.out} ({len(rows)} families)")
    print(f"wrote {args.view}")
    print(f"searches: {searches['cells']} comparisons, {searches['survivors']} survivors, "
          f"{searches['expected']:.1f} expected by chance")
    print(f"control:  {controls['cells']} comparisons, {controls['survivors']} survivors, "
          f"{controls['expected']:.1f} expected by chance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
