#!/usr/bin/env python3
"""First probe: does queue duration line up with delivery slip?

Joins the queue crosswalk to the EIA revision panel by EIA plant id and measures whether the time
a project spent from interconnection request to agreement co-moves with the size of its later
delivery revisions. This is an exploratory development probe, not a declared test: both sealed
windows are spent, the matched subset is small and selected toward larger plants, and no
instrument is tested. It is recorded because a measured link between two previously separate
datasets is evidence about the mechanism even when it is weak.

Writes results/queue-slip-probe.json.

    python3 scripts/probe_queue_slip.py
"""
from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "results" / "queue-panel.csv"
CROSSWALK = ROOT / "results" / "queue-crosswalk.csv"
REVISIONS = ROOT / "results" / "delivery-revisions.csv"
OUT = ROOT / "results" / "queue-slip-probe.json"

CAVEATS = [
    "development only: both sealed windows are spent and were not touched",
    "the matched subset is selected toward larger and older plants, not a random sample",
    "no instrument and no cost model are tested; this is an association, not an edge",
    "exploratory: the split at 1000 days was chosen after seeing the pairs",
]


def rank(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(order):
        end = index
        while end + 1 < len(order) and values[order[end + 1]] == values[order[index]]:
            end += 1
        average = (index + end) / 2 + 1
        for position in range(index, end + 1):
            ranks[order[position]] = average
        index = end + 1
    return ranks


def spearman(xs: list[float], ys: list[float]) -> float:
    rx, ry = rank(xs), rank(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    numerator = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    denominator = ((sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5)
    return numerator / denominator if denominator else 0.0


def main() -> int:
    duration = {}
    for row in csv.DictReader(QUEUE.open()):
        try:
            duration[row["q_id"]] = float(row["days_ir_to_ia"]) if row.get("days_ir_to_ia") else None
        except ValueError:
            duration[row["q_id"]] = None
    slips: dict[str, list[float]] = {}
    for row in csv.DictReader(REVISIONS.open()):
        try:
            months = float(row.get("revision_months") or "")
        except ValueError:
            continue
        if months > 0:
            slips.setdefault(row["plant_id"], []).append(months)
    pairs = []
    for row in csv.DictReader(CROSSWALK.open()):
        if row.get("match") != "yes":
            continue
        days = duration.get(row["q_id"])
        plant_slips = slips.get(row["eia_plant_id"])
        if days and plant_slips:
            pairs.append({"q_id": row["q_id"], "plant_id": row["eia_plant_id"],
                          "days_ir_to_ia": days, "mean_slip_months": statistics.mean(plant_slips),
                          "max_slip_months": max(plant_slips), "revisions": len(plant_slips)})
    report = {
        "status": "exploratory development only",
        "matched_queue_rows": sum(1 for row in csv.DictReader(CROSSWALK.open()) if row.get("match") == "yes"),
        "plants_with_slips": len(slips),
        "joined_pairs": len(pairs),
        "caveats": CAVEATS,
    }
    if len(pairs) >= 12:
        xs = [pair["days_ir_to_ia"] for pair in pairs]
        ys = [pair["mean_slip_months"] for pair in pairs]
        slow = [pair for pair in pairs if pair["days_ir_to_ia"] >= 1000]
        fast = [pair for pair in pairs if pair["days_ir_to_ia"] < 1000]
        report.update({
            "spearman_rho": round(spearman(xs, ys), 4),
            "slow_queue": {"threshold_days": 1000, "n": len(slow),
                           "mean_slip_months": round(statistics.mean(p["mean_slip_months"] for p in slow), 2)
                           if slow else None},
            "fast_queue": {"threshold_days": 1000, "n": len(fast),
                           "mean_slip_months": round(statistics.mean(p["mean_slip_months"] for p in fast), 2)
                           if fast else None},
        })
    OUT.write_text(json.dumps(report, indent=1) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"joined pairs {report['joined_pairs']}; rho {report.get('spearman_rho')}")
    if report.get("slow_queue"):
        print(f"slow queue: n={report['slow_queue']['n']} mean slip {report['slow_queue']['mean_slip_months']} months")
        print(f"fast queue: n={report['fast_queue']['n']} mean slip {report['fast_queue']['mean_slip_months']} months")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
