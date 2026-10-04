#!/usr/bin/env python3
"""Do compute rental prices lead queue withdrawals?

Protocol: docs/plan/compute-queue-study.md. Development only, both sealed windows spent. Writes
results/compute-queue-study.json.

    python3 scripts/build_compute_queue_study.py
"""
from __future__ import annotations

import collections
import csv
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "results" / "queue-panel.csv"
COMPUTE = ROOT / "results" / "compute-price-monthly.csv"
OUT = ROOT / "results" / "compute-queue-study.json"
START = "2022-05"
END = "2024-12"
LAGS = (1, 3, 6)
SPECULATIVE = {"Solar", "Solar+Battery", "Battery"}
FIRM = {"Gas", "Coal", "Nuclear"}
GROUPS = {"solar": {"Solar", "Solar+Battery"}, "wind": {"Wind", "Offshore Wind"},
          "battery": {"Battery"}, "gas": {"Gas"}, "other": {"Other", "Coal", "Nuclear", "Hydro", "Geothermal"}}


def month_index(month: str) -> int:
    return int(month[:4]) * 12 + int(month[5:7]) - 1


def month_label(index: int) -> str:
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def spearman(xs: list[float], ys: list[float]) -> float:
    def rank(values):
        order = sorted(range(len(values)), key=lambda i: values[i])
        ranks = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
                j += 1
            average = (i + j) / 2 + 1
            for k in range(i, j + 1):
                ranks[order[k]] = average
            i = j + 1
        return ranks
    if len(xs) < 4:
        return float("nan")
    rx, ry = rank(xs), rank(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    numerator = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    denominator = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return numerator / denominator if denominator else float("nan")


def main() -> int:
    rows = list(csv.DictReader(QUEUE.open()))
    families: dict[str, dict[int, float]] = collections.defaultdict(dict)
    for row in csv.DictReader(COMPUTE.open()):
        families[row["family"]][month_index(row["month"])] = float(row["median_usd_per_instance_hour"])
    months = sorted({month_index(row["month"]) for row in csv.DictReader(COMPUTE.open())})
    index = {}
    for month in months:
        values = [series[month] for series in families.values() if month in series]
        if len(values) >= 3:
            index[month] = statistics.median(values)
    index_months = sorted(index)
    window = [month for month in index_months if START <= month_label(month) <= END]
    change_3m = {month: math.log(index[month] / index[month - 3]) for month in window
                 if month - 3 in index and index[month - 3] > 0 and index[month] > 0}
    level_z = {}
    for month in window:
        history = [index[m] for m in range(month - 12, month + 1) if m in index]
        if len(history) >= 8:
            mean = statistics.mean(history)
            sd = statistics.pstdev(history)
            level_z[month] = (index[month] - mean) / sd if sd else 0.0
    print(f"rental index months {month_label(window[0])} to {month_label(window[-1])}, "
          f"{len(change_3m)} with a three month change, {len(level_z)} with a level reading")

    def alive_and_withdrawals() -> tuple[dict[int, int], dict[str, dict[int, int]]]:
        alive = collections.Counter()
        withdrawals = collections.defaultdict(collections.Counter)
        start, end = month_index(START), month_index(END)
        for row in rows:
            if not row["q_date"]:
                continue
            q = month_index(row["q_date"])
            if q > end:
                continue
            wd = month_index(row["wd_date"]) if row.get("wd_date") else None
            on = month_index(row["on_date"]) if row.get("on_date") else None
            end_alive = min([m for m in (wd, on, end + 1) if m is not None])
            for month in range(max(q, start), min(end_alive, end + 1)):
                alive[month] += 1
            if wd is not None and start <= wd <= end:
                technology = row.get("type_clean", "Other")
                for name, members in GROUPS.items():
                    if technology in members:
                        withdrawals[name][wd] += 1
                        break
        return alive, withdrawals

    alive, withdrawals = alive_and_withdrawals()
    hazards = {"all": {month: sum(counter[month] for counter in withdrawals.values()) / alive[month]
                       for month in range(month_index(START), month_index(END) + 1) if alive[month]}}
    for name in GROUPS:
        hazards[name] = {month: withdrawals[name][month] / alive[month]
                         for month in range(month_index(START), month_index(END) + 1) if alive[month]}

    def test(signal: dict[int, float], hazard: dict[int, float], lag: int) -> dict:
        pairs = [(signal[month - lag], hazard[month]) for month in hazard
                 if month - lag in signal]
        if len(pairs) < 8:
            return {"n": len(pairs), "status": "insufficient"}
        observed = spearman([a for a, _ in pairs], [b for _, b in pairs])
        shifts = []
        ordered = [signal[month - lag] for month in sorted(hazard) if month - lag in signal]
        hazard_values = [hazard[month] for month in sorted(hazard) if month - lag in signal]
        for shift in range(1, len(ordered)):
            shifted = ordered[shift:] + ordered[:shift]
            value = spearman(shifted, hazard_values)
            if value == value:
                shifts.append(value)
        share = sum(1 for value in shifts if value >= observed) / len(shifts) if shifts else None
        return {"n": len(pairs), "rho": round(observed, 3),
                "share_shifts_ge": round(share, 3) if share is not None else None,
                "shifts": len(shifts)}

    report = {"status": "development only; protocol docs/plan/compute-queue-study.md",
              "window": {"from": month_label(window[0]), "to": month_label(window[-1])},
              "months": len(window), "tests": {}}
    for label, signal in (("change_3m", change_3m), ("level_z", level_z)):
        report["tests"][label] = {}
        for lag in LAGS:
            report["tests"][label][f"lag{lag}"] = {
                name: test(signal, hazard, lag) for name, hazard in hazards.items()}
    speculative = [row for name, hazard in hazards.items() if name in ("solar", "battery")
                   for row in hazard.values()]
    firm = [row for name, hazard in hazards.items() if name in ("gas", "other") for row in hazard.values()]
    report["placebo"] = {"speculative_mean_hazard": round(statistics.mean(speculative), 5) if speculative else None,
                         "firm_mean_hazard": round(statistics.mean(firm), 5) if firm else None}
    OUT.write_text(json.dumps(report, indent=1) + "\n")
    for label in report["tests"]:
        for lag in report["tests"][label]:
            block = report["tests"][label][lag]
            print(f"{label} lag{lag}: " + ", ".join(
                f"{name} rho {value.get('rho')} (n {value.get('n')}, share {value.get('share_shifts_ge')})"
                for name, value in block.items()))
    print("placebo:", json.dumps(report["placebo"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
