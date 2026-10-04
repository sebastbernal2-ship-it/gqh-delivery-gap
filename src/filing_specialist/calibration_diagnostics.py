#!/usr/bin/env python3
"""Calibration and tail diagnostics: are the probabilities honest, and how bad are the tails?

The architecture document requires reliability and calibration diagnostics beside proper scores, and
the sleeve drawdowns make the return tails worth stating. Everything here is descriptive: a bin table,
an expected calibration error, a maximum calibration error, a small-sample interval, and the tail
statistics of a daily net series.
"""
from __future__ import annotations

import math
import random
import statistics


def reliability(confidences: list[float], correct: list[int], bins: int = 10) -> list[dict]:
    """Confidence bins with their observed frequency, the standard reliability table."""
    if len(confidences) != len(correct):
        raise ValueError("one correctness flag per confidence is required")
    edges = [index / bins for index in range(bins + 1)]
    rows = []
    for index in range(bins):
        lower, upper = edges[index], edges[index + 1]
        chosen = [position for position, value in enumerate(confidences)
                  if (lower <= value < upper) or (index == bins - 1 and value == upper)]
        if not chosen:
            continue
        mean_confidence = statistics.mean(confidences[position] for position in chosen)
        accuracy = statistics.mean(correct[position] for position in chosen)
        rows.append({"lower": lower, "upper": upper, "n": len(chosen),
                     "mean_confidence": mean_confidence, "accuracy": accuracy,
                     "gap": accuracy - mean_confidence})
    return rows


def expected_calibration_error(rows: list[dict]) -> float:
    total = sum(row["n"] for row in rows)
    if not total:
        return 0.0
    return sum(row["n"] * abs(row["gap"]) for row in rows) / total


def maximum_calibration_error(rows: list[dict]) -> float:
    return max((abs(row["gap"]) for row in rows), default=0.0)


def bootstrap_ece(confidences: list[float], correct: list[int], resamples: int = 1000,
                  seed: int = 20261004, bins: int = 10) -> dict:
    """Percentile interval over resampled rows.

    A percentile interval does not guarantee that the point estimate lies inside it, so callers must
    report both and never assume containment.
    """
    if len(confidences) != len(correct) or not confidences:
        raise ValueError("one correctness flag per confidence is required")
    rng = random.Random(seed)
    draws = []
    size = len(confidences)
    for _ in range(resamples):
        picks = [rng.randrange(size) for _ in range(size)]
        draws.append(expected_calibration_error(
            reliability([confidences[p] for p in picks], [correct[p] for p in picks], bins)))
    draws.sort()
    return {"point": expected_calibration_error(reliability(confidences, correct, bins)),
            "lower": draws[int(0.025 * len(draws))], "upper": draws[int(0.975 * len(draws)) - 1],
            "resamples": resamples, "rows": size}


def tail_statistics(series: list[float], window: int = 20) -> dict:
    """Value at risk, expected shortfall, the worst day and the worst rolling window."""
    if not series:
        return {"days": 0}
    ordered = sorted(series)
    count = len(ordered)

    def quantile(fraction: float) -> float:
        index = max(0, min(count - 1, int(fraction * count)))
        return ordered[index]

    worst_window, worst_start = 0.0, 0
    for start in range(max(1, count - window + 1)):
        compounded = 1.0
        for value in series[start:start + window]:
            compounded *= 1 + value
        if compounded - 1 < worst_window:
            worst_window, worst_start = compounded - 1, start
    mean = statistics.mean(series)
    deviation = statistics.pstdev(series) if count > 1 else 0.0
    return {"days": count, "mean": mean, "vol": deviation,
            "var_5pct": quantile(0.05), "cvar_5pct": statistics.mean(
                ordered[:max(1, int(0.05 * count))]),
            "var_1pct": quantile(0.01), "cvar_1pct": statistics.mean(
                ordered[:max(1, int(0.01 * count))]),
            "worst_day": ordered[0],
            "worst_window": {"length": window, "return": worst_window, "start": worst_start},
            "skew": (statistics.mean((value - mean) ** 3 for value in series)
                     / deviation ** 3) if deviation else 0.0}


def extreme_bin_check(probabilities: list[list[float]], labels: list[int],
                      classes: tuple[int, ...]) -> dict:
    """For the extreme classes: mean predicted probability against the realised frequency."""
    out = {}
    for name, position in (("lowest", 0), ("highest", len(classes) - 1)):
        predicted = statistics.mean(row[position] for row in probabilities)
        realised = statistics.mean(1 if label == classes[position] else 0 for label in labels)
        out[name] = {"class": classes[position], "rows": len(labels),
                     "mean_predicted": predicted, "realised": realised,
                     "gap": realised - predicted}
    return out
