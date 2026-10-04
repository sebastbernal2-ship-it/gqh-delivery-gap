#!/usr/bin/env python3
"""Contracts for the portfolio statistics: known arithmetic and a seeded blocked interval."""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.portfolio_stats import month_blocked_interval, portfolio_metrics  # noqa: E402


def daily(values: list[float], start_month: str = "2020-01") -> list[dict]:
    year, month = (int(part) for part in start_month.split("-"))
    rows = []
    for index, value in enumerate(values):
        month += 1
        if month > 12:
            year, month = year + 1, 1
        rows.append({"date": f"{year:04d}-{month:02d}-15", "net": value})
    return rows


def test_metrics_on_a_constant_series():
    rows = daily([0.001] * 252)
    result = portfolio_metrics(rows)
    assert result["days"] == 252
    assert abs(result["annual_return"] - 0.252) < 1e-9
    assert result["annual_vol"] == 0.0 and result["sharpe"] is None
    assert result["hit_rate"] == 1.0 and abs(result["max_drawdown"]) < 1e-12


def test_metrics_drawdown_and_volatility():
    rows = daily([0.01] * 10 + [-0.20] + [0.0] * 10)
    result = portfolio_metrics(rows)
    assert result["annual_vol"] > 0 and result["max_drawdown"] < -0.15
    assert portfolio_metrics([]) == {"days": 0}


def test_blocked_interval_is_seeded_and_contains_the_point():
    left = daily([0.002, -0.001, 0.003, -0.002, 0.001, 0.002, -0.001, 0.003])
    right = daily([0.001, -0.001, 0.001, -0.001, 0.001, 0.001, -0.001, 0.001])
    first = month_blocked_interval(left, right, resamples=200, seed=11)
    second = month_blocked_interval(left, right, resamples=200, seed=11)
    assert first == second
    assert first["months"] == 8 and first["lower"] <= first["point"] <= first["upper"]
    assert 0.0 <= first["share_positive"] <= 1.0


def test_a_short_overlap_returns_no_interval():
    result = month_blocked_interval(daily([0.01, 0.02]), daily([0.0, 0.0]))
    assert result["point"] is None and result["months"] == 2


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} portfolio statistics contract(s) held")
