"""Point-in-time classification for physical confirmation evidence."""
from __future__ import annotations

from typing import Iterable

from strategy.contracts import _timestamp, validate_physical


def classify_confirmation(event_available_at: str, observations: Iterable[dict]) -> dict:
    """Classify only physical evidence available by the event time.

    Later observations are returned as excluded evidence and never change the classification.
    """
    event_time = _timestamp({"event": event_available_at}, "event")
    eligible = []
    excluded = []
    for row in observations:
        validate_physical(row)
        target = eligible if _timestamp(row, "available_at") <= event_time else excluded
        target.append(row)
    statuses = {row["status"] for row in eligible}
    if "operating" in statuses or "energized" in statuses:
        status = "confirmed"
    elif "cancelled" in statuses:
        status = "contradicted"
    elif "permitted" in statuses or "under_construction" in statuses:
        status = "partial"
    else:
        status = "unconfirmed"
    return {"status": status, "eligible": eligible, "excluded_future": excluded}
