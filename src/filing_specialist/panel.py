"""Point-in-time join from a filing to the next obligation revision.

One row per obligation revision. The decision is the latest filing strictly before that
revision's availability, and every feature is known strictly before the decision time. The
label is the revision's surprise relative to its own previous value. Nothing here calculates
returns, sizes a position, or opens a sealed window.

Row-level rules:

- a date-only clock reads as the end of that day in UTC and is flagged;
- a filing at exactly the decision time is excluded, because the decision needs a strictly
  earlier observation;
- an unknown feature stays null and carries a missingness flag, never a filled-in zero.
"""
from __future__ import annotations

import bisect
import csv
import datetime
import statistics
from dataclasses import dataclass, field
from pathlib import Path

BIN_EDGES = (-0.05, -0.01, 0.01, 0.05)
BIN_LABELS = ("slip-large", "slip-small", "flat", "beat-small", "beat-large")
FEATURES = (
    "form_is_8k",
    "has_item_101",
    "has_item_202",
    "has_item_701",
    "filings_last_90d",
    "days_since_last_filing",
    "last_change_rel",
    "trailing_mean_change_rel",
    "prior_revision_count",
    "last_surprise_rel",
    "days_since_last_obligation",
    "concept_is_rpo",
)
FLAG_FEATURES = ("missing_last_change_rel", "missing_last_surprise_rel", "missing_last_obligation")


def parse_clock(value: str) -> tuple[datetime.datetime | None, bool]:
    """ISO timestamp with timezone. A date-only value reads as end of day UTC, flagged as coarse."""
    if value is None or not value.strip():
        return None, False
    text = value.strip()
    if "T" not in text:
        try:
            day = datetime.date.fromisoformat(text)
        except ValueError:
            return None, False
        return (datetime.datetime(day.year, day.month, day.day, 23, 59, 59, tzinfo=datetime.timezone.utc),
                True)
    try:
        stamp = datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None, False
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=datetime.timezone.utc)
        return stamp, True
    return stamp, False


@dataclass(frozen=True)
class Filing:
    ticker: str
    accession: str
    form: str
    items: str
    available: datetime.datetime
    clock_flag: bool


@dataclass(frozen=True)
class Obligation:
    ticker: str
    concept: str
    period_end: str
    value: float
    previous_value: float | None
    change: float | None
    available: datetime.datetime
    clock_flag: bool


@dataclass(frozen=True)
class Revision:
    ticker: str
    concept: str
    period_end: str
    change: float
    typical_change: float
    surprise: float
    available: datetime.datetime


@dataclass
class Panel:
    rows: list[dict] = field(default_factory=list)
    drops: dict[str, int] = field(default_factory=dict)

    def drop(self, reason: str) -> None:
        self.drops[reason] = self.drops.get(reason, 0) + 1


def load_filings(path: Path) -> list[Filing]:
    out = []
    for row in csv.DictReader(path.open()):
        available, coarse = parse_clock(row.get("earliest_availability_utc") or row.get("acceptance_utc")
                                        or row.get("filed_date", ""))
        if available is None or not row.get("ticker"):
            continue
        out.append(Filing(row["ticker"].strip(), row.get("accession", ""), row.get("form", ""),
                          row.get("items", ""), available, coarse))
    return sorted(out, key=lambda item: item.available)


def load_obligations(path: Path) -> list[Obligation]:
    out = []
    for row in csv.DictReader(path.open()):
        available, coarse = parse_clock(row.get("earliest_availability_utc") or row.get("acceptance_utc")
                                        or row.get("filed", ""))
        if available is None or not row.get("ticker"):
            continue
        try:
            value = float(row["value"])
        except (KeyError, TypeError, ValueError):
            continue
        previous = float(row["previous_value"]) if (row.get("previous_value") or "").strip() else None
        change = float(row["change"]) if (row.get("change") or "").strip() else None
        out.append(Obligation(row["ticker"].strip(), row.get("concept", ""), row.get("period_end", ""),
                              value, previous, change, available, coarse))
    return sorted(out, key=lambda item: item.available)


def load_revisions(path: Path) -> list[Revision]:
    out = []
    for row in csv.DictReader(path.open()):
        available, _ = parse_clock(row.get("available", ""))
        if available is None or not row.get("ticker"):
            continue
        try:
            change = float(row["change"])
            typical = float(row["typical_change"])
            surprise = float(row["surprise"])
        except (KeyError, TypeError, ValueError):
            continue
        out.append(Revision(row["ticker"].strip(), row.get("concept", ""), row.get("period_end", ""),
                            change, typical, surprise, available))
    return sorted(out, key=lambda item: item.available)


def relative_surprise(surprise: float, previous_value: float | None) -> float | None:
    if previous_value is None or previous_value == 0.0:
        return None
    return surprise / abs(previous_value)


