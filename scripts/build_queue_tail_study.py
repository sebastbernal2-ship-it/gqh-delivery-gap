#!/usr/bin/env python3
"""Run the declared queue tail study, exactly as docs/plan/queue-tail-study.md states it.

Development only. Both sealed windows are spent and are not touched. The protocol was committed
before this script ran; this file implements only what the protocol declares: the earliest queue
record per matched plant, the median split, two outcomes, and a state-conditioned permutation null.

Writes results/queue-tail-study.json.

    python3 scripts/build_queue_tail_study.py
"""
from __future__ import annotations

import collections
import csv
import json
import random
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "results" / "queue-panel.csv"
CROSSWALK = ROOT / "results" / "queue-crosswalk.csv"
SURVIVAL = ROOT / "results" / "promise-survival.csv"
REVISIONS = ROOT / "results" / "delivery-revisions.csv"
OUT = ROOT / "results" / "queue-tail-study.json"

DRAWS = 5000
SEED = 42
TAIL_MONTHS = 6


def main() -> int:
    panel = {row["q_id"]: row for row in csv.DictReader(QUEUE.open())}
    # One queue record per matched plant: the earliest request.
    earliest: dict[str, dict] = {}
    for row in csv.DictReader(CROSSWALK.open()):
        if row.get("match") != "yes":
            continue
        source = panel.get(row["q_id"])
        if not source:
            continue
        plant = row["eia_plant_id"]
        if plant not in earliest or (source.get("q_date") or "9999") < (earliest[plant].get("q_date") or "9999"):
            earliest[plant] = source
    # Outcomes per plant.
    slips: dict[str, list[float]] = collections.defaultdict(list)
    for row in csv.DictReader(SURVIVAL.open()):
        try:
            slips[row["plant_id"]].append(float(row.get("slip_months") or 0))
        except ValueError:
            slips[row["plant_id"]].append(0.0)
    exits = {row["plant_id"] for row in csv.DictReader(REVISIONS.open())
             if row.get("change") == "cancelled or postponed"}
    # Assemble the study rows.
    rows = []
    excluded = {"no_duration": 0, "no_survival": 0}
    for plant, source in earliest.items():
        try:
            days = float(source.get("days_ir_to_ia") or "")
        except ValueError:
            excluded["no_duration"] += 1
            continue
        if plant not in slips:
            excluded["no_survival"] += 1
            continue
        rows.append({"plant_id": plant, "state": source.get("state", ""), "days": days,
                     "tail": 1 if max(slips[plant]) >= TAIL_MONTHS else 0,
                     "exit": 1 if plant in exits else 0})
    if len(rows) < 20:
        raise SystemExit(f"only {len(rows)} usable rows; the declared study would be untestable")
    days = sorted(row["days"] for row in rows)
    median = days[len(days) // 2]
    slow = [row for row in rows if row["days"] >= median]
    fast = [row for row in rows if row["days"] < median]

    def shift(outcome: str) -> float:
        slow_share = sum(row[outcome] for row in slow) / len(slow)
        fast_share = sum(row[outcome] for row in fast) / len(fast)
        return slow_share - fast_share

    random.seed(SEED)
    by_state: dict[str, list[dict]] = collections.defaultdict(list)
    for row in rows:
        by_state[row["state"]].append(row)
    null: dict[str, list[float]] = {"tail": [], "exit": []}
    for _ in range(DRAWS):
        for group in by_state.values():
            values = [row["days"] for row in group]
            random.shuffle(values)
            for row, value in zip(group, values):
                row["_draw_days"] = value
        draw_slow = [row for row in rows if row["_draw_days"] >= median]
        draw_fast = [row for row in rows if row["_draw_days"] < median]
        for outcome in ("tail", "exit"):
            slow_share = sum(row[outcome] for row in draw_slow) / max(1, len(draw_slow))
            fast_share = sum(row[outcome] for row in draw_fast) / max(1, len(draw_fast))
            null[outcome].append(slow_share - fast_share)

    def p_value(outcome: str, observed: float) -> float:
        draws = null[outcome]
        return (1 + sum(1 for value in draws if value >= observed)) / (1 + len(draws))

    report = {
        "status": "development only; both sealed windows spent and untouched",
        "protocol": "docs/plan/queue-tail-study.md",
        "population": {"plants": len(rows), "excluded": excluded},
        "median_days_ir_to_ia": median,
        "tests": {},
    }
    for outcome in ("tail", "exit"):
        observed = shift(outcome)
        report["tests"][outcome] = {
            "slow_half": {"n": len(slow), "share": round(sum(row[outcome] for row in slow) / len(slow), 4)},
            "fast_half": {"n": len(fast), "share": round(sum(row[outcome] for row in fast) / len(fast), 4)},
            "observed_shift": round(observed, 4),
            "null_mean": round(statistics.mean(null[outcome]), 4),
            "null_p95": round(sorted(null[outcome])[int(0.95 * len(null[outcome]))], 4),
            "p_value": round(p_value(outcome, observed), 4),
        }
    OUT.write_text(json.dumps(report, indent=1) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"plants {len(rows)} (excluded {excluded}); median queue wait {median:.0f} days")
    for outcome in ("tail", "exit"):
        stats = report["tests"][outcome]
        print(f"{outcome:5s}: slow half {stats['slow_half']['share']:.1%} vs fast half "
              f"{stats['fast_half']['share']:.1%}; shift {stats['observed_shift']:+.3f} "
              f"(null p95 {stats['null_p95']:+.3f}); p={stats['p_value']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
