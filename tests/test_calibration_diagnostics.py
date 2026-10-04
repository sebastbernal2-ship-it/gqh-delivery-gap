#!/usr/bin/env python3
"""Contracts for the diagnostics: a calibrated set scores near zero, an overconfident set does not."""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.calibration_diagnostics import (bootstrap_ece, expected_calibration_error,  # noqa: E402
                                                       extreme_bin_check, maximum_calibration_error,
                                                       reliability, tail_statistics)


def test_a_perfectly_calibrated_set_has_near_zero_error():
    confidences, correct = [], []
    for confidence, share in ((0.1, 0.1), (0.3, 0.3), (0.5, 0.5), (0.9, 0.9)):
        count = 100
        confidences += [confidence] * count
        correct += [1] * int(share * count) + [0] * (count - int(share * count))
    rows = reliability(confidences, correct, bins=10)
    assert expected_calibration_error(rows) < 0.01
    assert maximum_calibration_error(rows) < 0.01


def test_overconfidence_shows_up_as_a_negative_gap():
    confidences = [0.9] * 100
    correct = [1] * 60 + [0] * 40
    rows = reliability(confidences, correct, bins=10)
    assert expected_calibration_error(rows) > 0.25
    assert rows[0]["gap"] < -0.25                    # predicted far above what happened


def test_the_bootstrap_interval_is_seeded_and_contains_the_point():
    confidences = [0.6] * 40 + [0.9] * 40
    correct = [1] * 24 + [0] * 16 + [1] * 36 + [0] * 4
    first = bootstrap_ece(confidences, correct, resamples=200, seed=5)
    second = bootstrap_ece(confidences, correct, resamples=200, seed=5)
    assert first == second                                  # seeded and reproducible
    assert first["lower"] <= first["upper"]                 # ordered, but not a containment claim
    assert first["rows"] == 80 and first["point"] >= 0


def test_tail_statistics_on_a_known_series():
    series = [0.01, -0.02, 0.03, -0.10, 0.02, 0.01, -0.05, 0.04, 0.00, 0.01]
    stats = tail_statistics(series, window=3)
    assert stats["worst_day"] == -0.10
    assert stats["cvar_1pct"] <= stats["var_5pct"] <= 0
    worst = stats["worst_window"]
    compounded = 1.0
    for value in series[worst["start"]:worst["start"] + worst["length"]]:
        compounded *= 1 + value
    assert abs(worst["return"] - (compounded - 1)) < 1e-12


def test_extreme_bins_compare_prediction_with_frequency():
    probabilities = [[0.8, 0.1, 0.1], [0.8, 0.1, 0.1], [0.1, 0.1, 0.8], [0.1, 0.1, 0.8]]
    check = extreme_bin_check(probabilities, [2, 2, 2, 2], (0, 1, 2))
    # the lowest class is assigned 0.8 twice and 0.1 twice, so 0.45 on average, and never happens
    assert abs(check["lowest"]["mean_predicted"] - 0.45) < 1e-12
    assert check["lowest"]["realised"] == 0.0 and abs(check["lowest"]["gap"] + 0.45) < 1e-12
    assert abs(check["highest"]["mean_predicted"] - 0.45) < 1e-12
    assert abs(check["highest"]["gap"] - 0.55) < 1e-12


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} calibration contract(s) held")
