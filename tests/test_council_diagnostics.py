#!/usr/bin/env python3
"""Contracts for the council diagnostics: distances, correlation, bootstrap, leave-one-out score."""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hpc" / "probabilistic-council"))
sys.path.insert(0, str(ROOT / "src"))
from panel_council import blocked_bootstrap, row_log_loss, top_probability_correlation  # noqa: E402
from panel_council import total_variation  # noqa: E402


def test_total_variation_bounds():
    assert total_variation([[1.0, 0.0]], [[1.0, 0.0]]) == 0.0
    assert total_variation([[1.0, 0.0]], [[0.0, 1.0]]) == 1.0
    assert abs(total_variation([[0.75, 0.25]], [[0.25, 0.75]]) - 0.5) < 1e-12


def test_correlation_and_flat_rows():
    left = [[0.9, 0.1], [0.6, 0.4], [0.7, 0.3]]
    right = [[0.8, 0.2], [0.5, 0.5], [0.65, 0.35]]
    # the confidences move together, so the correlation is high but not exactly one
    assert abs(top_probability_correlation(left, right) - 0.982) < 0.01
    assert top_probability_correlation(left, right) > 0.9
    assert top_probability_correlation([[0.5, 0.5]], [[0.5, 0.5]]) == 0.0


def test_row_log_loss_matches_the_picked_probability():
    losses = row_log_loss([[0.5, 0.5], [0.99, 0.01], [0.01, 0.99]], [0, 0, 1])
    assert abs(losses[0] - math.log(2)) < 1e-12
    assert abs(losses[1] - (-math.log(0.99))) < 1e-12
    assert abs(losses[2] - (-math.log(0.99))) < 1e-12
    # an impossible call is heavily but finitely penalised, so an interval stays computable
    huge = row_log_loss([[0.0, 1.0]], [0])[0]
    assert math.isfinite(huge) and huge > 30.0


def test_blocked_bootstrap_resamples_issuers_and_is_seeded():
    difference = [0.5, 0.4, -0.2, 0.3, 0.1, -0.1]
    groups = ["A", "A", "B", "B", "C", "C"]
    first = blocked_bootstrap(difference, groups, resamples=200, seed=7)
    second = blocked_bootstrap(difference, groups, resamples=200, seed=7)
    assert first == second
    assert first["issuers"] == 3 and first["resamples"] == 200
    assert first["lower"] <= first["point"] <= first["upper"]
    assert 0.0 <= first["share_favouring_the_first"] <= 1.0
    # with one issuer per block the interval stays at the block means, so a single issuer cannot
    # manufacture significance
    blocky = blocked_bootstrap([0.2, 0.2, -0.2, -0.2], ["A", "A", "B", "B"], resamples=200, seed=3)
    assert blocky["lower"] >= -0.2 - 1e-12 and blocky["upper"] <= 0.2 + 1e-12


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} council diagnostic contract(s) held")
