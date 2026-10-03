"""Point-in-time leakage gates for event packages."""
from __future__ import annotations

from typing import Mapping

from strategy.contracts import _timestamp


def validate_no_leakage(row: Mapping[str, object], *, allow_sealed: bool = False) -> Mapping[str, object]:
    """Reject labels or controls that were unavailable when a signal became usable."""
    usable = _timestamp(row, "usable_at")
    prior_available = row.get("prior_available_at")
    if prior_available:
        prior = _timestamp(row, "prior_available_at")
        observed = _timestamp(row, "observed_at")
        if prior > observed:
            raise ValueError("prior expectation became available after the observation")
    for name in ("label_at", "outcome_at"):
        if row.get(name):
            if _timestamp(row, name) <= usable:
                raise ValueError(f"{name} is available before or at the usable signal")
    for name in ("market_available_at", "sector_available_at", "control_available_at"):
        if row.get(name) and _timestamp(row, name) > usable:
            raise ValueError(f"{name} is available after the usable signal")
    sealed = str(row.get("in_sealed_window", "")).lower() in {"true", "1", "yes"}
    if sealed and not allow_sealed:
        raise ValueError("sealed-window row is closed")
    return row
