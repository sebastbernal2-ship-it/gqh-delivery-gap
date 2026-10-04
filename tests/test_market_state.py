#!/usr/bin/env python3
"""Contracts for the market-state specialist: strict cutoffs, known arithmetic, nulls not zeros."""
from __future__ import annotations

import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.market_state import (build, distance_from_high, feature_row,  # noqa: E402
                                            realized_vol, trailing_return, window)


def series_from_closes(closes: list[float], start: str = "2020-01-01") -> dict[str, float]:
    import datetime
    day = datetime.date.fromisoformat(start)
    out = {}
    for close in closes:
        out[day.isoformat()] = close
        day += datetime.timedelta(days=1)
    return out


def test_trailing_return_and_window_cutoff():
    closes = [100.0 + index for index in range(70)]
    assert abs(trailing_return(closes, 60) - (closes[-1] / closes[-61] - 1)) < 1e-12
    series = series_from_closes([100.0, 101.0, 102.0], "2020-03-01")
    days, values = window(series, "2020-03-03")
    assert days == ["2020-03-01", "2020-03-02"] and values == [100.0, 101.0]
    days, _ = window(series, "2020-03-01")
    assert days == []                                   # the decision day itself is excluded


def test_insufficient_history_is_null_not_zero():
    assert math.isnan(trailing_return([100.0, 101.0], 60))
    assert math.isnan(realized_vol([100.0], 60))
    assert math.isnan(distance_from_high([], 252))
    assert abs(distance_from_high([100.0, 50.0], 252) - (-0.5)) < 1e-12


def same(left: float, right: float) -> bool:
    return (left == right) or (math.isnan(left) and math.isnan(right))


def test_a_change_on_or_after_the_decision_does_not_move_a_feature():
    closes = [100.0 + index * 0.5 for index in range(300)]
    series = series_from_closes(closes)
    decision = sorted(series)[-3]
    row = {"ticker": "T", "label_available": f"{decision}T23:59:59+00:00"}
    before = feature_row(row, series, {})
    mutated = {day: (value * 5.0 if day in sorted(series)[-3:] else value)
               for day, value in series.items()}
    after = feature_row(row, mutated, {})
    for key in before:
        assert same(before[key], after[key]), key
    # a change strictly before the decision must move the features, proving the window is not empty
    earlier = {day: (value * 5.0 if day == sorted(series)[-4] else value)
               for day, value in series.items()}
    moved = feature_row(row, earlier, {})
    assert any(not same(before[key], moved[key]) for key in before)


def test_peer_relative_uses_the_group_median_and_reports_nulls():
    with tempfile.TemporaryDirectory() as tmp:
        cache = Path(tmp)
        closes = [100.0 + index for index in range(80)]
        for ticker in ("AAA", "BBB", "CCC"):
            (cache / f"{ticker}.json").write_text(json.dumps(series_from_closes(closes)))
        rows = [
            {"ticker": "AAA", "label_available": "2020-03-20T23:59:59+00:00", "group_datacenter": 1.0},
            {"ticker": "BBB", "label_available": "2020-03-20T23:59:59+00:00", "group_datacenter": 1.0},
            {"ticker": "CCC", "label_available": "2020-03-20T23:59:59+00:00", "group_datacenter": 0.0,
             "group_utility": 1.0},
            {"ticker": "MISSING", "label_available": "2020-03-20T23:59:59+00:00", "group_datacenter": 1.0},
        ]
        features, coverage = build(rows, cache=cache)
        # AAA and BBB are identical series, so each is exactly at its peer median
        assert abs(features[0]["market_peer_relative_60"]) < 1e-12
        assert abs(features[1]["market_peer_relative_5"]) < 1e-12
        # CCC has no peers, so its relative features are null
        assert math.isnan(features[2]["market_peer_relative_60"])
        # a ticker with no bar file has no absolute features either
        assert math.isnan(features[3]["market_return_60"])
        assert coverage["market_return_60"]["finite"] == 3
        assert coverage["market_peer_relative_60"]["finite"] == 2


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} market-state contract(s) held")
