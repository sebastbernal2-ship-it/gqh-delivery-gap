"""Contracts for a point-in-time index reconstitution study.

An index change is not a forced-flow observation until the announcement,
quantity inputs, and availability clocks are all known before the effective
close. Missing inputs remain exclusions instead of becoming guessed values.
"""
from __future__ import annotations

import datetime as dt
import math
from typing import Mapping
from urllib.parse import urlparse


DIRECTIONS = {"addition", "deletion"}
EVIDENCE_STATUS = {"primary", "secondary_public", "unverified"}


def _date(value: object, name: str) -> dt.date:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} is required")
    try:
        return dt.date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{name} must be YYYY-MM-DD") from exc


def _optional_date(value: object, name: str) -> dt.date | None:
    text = str(value or "").strip()
    return _date(text, name) if text else None


def _number(value: object, name: str) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        number = float(text)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def forced_shares(
    tracking_assets: float | int | None,
    weight_change: float | int | None,
    pre_event_price: float | int | None,
) -> float | None:
    """Estimate mandated shares from pre-event data, or return ``None``."""
    if tracking_assets is None or weight_change is None or pre_event_price is None:
        return None
    assets = float(tracking_assets)
    change = float(weight_change)
    price = float(pre_event_price)
    if not all(math.isfinite(value) for value in (assets, change, price)):
        return None
    if assets < 0 or price <= 0:
        return None
    return assets * change / price


def validate_event(row: Mapping[str, object]) -> None:
    """Validate the serialized event shape without making it eligible."""
    required = ("event_id", "index_id", "ticker", "direction", "effective_date", "source_url")
    missing = [name for name in required if not str(row.get(name) or "").strip()]
    if missing:
        raise ValueError("missing required fields: " + ", ".join(missing))
    if str(row["direction"]).strip() not in DIRECTIONS:
        raise ValueError("direction must be addition or deletion")
    status = str(row.get("evidence_status") or "unverified").strip()
    if status not in EVIDENCE_STATUS:
        raise ValueError("unknown evidence_status")
    effective = _date(row["effective_date"], "effective_date")
    announcement = _optional_date(row.get("announcement_date"), "announcement_date")
    availability = _optional_date(row.get("availability_date"), "availability_date")
    if announcement and announcement > effective:
        raise ValueError("announcement_date cannot be after effective_date")
    if availability and availability > effective:
        # This is a valid exclusion, so event_eligibility owns the decision.
        pass
    parsed = urlparse(str(row["source_url"]).strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("source_url must be an HTTP(S) URL")
    for name in ("target_weight_change", "tracking_assets", "pre_event_price", "forced_shares"):
        _number(row.get(name), name)
    for name in ("fund_assets_date", "price_date"):
        _optional_date(row.get(name), name)


def event_eligibility(row: Mapping[str, object], development_end: str) -> tuple[bool, str]:
    """Return whether the event can support a pre-effective flow test."""
    validate_event(row)
    effective = _date(row["effective_date"], "effective_date")
    boundary = _date(development_end, "development_end")
    if effective > boundary:
        return False, "outside development window"
    announcement = _optional_date(row.get("announcement_date"), "announcement_date")
    if announcement is None:
        return False, "missing announcement date"
    availability = _optional_date(row.get("availability_date"), "availability_date")
    if availability and availability > effective:
        return False, "evidence became available after the effective date"
    if str(row.get("evidence_status") or "").strip() != "primary":
        return False, "not primary evidence"
    for name in ("target_weight_change", "tracking_assets", "fund_assets_date", "pre_event_price", "price_date", "forced_shares"):
        if not str(row.get(name) or "").strip():
            return False, "missing forced quantity"
    assets_date = _date(row["fund_assets_date"], "fund_assets_date")
    price_date = _date(row["price_date"], "price_date")
    if assets_date >= effective or price_date >= effective:
        return False, "quantity input is not pre-effective"
    return True, "eligible"
