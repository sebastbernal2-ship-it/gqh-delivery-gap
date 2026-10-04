"""Filing features joined to the RPO disclosure rows, strictly earlier than each decision.

The question this supports is the equity bridge in its narrowest form: does what a firm filed add
anything to what it already disclosed, for forecasting its next RPO surprise.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass

from .panel import parse_clock

FILING_FEATURES = (
    "has_filing", "form_is_8k", "has_item_101", "has_item_202", "has_item_701", "has_item_801",
    "filings_last_90d", "days_since_last_filing", "days_since_last_8k",
)


@dataclass(frozen=True)
class Filing:
    ticker: str
    accession: str
    form: str
    items: str
    available: datetime.datetime


def load_filings(rows: list[dict]) -> dict[str, list[Filing]]:
    """Per-ticker filings with resolved clocks, sorted by availability."""
    by_ticker: dict[str, list[Filing]] = {}
    for row in rows:
        ticker = (row.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        available, _ = parse_clock(row.get("earliest_availability_utc")
                                   or row.get("acceptance_utc") or row.get("filed_date", ""))
        if available is None:
            continue
        by_ticker.setdefault(ticker, []).append(
            Filing(ticker, row.get("accession", ""), row.get("form", ""), row.get("items", ""),
                   available))
    for items in by_ticker.values():
        items.sort(key=lambda item: item.available)
    return by_ticker


def _latest_before(items: list[Filing], when: datetime.datetime) -> int | None:
    low, high, found = 0, len(items), None
    while low < high:
        middle = (low + high) // 2
        if items[middle].available < when:
            found, low = middle, middle + 1
        else:
            high = middle
    return found


def filing_features(items: list[Filing], decision: datetime.datetime) -> dict:
    index = _latest_before(items, decision)
    features = {name: None for name in FILING_FEATURES}
    features["has_filing"] = 0.0
    if index is None:
        return features
    latest = items[index]
    prior = [item for item in items[:index + 1] if (decision - item.available).days <= 90]
    features.update({
        "has_filing": 1.0,
        "form_is_8k": 1.0 if latest.form.startswith("8-K") else 0.0,
        "has_item_101": 1.0 if "1.01" in latest.items else 0.0,
        "has_item_202": 1.0 if "2.02" in latest.items else 0.0,
        "has_item_701": 1.0 if "7.01" in latest.items else 0.0,
        "has_item_801": 1.0 if "8.01" in latest.items else 0.0,
        "filings_last_90d": float(len(prior)),
        "days_since_last_filing": (decision - latest.available).total_seconds() / 86400.0,
    })
    eights = [item for item in items[:index + 1] if item.form.startswith("8-K")]
    if eights:
        features["days_since_last_8k"] = (decision - eights[-1].available).total_seconds() / 86400.0
    return features


def augment_rows(rows: list[dict], filings: dict[str, list[Filing]]) -> tuple[list[dict], dict]:
    """Attach filing features to prepared RPO rows; a missing filing stays null with a flag."""
    out = []
    drops = {"no_filing_for_issuer": 0}
    for row in rows:
        decision = datetime.datetime.fromisoformat(row["label_available"])
        items = filings.get(row["ticker"].upper(), [])
        if not items:
            drops["no_filing_for_issuer"] += 1
        enriched = dict(row)
        enriched.update(filing_features(items, decision))
        out.append(enriched)
    return out, drops
