#!/usr/bin/env python3
"""Build the regime state machine: one dated row per month with the phase and the gate readings.

Protocol: docs/plan/regime-state-machine.md. Development only, both sealed windows spent. Writes
results/regime-state-daily.csv and results/regime-state-summary.json.

    python3 scripts/build_regime_state.py
"""
from __future__ import annotations

import collections
import csv
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOTTLENECK = ROOT / "results" / "bottleneck-factors.csv"
QUEUE = ROOT / "results" / "queue-panel.csv"
COMPUTE = ROOT / "results" / "compute-price-monthly.csv"
OUT = ROOT / "results" / "regime-state-daily.csv"
SUMMARY = ROOT / "results" / "regime-state-summary.json"
START = "2014-01"
END = "2024-12"
PHASES = ("shortage", "buildout", "overbuild", "shakeout", "second_wave")


def month_index(month: str) -> int:
    return int(month[:4]) * 12 + int(month[5:7]) - 1


def month_label(index: int) -> str:
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def main() -> int:
    bottleneck = {}
    for row in csv.DictReader(BOTTLENECK.open()):
        try:
            bottleneck[row["month"]] = {
                "dc_spend": float(row["dc_construction_musd"]),
                "power_spend": float(row["power_construction_musd"]),
                "equipment_spend": float(row["equipment_construction_musd"]),
                "gscpi": float(row["gscpi"]) if row["gscpi"] else None,
                "delivery_times": float(row["delivery_times"]) if row["delivery_times"] else None,
                "ten_year": float(row["ten_year"]) if row["ten_year"] else None,
            }
        except (ValueError, KeyError):
            continue
    spend_months = sorted(bottleneck)

    families: dict[str, dict[int, float]] = collections.defaultdict(dict)
    for row in csv.DictReader(COMPUTE.open()):
        families[row["family"]][month_index(row["month"])] = float(row["median_usd_per_instance_hour"])
    rental_index = {}
    for month in sorted({month_index(row["month"]) for row in csv.DictReader(COMPUTE.open())}):
        values = [series[month] for series in families.values() if month in series]
        if len(values) >= 3:
            rental_index[month] = statistics.median(values)

    rows = list(csv.DictReader(QUEUE.open()))
    start, end = month_index(START), month_index(END)
    alive = collections.Counter()
    withdrawals = collections.Counter()
    age_sum = collections.Counter()
    for row in rows:
        if not row["q_date"]:
            continue
        q = month_index(row["q_date"])
        wd = month_index(row["wd_date"]) if row.get("wd_date") else None
        on = month_index(row["on_date"]) if row.get("on_date") else None
        end_alive = min([m for m in (wd, on, end + 1) if m is not None])
        for month in range(max(q, start), min(end_alive, end + 1)):
            alive[month] += 1
            age_sum[month] += month - q
        if wd is not None and start <= wd <= end:
            withdrawals[wd] += 1

    def median_of(values: list[float]) -> float | None:
        return statistics.median(values) if values else None

    records = []
    for month in range(start, end + 1):
        label = month_label(month)
        readings: dict[str, float | None] = {}
        spend = bottleneck.get(label)
        if spend and month - 12 >= start:
            past = bottleneck.get(month_label(month - 12))
            if past:
                for key, field in (("dc_growth", "dc_spend"), ("power_growth", "power_spend"),
                                   ("equipment_growth", "equipment_spend")):
                    if past[field] > 0:
                        readings[key] = math.log(spend[field] / past[field])
        readings["gscpi"] = spend["gscpi"] if spend else None
        readings["delivery_times"] = spend["delivery_times"] if spend else None
        readings["ten_year"] = spend["ten_year"] if spend else None
        # queue readings
        if alive[month]:
            hazard = sum(withdrawals[m] for m in range(month - 2, month + 1)) / (3 * alive[month])
            readings["hazard_3m"] = hazard
            readings["queue_age_months"] = age_sum[month] / alive[month]
        # rental level reading
        if month in rental_index:
            history = [rental_index[m] for m in range(month - 12, month + 1) if m in rental_index]
            if len(history) >= 8:
                mean = statistics.mean(history)
                sd = statistics.pstdev(history)
                readings["rental_level_z"] = (rental_index[month] - mean) / sd if sd else 0.0
        records.append({"month": label, **readings})

    def series(key: str) -> list[float]:
        return [row[key] for row in records if row.get(key) is not None]

    hazard_median = median_of(series("hazard_3m"))
    hazard_upper = sorted(series("hazard_3m"))[int(0.75 * len(series("hazard_3m")))] if series("hazard_3m") else None
    gscpi_median = median_of(series("gscpi"))
    delivery_median = median_of(series("delivery_times"))
    # Phase from two sensors: demand economics (rental level, or spend growth before 2022) and supply
    # stress (withdrawal hazard). The grid is declared in the protocol, and the markers stay visible.
    hazard_terciles = sorted(series("hazard_3m"))
    def tercile(values: list[float], value: float) -> str:
        if not values:
            return "mid"
        low = values[int(0.33 * (len(values) - 1))]
        high = values[int(0.66 * (len(values) - 1))]
        return "low" if value <= low else ("high" if value >= high else "mid")
    rental_terciles = sorted(series("rental_level_z"))

    def rental_band(value: float) -> str:
        return "low" if value < -0.5 else ("high" if value > 0.5 else "mid")

    previous_phase = None
    pending_phase, pending_count = None, 0
    for index, row in enumerate(records):
        hazard = row.get("hazard_3m")
        rental = row.get("rental_level_z")
        growths = [row.get(key) for key in ("dc_growth", "power_growth", "equipment_growth")
                   if row.get(key) is not None]
        positive_growth = sum(1 for value in growths if value > 0)
        demand_level = "no_sensor" if rental is None else rental_band(rental)
        stress_level = "no_sensor" if hazard is None else tercile(hazard_terciles, hazard)
        if demand_level == "no_sensor":
            phase = "buildout" if positive_growth >= 2 else ("shakeout" if stress_level == "high" else "overbuild")
            marker = f"pre rental sensor: spend growth {positive_growth} of {len(growths)}, stress {stress_level}"
        else:
            grid = {("high", "low"): "shortage", ("high", "mid"): "buildout", ("high", "high"): "buildout",
                    ("mid", "low"): "buildout", ("mid", "mid"): "buildout", ("mid", "high"): "shakeout",
                    ("low", "low"): "overbuild", ("low", "mid"): "overbuild", ("low", "high"): "shakeout"}
            phase = grid[(demand_level, stress_level)]
            marker = f"demand {demand_level} (rental {round(rental, 2)}), stress {stress_level} (hazard {round(hazard, 5)})"
            if phase == "shakeout" and hazard is not None and index > 0:
                previous = records[index - 1].get("hazard_3m")
                if previous is not None and hazard < previous:
                    phase = "second_wave"
                    marker += ", hazard falling"
        row["markers"] = marker
        row["phase_agreement"] = 1.0
        if previous_phase is None:
            previous_phase = phase
            row["phase"] = phase
            continue
        if phase != previous_phase:
            if pending_phase == phase:
                pending_count += 1
            else:
                pending_phase, pending_count = phase, 1
            if pending_count >= 2:
                previous_phase = phase
                pending_phase, pending_count = None, 0
            row["phase"] = previous_phase
        else:
            row["phase"] = phase
            pending_phase, pending_count = None, 0
    with OUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["month", "phase", "phase_agreement", "markers",
                                                    "rental_level_z", "hazard_3m", "queue_age_months",
                                                    "dc_growth", "power_growth", "equipment_growth", "gscpi",
                                                    "delivery_times", "ten_year"])
        writer.writeheader()
        writer.writerows(records)
    transitions = []
    for previous, current in zip(records, records[1:]):
        if previous["phase"] != current["phase"]:
            transitions.append({"from": previous["month"], "to": current["month"],
                                "from_phase": previous["phase"], "to_phase": current["phase"]})
    summary = {
        "months": len(records),
        "phase_counts": dict(collections.Counter(row["phase"] for row in records).most_common()),
        "transitions": transitions[-12:],
        "latest": records[-1],
        "hazard_median": round(hazard_median, 6) if hazard_median else None,
        "gscpi_median": round(gscpi_median, 3) if gscpi_median else None,
        "delivery_median": round(delivery_median, 2) if delivery_median else None,
    }
    SUMMARY.write_text(json.dumps(summary, indent=1) + "\n")
    print(f"regime rows {len(records)} from {records[0]['month']} to {records[-1]['month']}")
    print("phase counts:", json.dumps(summary["phase_counts"]))
    print("last 8 months:")
    for row in records[-8:]:
        print(f"  {row['month']}: {row['phase']} ({row['phase_agreement']}) rental {row.get('rental_level_z')} "
              f"hazard {row.get('hazard_3m'):.5f}" if row.get("hazard_3m") else f"  {row['month']}: {row['phase']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
