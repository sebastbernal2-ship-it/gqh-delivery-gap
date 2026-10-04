"""Provenance wrappers for strategy rows before analysis or promotion."""
from __future__ import annotations

from typing import Mapping

from strategy.leakage import validate_no_leakage
from strategy.contracts import (
    _required, validate_exposure, validate_physical, validate_primary_expectation,
    validate_revision, validate_trade,
)


def _receipt(row: Mapping[str, object]) -> None:
    _required(row, "source_receipt")


def validate_event_record(row: Mapping[str, object]) -> Mapping[str, object]:
    _required(row, "event_id", "vintage")
    if "missingness_reason" not in row:
        raise ValueError("missing required fields: missingness_reason")
    _receipt(row)
    validate_revision(row)
    return validate_no_leakage(row)


def validate_primary_event_record(row: Mapping[str, object]) -> Mapping[str, object]:
    _required(row, "event_id", "vintage")
    if "missingness_reason" not in row:
        raise ValueError("missing required fields: missingness_reason")
    _receipt(row)
    validate_primary_expectation(row)
    return validate_no_leakage(row)


def validate_exposure_record(row: Mapping[str, object]) -> Mapping[str, object]:
    _required(row, "source_receipt", "identity_vintage")
    return validate_exposure(row)


def validate_physical_record(row: Mapping[str, object]) -> Mapping[str, object]:
    _receipt(row)
    return validate_physical(row)


def validate_trade_record(row: Mapping[str, object]) -> Mapping[str, object]:
    _receipt(row)
    return validate_trade(row)


_VALIDATORS = {
    "events": validate_event_record,
    "primary_events": validate_primary_event_record,
    "exposures": validate_exposure_record,
    "physical": validate_physical_record,
    "trades": validate_trade_record,
}


def validate_rows(rows: list[Mapping[str, object]], kind: str) -> int:
    """Validate a typed CSV batch and return its row count."""
    try:
        validator = _VALIDATORS[kind]
    except KeyError as exc:
        raise ValueError(f"unknown ledger kind: {kind}") from exc
    seen: set[str] = set()
    for number, row in enumerate(rows, start=2):
        try:
            validator(row)
        except ValueError as exc:
            raise ValueError(f"{kind} row {number}: {exc}") from exc
        if kind == "events":
            event_id = str(row["event_id"])
            if event_id in seen:
                raise ValueError(f"events row {number}: duplicate event_id {event_id}")
            seen.add(event_id)
    return len(rows)
