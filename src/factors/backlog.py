"""Supplier and contractor backlogs, as lead time.

The firms that build and equip the chain disclose what they have contracted but not delivered. A rising
backlog across those firms is the closest thing we have to a measured lead time, and it comes from the same
obligation facts the firm level work already uses.

Two readings per group per month: the **share of firms whose obligation fell**, which is a direction, and the
**median growth over the trailing year**, which is a level. A value becomes usable in the month it became
public.
"""
from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVENTS = ROOT / "results" / "rpo-events.csv"
GROUPS = ("contractor", "equipment", "utility", "datacenter")


def _rows(path: Path = EVENTS) -> list[dict]:
    if not path.exists():
        return []
    with path.open() as handle:
        return list(csv.DictReader(handle))


def monthly_group_readings(path: Path = EVENTS) -> dict[str, dict[str, dict[str, float]]]:
    """Per group per month: share of negative revisions, and median relative change."""
    out: dict[str, dict[str, dict[str, float]]] = {group: {} for group in GROUPS}
    by_group_month: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in _rows(path):
        group = row.get("group")
        if group not in GROUPS:
            continue
        if str(row.get("in_sealed_window", "")).lower() in ("true", "1"):
            continue
        if not row.get("earliest_availability_utc") or not row.get("change"):
            continue
        try:
            change = float(row["change"])
            value = float(row["value"])
        except (TypeError, ValueError):
            continue
        if value == 0:
            continue
        by_group_month[(group, row["earliest_availability_utc"][:7])].append(change / abs(value))
    for (group, month), values in by_group_month.items():
        if not values:
            continue
        out[group][month] = {
            "share_negative": sum(1 for v in values if v < 0) / len(values),
            "median_relative_change": statistics.median(values),
            "reports": float(len(values)),
        }
    return out


def trailing_growth(series: dict[str, dict[str, float]], months: int = 12) -> dict[str, float]:
    """Median relative change over the trailing window, which is the lead time reading."""
    out: dict[str, float] = {}
    ordered = sorted(series)
    for index, month in enumerate(ordered):
        window = ordered[max(0, index - months + 1): index + 1]
        values = [series[m]["median_relative_change"] for m in window]
        if len(values) >= 3:
            out[month] = statistics.median(values)
    return out
