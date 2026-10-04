#!/usr/bin/env python3
"""Contracts for the driver vintages: the earliest-filed clock, quarter lengths, change arithmetic."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from build_complex_panels_pit import quarterly_earliest  # noqa: E402
from build_driver_vintages import build_input_rows  # noqa: E402


def payload(facts: list[dict]) -> dict:
    return {"units": {"USD": facts}}


def test_the_earliest_filing_wins_not_the_latest():
    facts = [
        {"start": "2020-01-01", "end": "2020-03-31", "val": 100.0, "filed": "2021-03-01",
         "form": "10-K", "fy": "2021", "fp": "Q1"},
        {"start": "2020-01-01", "end": "2020-03-31", "val": 100.0, "filed": "2020-04-28",
         "form": "10-Q", "fy": "2020", "fp": "Q1"},
    ]
    rows = quarterly_earliest(payload(facts), "T", "Tag")
    assert len(rows) == 1 and rows[0]["filed"] == "2020-04-28"


def test_annual_facts_are_dropped():
    facts = [
        {"start": "2020-01-01", "end": "2020-12-31", "val": 400.0, "filed": "2021-02-01"},
        {"start": "2020-01-01", "end": "2020-03-31", "val": 100.0, "filed": "2020-04-28"},
    ]
    rows = quarterly_earliest(payload(facts), "T", "Tag")
    assert len(rows) == 1 and rows[0]["period_end"] == "2020-03-31"


def test_input_rows_carry_change_previous_and_the_filing_clock():
    rows = [
        {"ticker": "T", "concept": "Tag", "period_start": "2020-01-01", "period_end": "2020-03-31",
         "value_usd": "100", "form": "10-Q", "filed": "2020-04-28"},
        {"ticker": "T", "concept": "Tag", "period_start": "2020-04-01", "period_end": "2020-06-30",
         "value_usd": "130", "form": "10-Q", "filed": "2020-07-28"},
    ]
    prepared, drops = build_input_rows(rows, "Tag", {"T": "power"})
    assert len(prepared) == 1                       # the first quarter has no prior value
    assert prepared[0]["previous_value"] == 100.0 and prepared[0]["change"] == 30.0
    assert prepared[0]["earliest_availability_utc"] == "2020-07-28T23:59:59+00:00"
    assert prepared[0]["group"] == "power" and drops["no_previous_value"] == 1


def test_the_preferred_concept_wins_on_a_shared_period():
    rows = [
        {"ticker": "T", "concept": "Other", "period_start": "2020-01-01", "period_end": "2020-03-31",
         "value_usd": "50", "form": "10-Q", "filed": "2020-04-28"},
        {"ticker": "T", "concept": "Tag", "period_start": "2020-01-01", "period_end": "2020-03-31",
         "value_usd": "60", "form": "10-Q", "filed": "2020-04-28"},
        {"ticker": "T", "concept": "Tag", "period_start": "2020-04-01", "period_end": "2020-06-30",
         "value_usd": "90", "form": "10-Q", "filed": "2020-07-28"},
    ]
    prepared, _ = build_input_rows(rows, "Tag", {})
    assert prepared[0]["previous_value"] == 60.0


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} driver-vintage contract(s) held")
