"""Reliability gate fitted only on its designated labelled partition."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Sequence, Tuple

from .distributions import ProbabilityVector


FLOOR = 1e-9


def multiclass_brier(probabilities: ProbabilityVector, label: int) -> float:
    if label < 0 or label >= len(probabilities):
        raise ValueError("label index is outside the forecast outcome space")
    return sum((p - (1.0 if i == label else 0.0)) ** 2
               for i, p in enumerate(probabilities))


@dataclass(frozen=True)
class ReliabilityGate:
    global_weights: Mapping[str, float]
    context_weights: Mapping[str, Mapping[str, float]]
    sample_counts: Mapping[str, int]
    minimum_context_rows: int

    def weights_for(self, context: str, active_specialists: Sequence[str]) -> Dict[str, float]:
        source = self.context_weights.get(context, self.global_weights)
        if set(active_specialists) - set(source):
            raise ValueError("gate has no trained weight for an active specialist")
        values = {name: source[name] for name in active_specialists}
        total = sum(values.values())
        if total <= 0.0:
            raise ValueError("active specialists have no reliability weight")
        return {name: value / total for name, value in values.items()}


def _fit_group(labels: Sequence[int], forecasts: Mapping[str, Sequence[ProbabilityVector]],
               minimum_weight: float) -> Dict[str, float]:
    errors = {}
    for name, rows in forecasts.items():
        if len(rows) != len(labels) or not rows:
            raise ValueError("each specialist needs a forecast for every gate-fit case")
        errors[name] = sum(multiclass_brier(row, label)
                           for row, label in zip(rows, labels)) / len(labels)
    inverse = {name: 1.0 / max(FLOOR, error) for name, error in errors.items()}
    total = sum(inverse.values())
    normalized = {name: value / total for name, value in inverse.items()}
    count = len(normalized)
    if minimum_weight < 0.0 or minimum_weight * count >= 1.0:
        raise ValueError("minimum gate weight must be nonnegative and below 1/N")
    return {name: minimum_weight + (1.0 - count * minimum_weight) * value
            for name, value in normalized.items()}


def fit_reliability_gate(contexts: Sequence[str], labels: Sequence[int],
                         forecasts: Mapping[str, Sequence[ProbabilityVector]],
                         minimum_context_rows: int = 40,
                         minimum_weight: float = 0.02) -> ReliabilityGate:
    if not contexts or len(contexts) != len(labels):
        raise ValueError("gate fitting needs equally sized, nonempty contexts and labels")
    if any(not context for context in contexts):
        raise ValueError("gate contexts must be nonempty identifiers")
    global_weights = _fit_group(labels, forecasts, minimum_weight)
    context_weights = {}
    sample_counts = {}
    for context in sorted(set(contexts)):
        indexes = [i for i, value in enumerate(contexts) if value == context]
        sample_counts[context] = len(indexes)
        if len(indexes) < minimum_context_rows:
            continue
        context_forecasts = {
            name: [rows[i] for i in indexes] for name, rows in forecasts.items()
        }
        context_labels = [labels[i] for i in indexes]
        context_weights[context] = _fit_group(context_labels, context_forecasts, minimum_weight)
    sample_counts["__global__"] = len(labels)
    return ReliabilityGate(global_weights, context_weights, sample_counts,
                           minimum_context_rows)
