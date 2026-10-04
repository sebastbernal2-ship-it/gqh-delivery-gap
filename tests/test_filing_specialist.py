#!/usr/bin/env python3
"""Contracts for the filing specialist panel: clocks, no future input, labels."""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.model import chronological_split, compare  # noqa: E402
from filing_specialist.panel import (Filing, Obligation, Revision, build_panel,  # noqa: E402
                                     parse_clock, relative_surprise, surprise_bin)

UTC = datetime.timezone.utc


def stamp(day: str, hour: int = 12) -> datetime.datetime:
    year, month, date = (int(part) for part in day.split("-"))
    return datetime.datetime(year, month, date, hour, tzinfo=UTC)


def filing(day: str, accession: str, form: str = "8-K", items: str = "") -> Filing:
    return Filing("PWR", accession, form, items, stamp(day), False)


def obligation(day: str, value: float, previous: float, change: float) -> Obligation:
    return Obligation("PWR", "us-gaap:RevenueRemainingPerformanceObligation", "2024-09-30",
                      value, previous, change, stamp(day), False)


def revision(day: str, surprise: float) -> Revision:
    return Revision("PWR", "us-gaap:RevenueRemainingPerformanceObligation", "2024-09-30",
                    1.0, 0.0, surprise, stamp(day))


def test_clock_parsing_flags_date_only_values():
    parsed, coarse = parse_clock("2024-09-30")
    assert parsed == datetime.datetime(2024, 9, 30, 23, 59, 59, tzinfo=UTC), parsed
    assert coarse is True
    parsed, coarse = parse_clock("2024-09-30T14:00:00+00:00")
    assert parsed == stamp("2024-09-30", 14) and coarse is False
    parsed, coarse = parse_clock("2024-09-30T14:00:00")
    assert parsed.tzinfo is not None and coarse is True
    assert parse_clock("")[0] is None


def test_bins_follow_the_left_closed_convention():
    assert surprise_bin(-0.06) == 0
    assert surprise_bin(-0.05) == 1
    assert surprise_bin(-0.01) == 2
    assert surprise_bin(0.01) == 3
    assert surprise_bin(0.05) == 4
    assert relative_surprise(10.0, -100.0) == 0.1
    assert relative_surprise(10.0, 0.0) is None


def test_deciding_filing_is_strictly_earlier_than_the_label():
    filings = [filing("2024-09-01", "early"), filing("2024-10-01", "at-label"),
               filing("2024-11-01", "after-label")]
    panel = build_panel(filings, [obligation("2024-08-01", 100.0, 90.0, 10.0)],
                        [revision("2024-10-01", 5.0)])
    assert len(panel.rows) == 1
    row = panel.rows[0]
    assert row["filing_accession"] == "early"
    assert row["candidate_filings"] == 1
    assert row["days_since_last_filing"] == 30.0


def test_future_obligations_are_not_features():
    filings = [filing("2024-01-01", "f1")]
    obligations = [obligation("2024-02-01", 100.0, 90.0, 10.0),
                   obligation("2024-12-01", 500.0, 100.0, 400.0)]
    panel = build_panel(filings, obligations, [revision("2024-10-01", 5.0)])
    row = panel.rows[0]
    assert abs(row["last_change_rel"] - 10.0 / 90.0) < 1e-12
    assert row["missing_last_obligation"] == 0.0


def test_unknown_features_stay_null_with_flags():
    filings = [filing("2024-01-01", "f1", form="10-Q", items="1.01,2.02,7.01")]
    # The matching obligation supplies the label's own previous value only; it is published at the
    # decision instant, so the strict-before rule keeps it out of the features.
    obligations = [Obligation("PWR", "us-gaap:RevenueRemainingPerformanceObligation", "2024-09-30",
                              100.0, 90.0, 10.0, stamp("2024-10-01"), False)]
    panel = build_panel(filings, obligations, [revision("2024-10-01", 5.0)])
    row = panel.rows[0]
    assert row["last_change_rel"] is None and row["missing_last_change_rel"] == 1.0
    assert row["last_surprise_rel"] is None and row["missing_last_surprise_rel"] == 1.0
    assert row["days_since_last_obligation"] is None and row["missing_last_obligation"] == 1.0
    assert row["form_is_8k"] == 0.0
    assert row["has_item_101"] == 1.0 and row["has_item_202"] == 1.0 and row["has_item_701"] == 1.0


def test_panel_counts_drops_with_a_reason():
    panel = build_panel([], [obligation("2024-01-01", 100.0, 90.0, 10.0)],
                        [revision("2024-10-01", 5.0)])
    assert panel.rows == []
    assert panel.drops == {"no_filing_before_label": 1}
    panel = build_panel([filing("2024-01-01", "f1")], [],
                        [revision("2024-10-01", 5.0)])
    assert panel.drops == {"no_previous_value": 1}


def test_split_is_chronological_and_models_are_finite():
    rows = []
    for index in range(40):
        day = f"2024-{1 + index // 28:02d}-{1 + index % 28:02d}"
        rows.append({"label_available": stamp(day).isoformat(),
                     "label_bin": index % 3,
                     "feature_a": float(index % 5),
                     "feature_b": float((index * 7) % 11)})
    ordered = sorted(rows, key=lambda row: row["label_available"])
    train, test = chronological_split(rows, 0.7)
    assert max(row["label_available"] for row in train) < min(row["label_available"] for row in test)
    report = compare(rows, ("feature_a", "feature_b"), fraction=0.7)
    for name in ("prevalence", "softmax"):
        assert report[name]["rows"] == len(test)
        assert 0.0 <= report[name]["accuracy"] <= 1.0
        assert report[name]["log_loss"] > 0.0
        assert report[name]["brier"] > 0.0
    assert set(report["split"]["classes"]) == {0, 1, 2}


def test_split_never_shares_a_timestamp():
    rows = [{"label_available": "2024-01-01T12:00:00+00:00", "label_bin": 0, "a": 1.0}
            for _ in range(6)]
    rows += [{"label_available": "2024-01-02T12:00:00+00:00", "label_bin": 1, "a": 2.0}
             for _ in range(6)]
    train, test = chronological_split(rows, 0.5)
    assert max(row["label_available"] for row in train) < min(row["label_available"] for row in test)
    assert len(train) == 6 and len(test) == 6


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} filing specialist contract(s) held")
