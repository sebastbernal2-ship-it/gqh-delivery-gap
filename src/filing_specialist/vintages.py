"""Point-in-time expectation vintages for RPO disclosures.

Each disclosure gets an expectation built only from observations that were public strictly
before it: the mean of the same quarter's prior changes for the same issuer, or the single prior
same-quarter change when only one exists. The current legacy column in `results/rpo-events.csv`
is a running median over all quarters and is retained for audit only; this module produces the
version a strategy may use, with the history count and span recorded next to every value.

Nothing here calculates returns or bins the surprise. Binning belongs to the consumer.
"""
from __future__ import annotations

import datetime
import statistics
from dataclasses import dataclass

from .panel import parse_clock

COLUMNS = (
    "ticker", "cik", "name", "concept", "sic", "group", "period_end", "quarter", "availability",
    "availability_resolution", "value", "previous_value", "change", "expectation_kind",
    "expectation_status", "history_count", "history_span_days", "expected_change_pit",
    "surprise_pit", "relative_surprise_pit",
    "relative_surprise_z", "change_relative_z", "label_edges", "in_sealed_window", "accession", "source_receipt",
)
MINIMUM_HISTORY = 2


@dataclass(frozen=True)
class Observation:
    ticker: str
    concept: str
    quarter: str
    availability: datetime.datetime
    change: float
    previous_value: float | None


def quarter_of(period_end: str) -> str:
    month = int(period_end[5:7])
    return f"Q{(month - 1) // 3 + 1}"


def observation_from_row(row: dict) -> tuple[Observation | None, str | None]:
    """A usable observation, or the reason the row is skipped."""
    ticker = (row.get("ticker") or "").strip()
    if not ticker:
        return None, "no_ticker"
    availability, _ = parse_clock(row.get("earliest_availability_utc") or "")
    if availability is None:
        return None, "no_availability"
    try:
        change = float(row["change"])
        raw_previous = row.get("previous_value")
        previous_value = (float(str(raw_previous).strip())
                          if raw_previous not in (None, "") and str(raw_previous).strip() else None)
        period_end = row["period_end"]
        if len(period_end) < 7:
            raise ValueError
    except (KeyError, TypeError, ValueError):
        return None, "no_change"
    return Observation(ticker, (row.get("concept") or "").strip(), quarter_of(period_end),
                       availability, change, previous_value), None


def expectation_for(observation: Observation, history: list[Observation],
                    minimum_history: int = MINIMUM_HISTORY) -> dict:
    """The declared point-in-time expectation from strictly earlier same-quarter observations."""
    usable = sorted((item for item in history
                     if item.ticker == observation.ticker and item.quarter == observation.quarter
                     and item.concept == observation.concept
                     and item.availability < observation.availability),
                    key=lambda item: item.availability)
    if len(usable) >= minimum_history:
        return {"kind": "same-quarter mean", "status": "measured",
                "expected": statistics.mean(item.change for item in usable),
                "count": len(usable),
                "span_days": (max(item.availability for item in usable)
                              - min(item.availability for item in usable)).days}
    if usable:
        return {"kind": "prior same-quarter", "status": "measured",
                "expected": usable[-1].change, "count": 1,
                "span_days": 0}
    return {"kind": "", "status": "missing", "expected": None, "count": 0, "span_days": None}


def build_vintages(rows: list[dict], minimum_history: int = MINIMUM_HISTORY) -> tuple[list[dict], dict]:
    observations = []
    drops: dict[str, int] = {}
    for row in rows:
        observation, reason = observation_from_row(row)
        if observation is None:
            drops[reason] = drops.get(reason, 0) + 1
            continue
        observations.append((row, observation))

    out = []
    all_observations = [item for _, item in observations]
    for row, observation in observations:
        expectation = expectation_for(observation, all_observations, minimum_history)
        change = observation.change
        expected = expectation["expected"]
        surprise = None if expected is None else change - expected
        relative = None
        if surprise is not None and observation.previous_value:
            relative = surprise / abs(observation.previous_value)
        record = {name: row.get(name, "") for name in COLUMNS}
        record.update({
            "ticker": observation.ticker,
            "quarter": observation.quarter,
            "availability": observation.availability.isoformat(),
            "expectation_kind": expectation["kind"],
            "expectation_status": expectation["status"],
            "history_count": expectation["count"],
            "history_span_days": expectation["span_days"] if expectation["span_days"] is not None else "",
            "expected_change_pit": expected if expected is not None else "",
            "surprise_pit": surprise if surprise is not None else "",
            "relative_surprise_pit": relative if relative is not None else "",
        })
        out.append(record)
    out.sort(key=lambda item: (item["availability"], item["ticker"], item["period_end"]))
    return out, drops
