#!/usr/bin/env python3
"""Contracts for the return bridge: entry rule, horizon arithmetic, ranks, spread and cost."""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.event_returns import (attach_returns, forward_return, group_means,  # noqa: E402
                                             long_short, quintile_rows, rank, rank_ic)

SERIES = {"2020-01-02": 100.0, "2020-01-03": 110.0, "2020-01-06": 121.0, "2020-01-07": 133.1}


def test_entry_is_the_first_session_strictly_after_the_decision():
    # decision on 2020-01-02: entry is 2020-01-03 at 110, one session later is 121
    assert abs(forward_return(SERIES, "2020-01-02", 1) - (121.0 / 110.0 - 1)) < 1e-12
    # decision on the last available day: no entry price exists
    assert math.isnan(forward_return(SERIES, "2020-01-07", 1))
    # horizon beyond the data is a null, never a zero
    assert math.isnan(forward_return(SERIES, "2020-01-02", 5))


def test_horizon_counts_trading_sessions():
    assert abs(forward_return(SERIES, "2020-01-02", 2) - (133.1 / 110.0 - 1)) < 1e-12


def test_attach_returns_covers_and_reports():
    rows = [{"ticker": "A", "label_available": "2020-01-02T23:59:59+00:00"},
            {"ticker": "B", "label_available": "2020-01-02T23:59:59+00:00"}]
    report = attach_returns(rows, {"A": SERIES, "B": {}}, horizons=(1,))
    assert report["rows_with_the_longest_horizon"] == 1
    assert rows[0]["fwd_ret_1"] > 0 and math.isnan(rows[1]["fwd_ret_1"])


def test_rank_and_information_coefficient():
    assert rank([3.0, 1.0, 2.0, 2.0]) == [4.0, 1.0, 2.5, 2.5]
    assert abs(rank_ic([1.0, 2.0, 3.0], [2.0, 4.0, 6.0]) - 1.0) < 1e-12
    assert abs(rank_ic([1.0, 2.0, 3.0], [6.0, 4.0, 2.0]) + 1.0) < 1e-12
    assert math.isnan(rank_ic([1.0, 2.0], [1.0, 2.0]))


def test_long_short_charges_costs_and_needs_both_sides():
    rows = [{"predicted_bin": 4, "fwd_ret_5": 0.03}, {"predicted_bin": 4, "fwd_ret_5": 0.01},
            {"predicted_bin": 0, "fwd_ret_5": -0.02}, {"predicted_bin": 0, "fwd_ret_5": -0.01},
            {"predicted_bin": 2, "fwd_ret_5": 0.99}]
    result = long_short(rows, 5, 4, 0, cost_bps=20)
    assert result["n_long"] == 2 and result["n_short"] == 2
    assert abs(result["spread"] - (0.02 - (-0.015))) < 1e-12
    assert abs(result["net"] - (result["spread"] - 0.002)) < 1e-12
    empty = long_short([{"predicted_bin": 2, "fwd_ret_5": 0.01}], 5, 4, 0)
    assert empty["spread"] is None


def test_group_means_and_quintiles():
    rows = [{"predicted_bin": 0, "fwd_ret_1": -0.01}, {"predicted_bin": 0, "fwd_ret_1": -0.03},
            {"predicted_bin": 1, "fwd_ret_1": 0.02}]
    groups = group_means(rows, "predicted_bin", "fwd_ret_1")
    assert groups[0] == {"group": 0, "n": 2, "mean": -0.02}
    assert groups[1]["mean"] == 0.02
    quintile_source = [{"confidence": index / 10, "fwd_ret_1": index / 100}
                       for index in range(10)]
    out = quintile_rows(quintile_source, 1)
    assert len(out) == 5 and out[0]["n"] == 2 and out[-1]["mean_return"] > out[0]["mean_return"]


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} return-bridge contract(s) held")
