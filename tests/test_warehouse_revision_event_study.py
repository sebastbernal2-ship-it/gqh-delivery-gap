#!/usr/bin/env python3
"""Offline checks for the Snowflake-backed event-study transformations."""
from datetime import datetime, timezone
from decimal import Decimal
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_warehouse_revision_event_study import close_return, event_rows, median  # noqa: E402


bars = {
    datetime(2024, 1, 2, tzinfo=timezone.utc): Decimal("100"),
    datetime(2024, 1, 3, tzinfo=timezone.utc): Decimal("110"),
    datetime(2024, 1, 4, tzinfo=timezone.utc): Decimal("121"),
    datetime(2024, 1, 5, tzinfo=timezone.utc): Decimal("110"),
}

# A daily bar timestamp is the session marker. If the filing arrives after that marker,
# the current session is excluded and the first later session is the return start.
assert close_return(bars, "2024-01-02T22:00:00Z", 1) == Decimal("0.1")
assert close_return(bars, "2024-01-04T22:00:00Z", 1) is None
assert median([Decimal("1"), Decimal("3")]) == Decimal("2")

base = {
    "ticker": "PWR", "cik": "1050915", "accession": "a1", "concept": "rpo",
    "period_end": "2024-03-31", "filed": "2024-05-01", "earliest_availability_utc": "2024-05-01T20:00:00Z",
    "change": "100.00", "previous_value": "900.00", "in_sealed_window": "False",
}
rows = event_rows([
    base,
    {**base, "accession": "a2", "earliest_availability_utc": "", "period_end": "2024-06-30"},
    {**base, "accession": "a3", "in_sealed_window": "True", "period_end": "2024-09-30"},
])
assert len(rows) == 1 and rows[0]["accession"] == "a1"

duplicate_rejected = False
try:
    event_rows([base, base])
except ValueError:
    duplicate_rejected = True
assert duplicate_rejected
print("warehouse revision event study tests: 6/6 passed")
