"""Opinion-pool baselines that preserve a shared joint outcome space."""

from __future__ import annotations

import math
from typing import Mapping, Tuple

from .distributions import ProbabilityVector, validate_distribution


FLOOR = 1e-12


def _normalized_weights(probabilities: Mapping[str, ProbabilityVector],
                        weights: Mapping[str, float]) -> Tuple[Tuple[str, float], ...]:
    if not probabilities:
        raise ValueError("at least one active specialist is required")
    if set(probabilities) - set(weights):
        raise ValueError("each active specialist needs a fitted gate weight")
    names = tuple(probabilities)
    raw = [weights[name] for name in names]
    if any(not math.isfinite(value) or value < 0.0 for value in raw):
        raise ValueError("fusion weights must be finite and nonnegative")
    total = sum(raw)
    if total <= 0.0:
        raise ValueError("active fusion weights must have positive mass")
    return tuple((name, weights[name] / total) for name in names)


def linear_opinion_pool(probabilities: Mapping[str, ProbabilityVector],
                        weights: Mapping[str, float]) -> ProbabilityVector:
    """Weighted mixture; does not assume specialists are independent."""
    active_weights = _normalized_weights(probabilities, weights)
    dimensions = {len(probabilities[name]) for name, _ in active_weights}
    if len(dimensions) != 1:
        raise ValueError("all specialist distributions must have the same outcome count")
    size = next(iter(dimensions))
    result = tuple(
        sum(weight * probabilities[name][index] for name, weight in active_weights)
        for index in range(size)
    )
    validate_distribution(tuple(str(i) for i in range(size)), result)
    return result


def logarithmic_opinion_pool(probabilities: Mapping[str, ProbabilityVector],
                             weights: Mapping[str, float]) -> ProbabilityVector:
    """Normalized geometric pool (a benchmark, not an independence claim)."""
    active_weights = _normalized_weights(probabilities, weights)
    dimensions = {len(probabilities[name]) for name, _ in active_weights}
    if len(dimensions) != 1:
        raise ValueError("all specialist distributions must have the same outcome count")
    size = next(iter(dimensions))
    logits = [
        sum(weight * math.log(max(FLOOR, probabilities[name][index]))
            for name, weight in active_weights)
        for index in range(size)
    ]
    maximum = max(logits)
    values = [math.exp(value - maximum) for value in logits]
    total = sum(values)
    result = tuple(value / total for value in values)
    validate_distribution(tuple(str(i) for i in range(size)), result)
    return result


def disagreement(probabilities: Mapping[str, ProbabilityVector],
                 weights: Mapping[str, float],
                 pooled: ProbabilityVector) -> float:
    """Weighted squared deviation; a diagnostic proxy for between-model uncertainty."""
    active_weights = _normalized_weights(probabilities, weights)
    return sum(
        weight * sum((left - right) ** 2
                     for left, right in zip(probabilities[name], pooled))
        for name, weight in active_weights
    )
