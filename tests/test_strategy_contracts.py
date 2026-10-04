#!/usr/bin/env python3
"""Offline checks for the strategy input contracts."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from event.study import revision_surprise  # noqa: E402
from strategy.contracts import validate_exposure, validate_physical, validate_revision, validate_trade  # noqa: E402
from strategy.gates import promotion_gate  # noqa: E402
from strategy.contracts import validate_primary_expectation  # noqa: E402
from strategy.ledger import validate_event_record, validate_exposure_record, validate_physical_record, validate_trade_record  # noqa: E402
from strategy.physical import classify_confirmation  # noqa: E402
from strategy.tradeability import capacity_shares, cost_scenarios, net_return, no_trade_reasons  # noqa: E402


BASE = {
    "source": "sec:example",
    "entity_key": "issuer:PWR",
    "observed_at": "2024-01-05T15:00:00+00:00",
    "available_at": "2024-01-05T16:00:00+00:00",
    "usable_at": "2024-01-05T16:15:00+00:00",
    "unit": "USD",
    "evidence_status": "reviewed",
}


def fails(fn, row):
    try:
        fn(row)
    except ValueError:
        return True
    return False


revision = {**BASE, "prior_value": 100.0, "current_value": 80.0, "expectation_kind": "guidance"}
assert validate_revision(revision) == revision
event = {**revision, "event_id": "event-1", "source_receipt": "sec:file:1", "vintage": "2024Q1", "missingness_reason": ""}
assert validate_event_record(event) == event
assert fails(validate_event_record, {**event, "source_receipt": ""})
assert fails(validate_event_record, {**event, "label_at": "2024-01-05T16:00:00+00:00"})
assert fails(validate_event_record, {**event, "in_sealed_window": "true"})
assert promotion_gate(verified_exposures=0, measured_expectations=0, market_control_rows=0, tradeability_rows=0, physical_rows=0)["status"] == "CLOSED"
primary = {**event, "expectation_kind": "guidance", "expectation_status": "measured", "entity_key": "issuer:PWR"}
assert validate_primary_expectation(primary) == primary
assert fails(validate_primary_expectation, event)
assert fails(validate_revision, {**revision, "usable_at": "2024-01-05T15:30:00+00:00"})
assert fails(validate_revision, {**revision, "prior_value": None})
assert revision_surprise(80.0, 100.0) == -20.0
assert revision_surprise(None, 100.0) is None

exposure = {
    "event_id": "event-1", "issuer": "PWR", "security": "PWR", "segment": "power",
    "direction": "negative", "weight": 0.6, "status": "verified", "evidence": "sec:example",
}
assert validate_exposure(exposure) == exposure
assert validate_exposure_record({**exposure, "source_receipt": "sec:file:1", "identity_vintage": "2024Q1"})["event_id"] == "event-1"
assert fails(validate_exposure, {**exposure, "weight": 1.2})
assert fails(validate_exposure, {**exposure, "status": "proposed", "evidence": ""})

trade = {
    "security": "PWR", "signal_at": "2024-01-05T16:00:00+00:00",
    "fill_at": "2024-01-08T14:30:00+00:00", "side": "sell", "quantity": 10,
    "price": 80.0, "cost_bps": 12.0, "borrow_bps": 4.0,
}
assert validate_trade(trade) == trade
assert validate_trade_record({**trade, "source_receipt": "market:file:1"})["security"] == "PWR"
assert fails(validate_trade, {**trade, "fill_at": "2024-01-05T15:59:00+00:00"})
assert fails(validate_trade, {**trade, "cost_bps": -1})
assert round(net_return(0.05, 10.0, 10.0, 4.0, 5), 6) == 0.046
assert capacity_shares(100.0, 1_000_000.0, 0.1) == 1000
assert no_trade_reasons("sell", False, 1000, 1001, 25.0, 20.0) == ["borrow unavailable", "quantity exceeds capacity", "spread exceeds limit"]
assert round(cost_scenarios(0.05, 10.0, 10.0, 4.0, 5)["double"], 6) == 0.042

physical = {
    "observation_id": "obs-1", "project_key": "project:1", "status": "energized",
    "observed_at": "2024-01-01T00:00:00+00:00", "available_at": "2024-01-10T00:00:00+00:00",
    "source": "eia:860m", "evidence": "eia:file:1", "capacity_mw": 100.0,
}
assert validate_physical(physical) == physical
assert validate_physical_record({**physical, "source_receipt": "eia:file:1"})["project_key"] == "project:1"
assert fails(validate_physical, {**physical, "available_at": "2023-12-01T00:00:00+00:00"})
assert fails(validate_physical, {**physical, "capacity_mw": -1})
assert classify_confirmation("2024-01-12T00:00:00+00:00", [physical])["status"] == "confirmed"
assert classify_confirmation("2024-01-05T00:00:00+00:00", [physical])["status"] == "unconfirmed"

print("strategy contracts: 31/31 passed")
