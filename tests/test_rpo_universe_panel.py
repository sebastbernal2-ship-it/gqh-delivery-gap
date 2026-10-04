#!/usr/bin/env python3
"""Contracts for the broad RPO panel: acceptance clocks, quarter gaps, change arithmetic, drops."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_rpo_universe_panel import prepared_rows  # noqa: E402


def frame(cik: int, end: str, value: float, accession: str) -> tuple[tuple[int, str], dict]:
    return (cik, end), {"cik": cik, "end": end, "val": value, "accn": accession,
                        "entityName": f"CIK{cik}"}


def filer(cik: int, stamps: dict[str, str]) -> tuple[int, dict]:
    return cik, {"ticker": f"T{cik}", "name": f"Filer {cik}", "sic": "1234", "stamps": stamps}


def test_acceptance_clock_and_change_arithmetic():
    frames = dict([frame(7, "2020-03-31", 100.0, "A1"), frame(7, "2020-06-30", 130.0, "A2")])
    filers = dict([filer(7, {"A1": "2020-04-28T16:00:00.000Z", "A2": "2020-07-28T16:00:00.000Z"})])
    rows, drops = prepared_rows(frames, filers)
    assert len(rows) == 1
    assert rows[0]["change"] == 30.0 and rows[0]["previous_value"] == 100.0
    assert rows[0]["earliest_availability_utc"] == "2020-07-28T16:00:00.000Z"
    assert rows[0]["availability_resolution"] == "accession acceptance timestamp"
    assert drops["no_previous_value"] == 1


def test_a_missing_acceptance_stamp_drops_the_row():
    frames = dict([frame(7, "2020-03-31", 100.0, "A1"), frame(7, "2020-06-30", 130.0, "A2")])
    filers = dict([filer(7, {"A1": "2020-04-28T16:00:00.000Z"})])
    rows, drops = prepared_rows(frames, filers)
    assert rows == [] and drops["no_acceptance_stamp"] == 1


def test_a_quarter_gap_is_enforced_and_zeros_are_dropped():
    frames = dict([frame(7, "2020-03-31", 100.0, "A1"), frame(7, "2020-09-30", 130.0, "A2"),
                   frame(8, "2020-03-31", 0.0, "B1")])
    filers = dict([filer(7, {"A1": "2020-04-28T16:00:00.000Z", "A2": "2020-10-28T16:00:00.000Z"}),
                   filer(8, {"B1": "2020-04-28T16:00:00.000Z"})])
    rows, drops = prepared_rows(frames, filers)
    assert rows == []
    assert drops["gap_not_quarterly"] == 1 and drops["no_positive_value"] == 1


def test_a_filer_without_submissions_is_dropped():
    frames = dict([frame(9, "2020-03-31", 100.0, "A1")])
    rows, drops = prepared_rows(frames, {})
    assert rows == [] and drops["no_submissions"] == 1


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} broad-panel contract(s) held")
