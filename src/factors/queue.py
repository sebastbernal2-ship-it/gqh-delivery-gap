"""Congestion, measured from the inventory itself.

The real queue data is not reachable from this host: the national queue dataset refused and the system
operators did not answer. So congestion is measured from what we already hold, and the proxy is declared:

- **pipeline momentum**: the change in planned capacity in a state over the previous twelve months. A state
  whose pipeline is growing faster than it can be built is more congested.
- **promise horizon**: the median months between a vintage and the dates it promises, within a state. A
  congested state promises further out.

Both are point in time: each is computed from one monthly vintage and is knowable at that vintage's month end.
This is a proxy, not a filing, and the report says so wherever it is used.
"""
from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "promise-series"


def month_index(stamp: str) -> int:
    return int(stamp[:4]) * 12 + int(stamp[5:7])


def operating_by_state(vintage: dict[str, list]) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for generator in vintage.get("Operating", []):
        try:
            totals[generator.state] += float(generator.capacity_mw)
        except (TypeError, ValueError):
            continue
    return dict(totals)


def vintage_readings(rows: list[dict], stamp: str, operating: dict[str, float] | None = None) -> dict[str, dict[str, float]]:
    """Per state: planned MW, its ratio to operating MW, and the median promise horizon in months."""
    planned: dict[str, float] = defaultdict(float)
    horizons: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        state = row.get("state") or "?"
        try:
            planned[state] += float(row.get("capacity_mw") or 0)
        except (TypeError, ValueError):
            pass
        statement = row.get("statement") or ""
        if len(statement) == 7:
            horizons[state].append(month_index(statement) - month_index(stamp))
    out: dict[str, dict[str, float]] = {}
    for state, megawatts in planned.items():
        out[state] = {
            "planned_mw": megawatts,
            "promise_horizon_months": statistics.median(horizons[state]) if horizons.get(state) else None,
        }
    return out


def readings(start: str = "2015-07", end: str = "2022-09") -> dict[str, dict[str, dict[str, float]]]:
    """Every cached vintage reduced to per state readings, with twelve month pipeline momentum added."""
    out: dict[str, dict[str, dict[str, float]]] = {}
    for path in sorted(CACHE.glob("*.jsonl")):
        stamp = path.stem
        if stamp < start or stamp > end:
            continue
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        out[stamp] = vintage_readings(rows, stamp)
    # Momentum needs the vintage twelve months earlier, in the same state.
    for stamp, states in list(out.items()):
        prior = f"{int(stamp[:4]) - 1}-{stamp[5:]}"
        if prior not in out:
            continue
        for state, values in states.items():
            was = out[prior].get(state, {}).get("planned_mw")
            now = values.get("planned_mw")
            values["pipeline_momentum"] = ((now - was) / was) if was else None
    return out


def state_panel(start: str = "2015-07", end: str = "2022-09") -> dict[tuple[str, str], dict[str, float]]:
    """The readings flattened to (state, month) for joining into the delivery panel."""
    out: dict[tuple[str, str], dict[str, float]] = {}
    for stamp, states in readings(start, end).items():
        for state, values in states.items():
            out[(state, stamp)] = values
    return out