def surprise_bin(value: float) -> int:
    """Left-closed bins on the relative surprise; the convention matches the risk track."""
    return bisect.bisect_right(BIN_EDGES, value)


def _days(left: datetime.datetime, right: datetime.datetime) -> float:
    return (left - right).total_seconds() / 86400.0


def feature_row(ticker: str, concept: str, decision: datetime.datetime, filings: list[Filing],
                obligations: list[Obligation], revisions: list[Revision], deciding: Filing) -> dict:
    same_ticker = [item for item in filings if item.ticker == ticker and item.available < decision]
    recent = [item for item in same_ticker if (decision - item.available).days <= 90]
    concept_obligations = [item for item in obligations
                           if item.ticker == ticker and item.concept == concept
                           and item.available < decision]
    concept_revisions = [item for item in revisions
                         if item.ticker == ticker and item.concept == concept
                         and item.available < decision]
    row = {
        "ticker": ticker,
        "concept": concept,
        "decision_time": decision.isoformat(),
        "filing_accession": deciding.accession,
        "filing_form": deciding.form,
        "decision_clock_coarse": deciding.clock_flag,
        "form_is_8k": 1.0 if deciding.form.startswith("8-K") else 0.0,
        "has_item_101": 1.0 if "1.01" in deciding.items else 0.0,
        "has_item_202": 1.0 if "2.02" in deciding.items else 0.0,
        "has_item_701": 1.0 if "7.01" in deciding.items else 0.0,
        "filings_last_90d": float(len(recent)),
        "days_since_last_filing": (round(_days(decision, same_ticker[-1].available), 3)
                                   if same_ticker else None),
        "prior_revision_count": float(len(concept_revisions)),
        "concept_is_rpo": 1.0 if concept.endswith("RevenueRemainingPerformanceObligation") else 0.0,
    }
    if concept_obligations:
        latest = concept_obligations[-1]
        last_change_rel = (latest.change / abs(latest.previous_value)
                           if latest.change is not None and latest.previous_value else None)
        window = [item.change / abs(item.previous_value) for item in concept_obligations[-4:]
                  if item.change is not None and item.previous_value]
        row["last_change_rel"] = last_change_rel
        row["trailing_mean_change_rel"] = statistics.mean(window) if window else None
        row["days_since_last_obligation"] = round(_days(decision, latest.available), 3)
    else:
        row["last_change_rel"] = None
        row["trailing_mean_change_rel"] = None
        row["days_since_last_obligation"] = None
    if concept_revisions:
        previous = None
        for obligation in concept_obligations:
            if obligation.period_end == concept_revisions[-1].period_end:
                previous = obligation.previous_value
                break
        value = relative_surprise(concept_revisions[-1].surprise, previous)
        row["last_surprise_rel"] = value
        row["prior_revision_period_end"] = concept_revisions[-1].period_end
    else:
        row["last_surprise_rel"] = None
        row["prior_revision_period_end"] = None
    for name in FLAG_FEATURES:
        row[name] = 0.0
    if row["last_change_rel"] is None:
        row["missing_last_change_rel"] = 1.0
    if row["last_surprise_rel"] is None:
        row["missing_last_surprise_rel"] = 1.0
    if row["days_since_last_obligation"] is None:
        row["missing_last_obligation"] = 1.0
    return row


def build_panel(filings: list[Filing], obligations: list[Obligation],
                revisions: list[Revision]) -> Panel:
    panel = Panel()
    for label in revisions:
        candidates = [item for item in filings
                      if item.ticker == label.ticker and item.available < label.available]
        if not candidates:
            panel.drop("no_filing_before_label")
            continue
        deciding = candidates[-1]
        previous = None
        for obligation in obligations:
            if (obligation.ticker == label.ticker and obligation.concept == label.concept
                    and obligation.period_end == label.period_end):
                previous = obligation.previous_value
                break
        if previous is None:
            panel.drop("no_previous_value")
            continue
        value = relative_surprise(label.surprise, previous)
        if value is None:
            panel.drop("zero_previous_value")
            continue
        row = feature_row(label.ticker, label.concept, label.available, filings, obligations,
                          revisions, deciding)
        row.update({
            "label_period_end": label.period_end,
            "label_available": label.available.isoformat(),
            "label_change": label.change,
            "label_typical_change": label.typical_change,
            "label_surprise": label.surprise,
            "label_relative_surprise": value,
            "label_bin": surprise_bin(value),
            "label_bin_label": BIN_LABELS[surprise_bin(value)],
            "candidate_filings": len(candidates),
        })
        panel.rows.append(row)
    panel.rows.sort(key=lambda row: row["label_available"])
    return panel
