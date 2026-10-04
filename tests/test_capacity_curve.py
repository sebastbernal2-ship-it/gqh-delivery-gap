#!/usr/bin/env python3
"""Contracts for the capacity curve: the limiting formula, trailing medians, missing data."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_capacity_curve import capacity_of  # noqa: E402


def test_capacity_is_the_participation_of_the_binding_name():
    positions = {"2024-01-02": {"AAA": 0.8, "BBB": 0.2}}
    adv = {("AAA", "2024-01-02"): 1_000_000.0, ("BBB", "2024-01-02"): 10_000_000.0}
    result = capacity_of(positions, adv, 0.01)
    # AAA needs 0.8 of the capital, so its dollar volume limits the fund to 1 percent of that name
    assert abs(result["median"] - 0.01 * 1_000_000.0 / 0.8) < 1e-6
    assert result["binding_names"] == {"AAA": 1}


def test_names_without_adv_are_skipped_and_empty_days_ignored():
    positions = {"2024-01-02": {"AAA": 0.5, "CCC": 0.5}, "2024-01-03": {"CCC": 1.0}}
    adv = {("AAA", "2024-01-02"): 2_000_000.0}
    result = capacity_of(positions, adv, 0.01)
    assert result["dates"] == 1                     # the second day has no usable name
    assert abs(result["median"] - 0.01 * 2_000_000.0 / 0.5) < 1e-6
    assert capacity_of({}, adv, 0.01) == {"dates": 0}


def test_the_binding_name_is_the_one_with_the_largest_weight_to_volume_ratio():
    positions = {"2024-01-02": {"HEAVY": 0.9, "LIGHT": 0.1}}
    adv = {("HEAVY", "2024-01-02"): 5_000_000.0, ("LIGHT", "2024-01-02"): 1_000_000.0}
    result = capacity_of(positions, adv, 0.05)
    assert list(result["binding_names"]) == ["HEAVY"]
    assert abs(result["p10"] - 0.05 * 5_000_000.0 / 0.9) < 1e-6


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} capacity contract(s) held")
