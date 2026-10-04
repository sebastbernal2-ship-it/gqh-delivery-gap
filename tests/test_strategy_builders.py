#!/usr/bin/env python3
"""Offline checks for the event and physical ledger builders."""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_capacity_event_ledger import build_events  # noqa: E402
from build_physical_ledger import build_observations  # noqa: E402
from strategy.ledger import validate_rows  # noqa: E402

capacity = build_events([
    {"vintage": "2022-01", "available_from": "2022-01-31", "promised_year": "2023",
     "capacity_mw": "100", "source_receipt": "eia:2022-01"},
    {"vintage": "2023-01", "available_from": "2023-01-31", "promised_year": "2023",
     "capacity_mw": "80", "source_receipt": "eia:2023-01"},
], dt.date(2022, 1, 1), dt.date(2023, 12, 31))
assert len(capacity) == 1
assert capacity[0]["expectation_kind"] == "public_plan"
assert capacity[0]["expectation_status"] == "measured"
assert validate_rows(capacity, "events") == 1

physical = build_observations([{
    "plant_id": "1", "generator_id": "A", "entity_name": "Example", "capacity_mw": "100",
    "promise_vintage": "2022-01", "realized_vintage": "2023-01",
}])
assert [row["status"] for row in physical] == ["planned", "operating"]
assert validate_rows(physical, "physical") == 2
print("strategy builders: 2/2 passed")
