"""Promotion gate state. A missing evidence package keeps the thesis closed."""
from __future__ import annotations


def promotion_gate(*, verified_exposures: int, measured_expectations: int,
                   market_control_rows: int, tradeability_rows: int, physical_rows: int,
                   sealed_open: bool = False) -> dict:
    reasons = []
    if verified_exposures <= 0:
        reasons.append("no verified issuer exposure")
    if measured_expectations <= 0:
        reasons.append("no measured expectation vintages")
    if market_control_rows <= 0:
        reasons.append("no market-control panel")
    if tradeability_rows <= 0:
        reasons.append("no tradeable execution rows")
    if physical_rows <= 0:
        reasons.append("no physical observations")
    if sealed_open:
        reasons.append("sealed window is already open")
    return {"status": "OPEN" if not reasons else "CLOSED", "reasons": reasons}
