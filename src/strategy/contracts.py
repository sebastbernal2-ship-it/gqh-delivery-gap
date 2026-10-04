"""Small validation gates for the delivery-gap strategy inputs.

These contracts reject future information, unbounded attribution, and non-executable fills.
They validate rows only. They do not fetch data, infer identity, or promote a thesis.
"""
from __future__ import annotations

import datetime as dt
import math
from typing import Mapping


_ALLOWED_EVIDENCE = {"reviewed", "downloaded", "documented"}
_ALLOWED_EXPOSURE_STATUS = {"verified", "proposed", "ambiguous", "unmatched"}
_ALLOWED_DIRECTIONS = {"positive", "negative", "neutral"}
_ALLOWED_PHYSICAL_STATUS = {"planned", "permitted", "under_construction", "energized", "operating", "cancelled"}
_ALLOWED_EXPECTATIONS = {"guidance", "consensus", "market_implied", "public_plan"}
_PRIMARY_EXPECTATIONS = {"guidance", "consensus", "market_implied"}


def _timestamp(row: Mapping[str, object], name: str) -> dt.datetime:
    value = row.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty timestamp")
    text = value.strip()
    try:
        parsed = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} is not ISO-8601: {value}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{name} must include a timezone: {value}")
    return parsed.astimezone(dt.timezone.utc)


def _number(row: Mapping[str, object], name: str, *, nonnegative: bool = False) -> float:
    value = row.get(name)
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not math.isfinite(number) or (nonnegative and number < 0):
        raise ValueError(f"{name} has an invalid value: {value}")
    return number


def _required(row: Mapping[str, object], *names: str) -> None:
    missing = [name for name in names if row.get(name) in (None, "")]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")


def _ordered(row: Mapping[str, object], *names: str) -> None:
    stamps = [_timestamp(row, name) for name in names]
    if any(left > right for left, right in zip(stamps, stamps[1:])):
        raise ValueError(f"timestamps are not ordered: {', '.join(names)}")


def validate_revision(row: Mapping[str, object]) -> Mapping[str, object]:
    """Validate a point-in-time expectation revision."""
    _required(row, "source", "entity_key", "unit", "evidence_status", "expectation_kind")
    _ordered(row, "observed_at", "available_at", "usable_at")
    if row["evidence_status"] not in _ALLOWED_EVIDENCE:
        raise ValueError("revision evidence must be reviewed, downloaded, or documented")
    if row["expectation_kind"] not in _ALLOWED_EXPECTATIONS:
        raise ValueError(f"unknown expectation kind: {row['expectation_kind']}")
    _number(row, "prior_value")
    _number(row, "current_value")
    return row


def validate_exposure(row: Mapping[str, object]) -> Mapping[str, object]:
    """Validate a bounded issuer-to-event exposure mapping."""
    _required(row, "event_id", "issuer", "security", "segment", "direction", "status", "evidence")
    if row["direction"] not in _ALLOWED_DIRECTIONS:
        raise ValueError(f"unknown exposure direction: {row['direction']}")
    if row["status"] not in _ALLOWED_EXPOSURE_STATUS:
        raise ValueError(f"unknown exposure status: {row['status']}")
    weight = _number(row, "weight")
    if not 0 <= weight <= 1:
        raise ValueError("exposure weight must be between zero and one")
    return row


def validate_trade(row: Mapping[str, object]) -> Mapping[str, object]:
    """Validate an executable trade with a strictly lagged fill."""
    _required(row, "security", "side")
    signal = _timestamp(row, "signal_at")
    fill = _timestamp(row, "fill_at")
    if fill <= signal:
        raise ValueError("fill must occur strictly after the signal")
    if row["side"] not in {"buy", "sell"}:
        raise ValueError(f"unknown trade side: {row['side']}")
    _number(row, "quantity", nonnegative=True)
    if float(row["quantity"]) == 0:
        raise ValueError("quantity must be positive")
    _number(row, "price", nonnegative=True)
    if float(row["price"]) == 0:
        raise ValueError("price must be positive")
    _number(row, "cost_bps", nonnegative=True)
    _number(row, "borrow_bps", nonnegative=True)
    return row


def validate_physical(row: Mapping[str, object]) -> Mapping[str, object]:
    """Validate a dated physical observation without treating it as a financial label."""
    _required(row, "observation_id", "project_key", "status", "source", "evidence")
    observed = _timestamp(row, "observed_at")
    available = _timestamp(row, "available_at")
    if available < observed:
        raise ValueError("physical evidence cannot be available before observation")
    if row["status"] not in _ALLOWED_PHYSICAL_STATUS:
        raise ValueError(f"unknown physical status: {row['status']}")
    _number(row, "capacity_mw", nonnegative=True)
    return row


def validate_primary_expectation(row: Mapping[str, object]) -> Mapping[str, object]:
    """Require an issuer-linked expectation for the financial pilot."""
    validate_revision(row)
    if row["expectation_kind"] not in _PRIMARY_EXPECTATIONS:
        raise ValueError("public-plan and other proxy evidence cannot drive the primary strategy")
    if not str(row["entity_key"]).startswith("issuer:"):
        raise ValueError("primary expectation must be issuer-linked")
    if row.get("expectation_status") != "measured":
        raise ValueError("primary expectation is not measured")
    return row
