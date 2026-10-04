#!/usr/bin/env python3
"""The decision layer: turn a probability vector into one action, or no action.

The council emits a distribution per case. A decision needs an action and a reason to abstain.
The declared rule is utility maximisation: a correct call pays +reward, a wrong call pays
-reward, and acting costs `cost` on every acted row. Acting is worth it only when

    reward * (2 * p_best - 1) > cost,  that is  p_best > (reward + cost) / (2 * reward)

so the cost sets the confidence gate and rows under the gate abstain. The layer reports the
coverage and the accuracy of what it actually decides, plus the utility against acting blind.

Labels are column indices, never class values: convert with `classes.index(label)` first.
"""
from __future__ import annotations

import numpy as np

DEFAULT_THRESHOLDS = tuple(round(0.20 + 0.05 * step, 2) for step in range(15))
DEFAULT_COSTS = (0.0, 0.05, 0.10, 0.20, 0.40)
DEFAULT_TARGETS = (0.50, 0.60, 0.70, 0.80)


def _matrix(probabilities) -> np.ndarray:
    matrix = np.asarray(probabilities, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] == 0:
        raise ValueError("probabilities must be a nonempty matrix of rows by classes")
    return matrix


def best_probability(probabilities) -> np.ndarray:
    """The top class probability per row, the confidence the gate reads."""
    return _matrix(probabilities).max(axis=1)


def predicted_labels(probabilities) -> np.ndarray:
    """The argmax action per row, as a column index."""
    return _matrix(probabilities).argmax(axis=1)


def threshold_for_cost(cost: float, reward: float = 1.0) -> float:
    """The confidence a row must beat for acting to be worth the declared cost."""
    if reward <= 0:
        raise ValueError("reward must be positive")
    if cost < 0:
        raise ValueError("cost cannot be negative")
    return (reward + cost) / (2 * reward)


def selective_curve(probabilities, labels, thresholds=DEFAULT_THRESHOLDS) -> list[dict]:
    """Coverage and accuracy on acted rows for each confidence gate."""
    matrix = _matrix(probabilities)
    truth = np.asarray(labels, dtype=int)
    if len(truth) != len(matrix):
        raise ValueError("one label per probability row is required")
    best = best_probability(matrix)
    correct = predicted_labels(matrix) == truth
    rows = []
    for threshold in thresholds:
        acted = best >= threshold
        acted_count = int(acted.sum())
        right = int((acted & correct).sum())
        rows.append({
            "threshold": float(threshold),
            "acted": acted_count,
            "coverage": acted_count / len(truth),
            "accuracy_acted": (right / acted_count) if acted_count else None,
            "accuracy_overall": right / len(truth),
        })
    return rows


def utility_curve(probabilities, labels, costs=DEFAULT_COSTS, reward: float = 1.0) -> list[dict]:
    """Realised utility per row under the cost-implied gate, against acting on every row."""
    matrix = _matrix(probabilities)
    truth = np.asarray(labels, dtype=int)
    if len(truth) != len(matrix):
        raise ValueError("one label per probability row is required")
    best = best_probability(matrix)
    correct = predicted_labels(matrix) == truth
    rows = []
    for cost in costs:
        threshold = threshold_for_cost(cost, reward)
        acted = best > threshold
        acted_count = int(acted.sum())
        right = int((acted & correct).sum())
        wrong = acted_count - right
        selective = (reward * right - reward * wrong - cost * acted_count) / len(truth)
        blind = (reward * int(correct.sum()) - reward * int((~correct).sum())
                 - cost * len(truth)) / len(truth)
        rows.append({
            "cost": float(cost),
            "threshold": float(threshold),
            "acted": acted_count,
            "coverage": acted_count / len(truth),
            "accuracy_acted": (right / acted_count) if acted_count else None,
            "utility_per_row": selective,
            "utility_acting_on_every_row": blind,
            "utility_gain_over_blind": selective - blind,
        })
    return rows


def accuracy_at_target(curve: list[dict], target: float) -> dict | None:
    """The highest-coverage gate whose acted accuracy still meets the target."""
    candidates = [row for row in curve
                  if row["acted"] and row["accuracy_acted"] is not None
                  and row["accuracy_acted"] >= target]
    if not candidates:
        return None
    return max(candidates, key=lambda row: (row["coverage"], row["threshold"]))

# The five bins are ordered, from down-large to up-large. A near miss is not a wild miss, so the
# declared ordinal payoff is +1 exact, 0 adjacent, -1 two or more bins away. The symmetric payoff
# above treats every wrong call as -1 and is kept as the conservative reference.
DISTANCE_PAYOFF = tuple(
    tuple(1.0 if abs(i - j) == 0 else 0.0 if abs(i - j) == 1 else -1.0
          for j in range(5))
    for i in range(5)
)
SYMMETRIC_PAYOFF = tuple(
    tuple(1.0 if i == j else -1.0 for j in range(5))
    for i in range(5)
)


def expected_payoff(probabilities, payoff=DISTANCE_PAYOFF) -> np.ndarray:
    """Expected payoff of each action per row, from the distribution and the payoff matrix."""
    matrix = _matrix(probabilities)
    table = np.asarray(payoff, dtype=float)
    if table.shape[0] != matrix.shape[1]:
        raise ValueError("the payoff matrix needs one row per class in the probabilities")
    return matrix @ table.T


def best_action(probabilities, payoff=DISTANCE_PAYOFF) -> tuple[np.ndarray, np.ndarray]:
    """The action with the highest expected payoff and that payoff, per row."""
    expected = expected_payoff(probabilities, payoff)
    return expected.argmax(axis=1), expected.max(axis=1)


def ordinal_utility_curve(probabilities, labels, costs=DEFAULT_COSTS,
                          payoff=DISTANCE_PAYOFF) -> list[dict]:
    """Realised utility under the rule: act only when the best expected payoff beats the cost."""
    matrix = _matrix(probabilities)
    truth = np.asarray(labels, dtype=int)
    if len(truth) != len(matrix):
        raise ValueError("one label per probability row is required")
    table = np.asarray(payoff, dtype=float)
    action, best = best_action(matrix, payoff)
    realised = table[action, truth]
    rows = []
    for cost in costs:
        acted = best > cost
        acted_count = int(acted.sum())
        right = int((acted & (action == truth)).sum())
        utility = float((realised[acted] - cost).sum()) / len(truth)
        blind = float((realised - cost).sum()) / len(truth)
        rows.append({
            "cost": float(cost),
            "acted": acted_count,
            "coverage": acted_count / len(truth),
            "accuracy_acted": (right / acted_count) if acted_count else None,
            "utility_per_row": utility,
            "utility_acting_on_every_row": blind,
            "utility_gain_over_blind": utility - blind,
        })
    return rows
