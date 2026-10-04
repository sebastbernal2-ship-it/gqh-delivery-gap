#!/usr/bin/env python3
"""Price sanity rule: a split-sized drop must be detected, a normal series must pass."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from repair_unadjusted_bars import suspicious  # noqa: E402


def test_a_ten_for_one_split_is_flagged():
    series = {"2024-06-07": 1200.0, "2024-06-10": 120.0, "2024-06-11": 121.0}
    assert suspicious(series) is True


def test_a_normal_series_passes():
    series = {"2024-06-07": 100.0, "2024-06-10": 101.5, "2024-06-11": 98.0}
    assert suspicious(series) is False
    assert suspicious({}) is False and suspicious({"2024-06-07": 100.0}) is False


def test_a_merger_sized_drop_is_flagged_but_a_bad_print_is_too():
    # any unexplained move beyond the bound is treated as a data problem, never as a return
    assert suspicious({"2024-01-02": 50.0, "2024-01-03": 30.0}) is True    # -40 percent
    assert suspicious({"2024-01-02": 50.0, "2024-01-03": 35.0}) is False   # -30 percent


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} price sanity contract(s) held")
