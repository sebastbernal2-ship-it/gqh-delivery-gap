"""Point-in-time features and labels for the RPO surprise specialist.

The decision is one RPO disclosure. Every feature comes from that issuer's own strictly earlier
disclosures or from the disclosure's own vintage record, which was built from earlier data. The
label is the relative point-in-time surprise in five declared bins. Nothing here touches returns.
"""
from __future__ import annotations

import bisect
import math
import statistics
from dataclasses import dataclass

from .panel import parse_clock

BIN_EDGES = (-0.10, -0.02, 0.02, 0.10)
BIN_LABELS = ("surprise-down-large", "surprise-down-small", "flat",
              "surprise-up-small", "surprise-up-large")
GROUP_FLAGS = ("datacenter", "equipment", "utility", "contractor")
FEATURES = (
    "last_relative_surprise", "mean_relative_surprise_3", "last_relative_change",
    "mean_relative_change_3", "stdev_relative_change_4", "days_since_prior", "prior_count",
    "seasonal_history_count", "history_span_days", "log_previous_value", "quarter_number",
    *(f"group_{group}" for group in GROUP_FLAGS),
    "missing_prior", "missing_seasonal_history",
)


def surprise_bin(value: float) -> int:
    return bisect.bisect_right(BIN_EDGES, value)


@dataclass(frozen=True)
class Disclosure:
    ticker: str
    available: object
    relative: float
    change_relative: float | None
    previous_value: float | None
    quarter: int
    group: str


def disclosure_from_row(row: dict) -> tuple[Disclosure | None, str | None]:
    if (row.get("expectation_status") or "") != "measured":
        return None, "not_measured"
    relative = (row.get("relative_surprise_pit") or "").strip()
    if not relative:
        return None, "no_relative_surprise"
    ticker = (row.get("ticker") or "").strip()
    if not ticker:
        return None, "no_ticker"
    available, _ = parse_clock(row.get("availability") or "")
    if available is None:
        return None, "no_availability"
    try:
        previous = float(row["previous_value"]) if (row.get("previous_value") or "").strip() else None
        change = float(row["change"]) if (row.get("change") or "").strip() else None
        quarter = (int(row["period_end"][5:7]) - 1) // 3 + 1
    except (KeyError, TypeError, ValueError):
        return None, "no_quarter"
    change_relative = (change / abs(previous)) if (change is not None and previous) else None
    return Disclosure(ticker, available, float(relative), change_relative, previous, quarter,
                      (row.get("group") or "").strip()), None


def _prior_features(disclosure: Disclosure, prior: list[Disclosure]) -> dict:
    surprises = [item.relative for item in prior]
    changes = [item.change_relative for item in prior if item.change_relative is not None]
    latest = prior[-1] if prior else None
    return {
        "last_relative_surprise": surprises[-1] if surprises else None,
        "mean_relative_surprise_3": statistics.mean(surprises[-3:]) if surprises else None,
        "last_relative_change": changes[-1] if changes else None,
        "mean_relative_change_3": statistics.mean(changes[-3:]) if changes else None,
        "stdev_relative_change_4": (statistics.stdev(changes[-4:]) if len(changes) >= 2 else None),
        "days_since_prior": ((disclosure.available - latest.available).total_seconds() / 86400.0
                             if latest else None),
        "prior_count": float(len(prior)),
        "missing_prior": 0.0 if prior else 1.0,
    }


def prepare_rows(vintages: list[dict]) -> tuple[list[dict], dict]:
    by_ticker: dict[str, list[Disclosure]] = {}
    drops: dict[str, int] = {}
    for row in vintages:
        disclosure, reason = disclosure_from_row(row)
        if disclosure is None:
            drops[reason] = drops.get(reason, 0) + 1
            continue
        by_ticker.setdefault(disclosure.ticker, []).append((row, disclosure))  # type: ignore[arg-type]

    rows = []
    for ticker, items in sorted(by_ticker.items()):
        items.sort(key=lambda pair: pair[1].available)
        history: list[Disclosure] = []
        for record, disclosure in items:
            features = _prior_features(disclosure, history)
            seasonal_count = record.get("history_count") or ""
            span = record.get("history_span_days") or ""
            row = {
                "ticker": ticker,
                "period_end": record.get("period_end", ""),
                "label_available": disclosure.available.isoformat(),
                "label_relative_surprise": disclosure.relative,
                "label_bin": surprise_bin(disclosure.relative),
                "label_bin_label": BIN_LABELS[surprise_bin(disclosure.relative)],
                "seasonal_history_count": float(seasonal_count) if str(seasonal_count).strip() else 0.0,
                "history_span_days": float(span) if str(span).strip() else 0.0,
                "log_previous_value": (math.log1p(abs(disclosure.previous_value))
                                       if disclosure.previous_value else None),
                "quarter_number": float(disclosure.quarter),
                "missing_seasonal_history": 0.0 if str(seasonal_count).strip() else 1.0,
                **features,
            }
            for group in GROUP_FLAGS:
                row[f"group_{group}"] = 1.0 if disclosure.group == group else 0.0
            rows.append(row)
            history.append(disclosure)
    rows.sort(key=lambda item: item["label_available"])
    return rows, drops
