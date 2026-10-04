#!/usr/bin/env python3
"""Contracts for the three-sleeve combiner: alignment, weighting and inverse-volatility weights."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_three_sleeve_portfolio import align, inverse_vol_weights, weighted_daily  # noqa: E402


def series(dates_and_values: list[tuple[str, float]]) -> list[dict]:
    return [{"date": date, "net": value, "gross": value} for date, value in dates_and_values]


def test_align_keeps_only_the_common_calendar():
    left = series([("2024-01-02", 0.01), ("2024-01-03", 0.02), ("2024-01-04", 0.03)])
    right = series([("2024-01-03", 0.05), ("2024-01-04", -0.01), ("2024-01-05", 0.07)])
    dates, values = align([left, right])
    assert dates == ["2024-01-03", "2024-01-04"]
    assert values[0] == [0.02, 0.03] and values[1] == [0.05, -0.01]


def test_weighted_daily_averages_with_the_declared_weights():
    dates = ["2024-01-02", "2024-01-03"]
    values = [[0.10, 0.00], [0.00, 0.20], [0.20, 0.20]]
    equal = weighted_daily(dates, values, [[1 / 3, 1 / 3], [1 / 3, 1 / 3], [1 / 3, 1 / 3]])
    assert abs(equal[0]["net"] - 0.10) < 1e-12
    assert abs(equal[1]["net"] - (0.40 / 3)) < 1e-12
    only_first = weighted_daily(dates, values, [[1.0, 1.0], [0.0, 0.0], [0.0, 0.0]])
    assert abs(only_first[0]["net"] - 0.10) < 1e-12


def test_inverse_volatility_weights_favour_the_calmer_sleeve():
    values = [[0.01, -0.01] * 40, [0.001, -0.001] * 40]          # second sleeve is ten times calmer
    weights = inverse_vol_weights(values, window=20)
    assert weights[1][-1] > weights[0][-1]
    assert abs(weights[0][-1] + weights[1][-1] - 1.0) < 1e-9


def test_zero_volatility_sleeves_do_not_divide_by_zero():
    values = [[0.0] * 30, [0.0] * 30]
    weights = inverse_vol_weights(values, window=10)
    assert abs(weights[0][-1] + weights[1][-1] - 1.0) < 1e-9


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} three-sleeve contract(s) held")
