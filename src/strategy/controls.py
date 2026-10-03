"""Deterministic placebo and negative-control helpers."""
from __future__ import annotations

import copy
import random
from collections import defaultdict
from typing import Mapping


def calendar_placebo(rows: list[Mapping[str, object]], group_key: str = "entity_key", seed: int = 20261003) -> list[dict]:
    """Rotate usable timestamps within each entity while preserving event identities."""
    groups: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(group_key, ""))].append(row)
    rng = random.Random(seed)
    output = []
    for group in groups.values():
        dates = [row.get("available_at") for row in group]
        shuffled = list(dates)
        rng.shuffle(shuffled)
        for row, available in zip(group, shuffled):
            placebo = copy.deepcopy(dict(row))
            placebo["available_at"] = available
            placebo["usable_at"] = available
            placebo["control_kind"] = "calendar_placebo"
            output.append(placebo)
    return output


def negative_control(row: Mapping[str, object], *, unrelated: bool) -> dict:
    """Mark a control event and refuse to call it issuer exposure when unrelated."""
    output = dict(row)
    output["control_kind"] = "negative_control"
    output["exposure_allowed"] = bool(not unrelated)
    return output
