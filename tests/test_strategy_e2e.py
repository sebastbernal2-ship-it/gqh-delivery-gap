#!/usr/bin/env python3
"""Synthetic end-to-end gate test with valid and rejected paths."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from strategy.contracts import validate_trade  # noqa: E402
from strategy.gates import promotion_gate  # noqa: E402
from strategy.ledger import validate_exposure_record, validate_physical_record, validate_primary_event_record  # noqa: E402
from strategy.tradeability import no_trade_reasons  # noqa: E402

event = {"event_id": "e1", "source": "sec:1", "source_receipt": "sec:1", "entity_key": "issuer:PWR",
         "vintage": "2024Q1", "observed_at": "2024-01-05T15:00:00+00:00",
         "available_at": "2024-01-05T16:00:00+00:00", "usable_at": "2024-01-05T16:01:00+00:00",
         "unit": "USD", "evidence_status": "reviewed", "expectation_kind": "guidance",
         "expectation_status": "measured", "prior_value": "100", "current_value": "80",
         "missingness_reason": ""}
exposure = {"event_id": "e1", "issuer": "PWR", "security": "PWR", "segment": "corporate",
            "direction": "negative", "weight": "1", "status": "verified", "evidence": "sec:1",
            "source_receipt": "sec:1", "identity_vintage": "2024Q1"}
physical = {"observation_id": "o1", "project_key": "p1", "status": "operating",
            "observed_at": "2024-01-01T00:00:00+00:00", "available_at": "2024-01-02T00:00:00+00:00",
            "source": "eia:1", "evidence": "eia:1", "source_receipt": "eia:1", "capacity_mw": "10"}
trade = {"security": "PWR", "signal_at": "2024-01-05T16:01:00+00:00",
         "fill_at": "2024-01-08T14:30:00+00:00", "side": "sell", "quantity": "10", "price": "100",
         "cost_bps": "10", "borrow_bps": "4", "source_receipt": "market:1"}
assert validate_primary_event_record(event) == event
assert validate_exposure_record(exposure) == exposure
assert validate_physical_record(physical) == physical
assert validate_trade(trade) == trade
assert no_trade_reasons("sell", True, 10, 10, 5, 20) == []
assert promotion_gate(verified_exposures=1, measured_expectations=1, market_control_rows=1,
                      tradeability_rows=1, physical_rows=1)["status"] == "OPEN"
for bad in (
    {**event, "expectation_kind": "public_plan"},
    {**event, "label_at": "2024-01-05T16:00:00+00:00"},
):
    try:
        validate_primary_event_record(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid synthetic event was accepted")
try:
    validate_trade({**trade, "fill_at": trade["signal_at"]})
except ValueError:
    pass
else:
    raise AssertionError("same-bar synthetic trade was accepted")
print("strategy e2e: 8/8 passed")
