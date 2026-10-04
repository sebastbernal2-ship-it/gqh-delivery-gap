#!/usr/bin/env python3
"""Contracts for the decision layer: gate arithmetic, coverage behaviour, utility identity."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hpc" / "probabilistic-council"))
from decision_layer import (DISTANCE_PAYOFF, SYMMETRIC_PAYOFF, accuracy_at_target,  # noqa: E402
                            best_action, expected_payoff, ordinal_utility_curve,
                            best_probability, predicted_labels, selective_curve,
                            threshold_for_cost, utility_curve)

# four rows, three classes: confident-correct, confident-wrong, unsure, confident-correct
PROBABILITIES = [[0.80, 0.10, 0.10],
                 [0.10, 0.70, 0.20],
                 [0.40, 0.35, 0.25],
                 [0.05, 0.05, 0.90]]
LABELS = [0, 0, 2, 2]


def test_gate_arithmetic():
    assert threshold_for_cost(0.0) == 0.5
    assert abs(threshold_for_cost(0.20) - 0.6) < 1e-12
    assert abs(threshold_for_cost(0.10, reward=1.0) - 0.55) < 1e-12
    for bad in (-0.1,):
        try:
            threshold_for_cost(bad)
        except ValueError:
            continue
        raise AssertionError("a negative cost must be refused")


def test_best_probability_and_argmax():
    assert list(best_probability(PROBABILITIES)) == [0.80, 0.70, 0.40, 0.90]
    assert list(predicted_labels(PROBABILITIES)) == [0, 1, 0, 2]


def test_coverage_falls_and_accuracy_on_acted_rows_rises():
    curve = selective_curve(PROBABILITIES, LABELS, (0.30, 0.50, 0.60, 0.75, 0.90))
    coverages = [row["coverage"] for row in curve]
    assert coverages == [1.0, 0.75, 0.75, 0.5, 0.25], coverages
    acted = [row["accuracy_acted"] for row in curve]
    assert acted == sorted(acted), acted
    assert acted[0] == 0.5                        # acts on all four, two right
    assert abs(acted[1] - 2 / 3) < 1e-12          # drops the unsure row
    assert acted[-1] == 1.0                       # only the 0.90 row clears 0.90
    assert curve[-1]["acted"] == 1


def test_utility_identity_and_empty_coverage():
    rows = utility_curve(PROBABILITIES, LABELS, (0.0, 0.20), reward=1.0)
    free = rows[0]
    assert free["threshold"] == 0.5 and free["coverage"] == 0.75
    assert abs(free["utility_per_row"] - 0.25) < 1e-12        # two right, one wrong, no cost
    assert abs(free["utility_acting_on_every_row"] - 0.0) < 1e-12
    costly = rows[1]
    assert abs(costly["utility_per_row"] - 0.1) < 1e-12       # two right, one wrong, 0.2 each
    assert costly["utility_acting_on_every_row"] < 0
    empty = selective_curve(PROBABILITIES, LABELS, (0.99,))
    assert empty[0]["acted"] == 0 and empty[0]["accuracy_acted"] is None


def test_accuracy_at_target_picks_highest_coverage():
    curve = selective_curve(PROBABILITIES, LABELS, (0.20, 0.45, 0.55, 0.85))
    best = accuracy_at_target(curve, 0.75)
    assert best is not None and best["acted"] == 1 and best["accuracy_acted"] == 1.0
    wrong = selective_curve([[0.6, 0.4]], [1], (0.2,))
    assert accuracy_at_target(wrong, 0.5) is None


def test_ordinal_payoff_prefers_the_neighbouring_bin():
    # mass on bin 1 but almost as much on bin 2: the ordinal rule picks the neighbour, not a far bin
    row = [[0.02, 0.52, 0.44, 0.01, 0.01]]
    action, best = best_action(row, DISTANCE_PAYOFF)
    assert list(action) == [1]
    # bin 1 pays 1 x 0.52, its neighbours pay 0, the two far bins pay -1 x 0.02
    assert abs(best[0] - 0.50) < 1e-12
    # the symmetric payoff charges every wrong call the full -1
    symmetric = expected_payoff(row, SYMMETRIC_PAYOFF)[0]
    assert abs(symmetric[1] - 0.04) < 1e-12


def test_ordinal_utility_identity_and_gate():
    probabilities = [[0.02, 0.52, 0.44, 0.01, 0.01],   # true bin 2: a near miss on bin 1
                     [0.60, 0.10, 0.10, 0.10, 0.10],   # true bin 1: a wild miss on bin 0
                     [0.20, 0.20, 0.20, 0.20, 0.20]]   # no information
    labels = [2, 1, 3]
    rows = ordinal_utility_curve(probabilities, labels, (0.0, 0.4), DISTANCE_PAYOFF)
    # at zero cost the two rows with a nonnegative best expected payoff act; the uniform row does not
    assert abs(rows[0]["coverage"] - 2 / 3) < 1e-12
    # row 1 is a near miss (0.0) and row 2 is adjacent (0.0), so the acted rows break even
    assert abs(rows[0]["utility_per_row"] - 0.0) < 1e-12
    assert rows[0]["utility_acting_on_every_row"] < 0
    assert rows[1]["acted"] == 1                       # the 0.50-expected row is the only one above 0.4
    assert abs(rows[1]["utility_per_row"] - (-0.4 / 3)) < 1e-12
    assert rows[1]["utility_gain_over_blind"] > 0


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} decision layer contract(s) held")
