"""Categorical temperature calibration fitted on a separate calibration partition."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence, Tuple

from .distributions import ProbabilityVector, validate_distribution


DEFAULT_TEMPERATURES = (0.5, 0.65, 0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 2.0, 3.0)
FLOOR = 1e-12


def temperature_scale(probabilities: ProbabilityVector, temperature: float) -> ProbabilityVector:
    if not math.isfinite(temperature) or temperature <= 0.0:
        raise ValueError("temperature must be finite and positive")
    logits = [math.log(max(FLOOR, p)) / temperature for p in probabilities]
    maximum = max(logits)
    weights = [math.exp(value - maximum) for value in logits]
    total = sum(weights)
    result = tuple(value / total for value in weights)
    validate_distribution(tuple(str(i) for i in range(len(result))), result)
    return result


def multiclass_log_loss(rows: Sequence[ProbabilityVector], labels: Sequence[int]) -> float:
    if not rows or len(rows) != len(labels):
        raise ValueError("log-loss requires equally sized, nonempty forecasts and labels")
    if any(label < 0 or label >= len(row) for row, label in zip(rows, labels)):
        raise ValueError("label index is outside the forecast outcome space")
    return sum(-math.log(max(FLOOR, row[label])) for row, label in zip(rows, labels)) / len(rows)


@dataclass(frozen=True)
class TemperatureCalibrator:
    temperature: float
    sample_count: int
    log_loss_before: float
    log_loss_after: float
    method: str = "grid_minimum_multiclass_log_loss"

    def apply(self, probabilities: ProbabilityVector) -> ProbabilityVector:
        return temperature_scale(probabilities, self.temperature)


def fit_temperature(rows: Sequence[ProbabilityVector], labels: Sequence[int],
                    candidates: Tuple[float, ...] = DEFAULT_TEMPERATURES) -> TemperatureCalibrator:
    if not candidates or any(not math.isfinite(value) or value <= 0.0 for value in candidates):
        raise ValueError("temperature candidates must be nonempty and positive")
    before = multiclass_log_loss(rows, labels)
    scored = []
    for temperature in candidates:
        transformed = [temperature_scale(row, temperature) for row in rows]
        scored.append((multiclass_log_loss(transformed, labels), temperature))
    after, selected = min(scored)
    return TemperatureCalibrator(selected, len(rows), before, after)
