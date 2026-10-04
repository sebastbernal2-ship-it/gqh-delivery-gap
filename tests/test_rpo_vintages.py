#!/usr/bin/env python3
"""Contracts for the point-in-time RPO vintages: no future input, seasonality, missingness."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.vintages import build_vintages, observation_from_row, quarter_of  # noqa: E402


def row(ticker: str, period_end: str, change: float, availability: str,
        previous: float = 100.0) -> dict:
    return {"ticker": ticker, "period_end": period_end, "change": str(change),
            "previous_value": str(previous), "earliest_availability_utc": availability,
            "cik": "1", "name": "n", "sic": "1", "group": "g",
            "in_sealed_window": "False", "accession": "a", "source_receipt": "r"}


def test_quarter_mapping():
    assert quarter_of("2024-03-31") == "Q1"
    assert quarter_of("2024-06-30") == "Q2"
    assert quarter_of("2024-12-31") == "Q4"


def test_expectation_uses_only_earlier_same_quarter_rows():
    rows = [
        row("T", "2022-03-31", 10.0, "2022-05-01T00:00:00+00:00"),
        row("T", "2022-06-30", 99.0, "2022-08-01T00:00:00+00:00"),
        row("T", "2023-03-31", 20.0, "2023-05-01T00:00:00+00:00"),
        row("T", "2024-03-31", 30.0, "2024-05-01T00:00:00+00:00"),
    ]
    vintages, _ = build_vintages(rows)
    by_period = {item["period_end"]: item for item in vintages}
    first = by_period["2022-03-31"]
    assert first["expectation_status"] == "missing" and first["expected_change_pit"] == ""
    second = by_period["2023-03-31"]
    assert second["expectation_kind"] == "prior same-quarter"
    assert float(second["expected_change_pit"]) == 10.0
    third = by_period["2024-03-31"]
    assert third["expectation_kind"] == "same-quarter mean"
    assert float(third["expected_change_pit"]) == 15.0
    assert third["history_count"] == 2
    assert float(third["surprise_pit"]) == 15.0


def test_future_rows_cannot_change_past_expectations():
    rows = [
        row("T", "2022-03-31", 10.0, "2022-05-01T00:00:00+00:00"),
        row("T", "2023-03-31", 20.0, "2023-05-01T00:00:00+00:00"),
    ]
    before, _ = build_vintages(rows)
    later = rows + [row("T", "2026-03-31", 10_000.0, "2026-05-01T00:00:00+00:00")]
    after, _ = build_vintages(later)
    key = lambda items: [(item["period_end"], item["expected_change_pit"], item["history_count"])
                         for item in items if item["period_end"] in ("2022-03-31", "2023-03-31")]
    assert key(before) == key(after)


def test_equal_availability_is_not_history():
    rows = [
        row("T", "2023-03-31", 10.0, "2024-05-01T00:00:00+00:00"),
        row("T", "2024-03-31", 20.0, "2024-05-01T00:00:00+00:00"),
    ]
    vintages, _ = build_vintages(rows)
    later = [item for item in vintages if item["period_end"] == "2024-03-31"][0]
    assert later["expectation_status"] == "missing"


def test_rows_are_skipped_with_a_reason_and_never_faked():
    rows = [
        {"ticker": "", "period_end": "2024-03-31", "change": "1", "previous_value": "1",
         "earliest_availability_utc": "2024-05-01T00:00:00+00:00"},
        {"ticker": "T", "period_end": "2024-03-31", "change": "", "previous_value": "1",
         "earliest_availability_utc": "2024-05-01T00:00:00+00:00"},
        {"ticker": "T", "period_end": "2024-03-31", "change": "1", "previous_value": "1",
         "earliest_availability_utc": ""},
    ]
    vintages, drops = build_vintages(rows)
    assert vintages == []
    assert drops == {"no_ticker": 1, "no_change": 1, "no_availability": 1}


def test_the_output_carries_the_decision_clock():
    rows = [row("T", "2022-03-31", 10.0, "2022-05-01T00:00:00+00:00"),
            row("T", "2023-03-31", 20.0, "2023-05-01T00:00:00+00:00")]
    vintages, _ = build_vintages(rows)
    for item in vintages:
        assert item["availability"], "the availability column must never be empty"
    assert vintages[0]["availability"] == "2022-05-01T00:00:00+00:00"
    assert vintages[1]["availability"] == "2023-05-01T00:00:00+00:00"


def test_different_concepts_do_not_share_history():
    rows = [
        {"ticker": "T", "concept": "A", "period_end": "2022-03-31", "change": "100",
         "previous_value": "1000", "earliest_availability_utc": "2022-05-01T00:00:00+00:00"},
        {"ticker": "T", "concept": "B", "period_end": "2023-03-31", "change": "5",
         "previous_value": "1000", "earliest_availability_utc": "2023-05-01T00:00:00+00:00"},
        {"ticker": "T", "concept": "B", "period_end": "2024-03-31", "change": "7",
         "previous_value": "1000", "earliest_availability_utc": "2024-05-01T00:00:00+00:00"},
    ]
    vintages, _ = build_vintages(rows)
    by_key = {(item["concept"], item["period_end"]): item for item in vintages}
    assert by_key[("B", "2023-03-31")]["expectation_status"] == "missing"
    assert by_key[("B", "2024-03-31")]["expectation_kind"] == "prior same-quarter"
    assert float(by_key[("B", "2024-03-31")]["expected_change_pit"]) == 5.0


def test_relative_surprise_is_null_without_a_previous_value():
    rows = [row("T", "2022-03-31", 10.0, "2022-05-01T00:00:00+00:00"),
            row("T", "2023-03-31", 20.0, "2023-05-01T00:00:00+00:00", previous=0.0)]
    vintages, _ = build_vintages(rows)
    later = [item for item in vintages if item["period_end"] == "2023-03-31"][0]
    assert later["surprise_pit"] == 10.0
    assert later["relative_surprise_pit"] == ""


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} rpo vintage contract(s) held")
