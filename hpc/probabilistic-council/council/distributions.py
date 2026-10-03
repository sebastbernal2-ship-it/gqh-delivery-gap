"""Versioned probability objects shared by council specialists and fusion."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple


CONTRACT_VERSION = "council-distribution-0.2.0"
ProbabilityVector = Tuple[float, ...]


def validate_distribution(outcomes: Tuple[str, ...], probabilities: Tuple[float, ...],
                          tolerance: float = 1e-9) -> None:
    if len(outcomes) < 2 or len(set(outcomes)) != len(outcomes):
        raise ValueError("outcome labels must be unique and contain at least two values")
    if len(probabilities) != len(outcomes):
        raise ValueError("probability count must match the ordered outcome space")
    if any(not math.isfinite(p) or p < 0.0 or p > 1.0 for p in probabilities):
        raise ValueError("probabilities must be finite values in [0, 1]")
    if abs(sum(probabilities) - 1.0) > tolerance:
        raise ValueError("probabilities must sum to one")


@dataclass(frozen=True)
class SpecialistForecast:
    """A categorical distribution with enough provenance to gate it safely."""

    specialist_id: str
    outcome_space: Tuple[str, ...]
    probabilities: ProbabilityVector
    context: str
    forecast_time: str
    valid_until: str
    information_cutoff: str
    model_version: str
    data_version: str
    epistemic_uncertainty: Optional[float] = None
    abstain: bool = False
    dimensions: Tuple[str, ...] = ()
    outcome_states: Tuple[Tuple[str, ...], ...] = ()

    def __post_init__(self) -> None:
        validate_distribution(self.outcome_space, self.probabilities)
        required = (self.specialist_id, self.context, self.forecast_time,
                    self.valid_until, self.information_cutoff,
                    self.model_version, self.data_version)
        if any(not value for value in required):
            raise ValueError("forecast identity, time, cutoff, and versions are required")
        try:
            forecast_time = datetime.fromisoformat(self.forecast_time)
            valid_until = datetime.fromisoformat(self.valid_until)
            information_cutoff = datetime.fromisoformat(self.information_cutoff)
        except ValueError as error:
            raise ValueError("forecast times must be ISO-8601 timestamps") from error
        if any(value.tzinfo is None or value.utcoffset() is None
               for value in (forecast_time, valid_until, information_cutoff)):
            raise ValueError("forecast timestamps must include a timezone")
        if not information_cutoff <= forecast_time < valid_until:
            raise ValueError("information cutoff <= forecast time < valid_until is required")
        if self.epistemic_uncertainty is not None and (
            not math.isfinite(self.epistemic_uncertainty) or self.epistemic_uncertainty < 0.0
        ):
            raise ValueError("epistemic uncertainty must be finite and nonnegative")
        if bool(self.dimensions) != bool(self.outcome_states):
            raise ValueError("joint distributions need both dimensions and outcome states")
        if self.dimensions:
            if len(set(self.dimensions)) != len(self.dimensions):
                raise ValueError("joint dimension names must be unique")
            if len(self.outcome_states) != len(self.outcome_space):
                raise ValueError("joint state count must match the probability vector")
            if any(len(state) != len(self.dimensions) or any(not value for value in state)
                   for state in self.outcome_states):
                raise ValueError("each joint state must name one value per dimension")
            if len(set(self.outcome_states)) != len(self.outcome_states):
                raise ValueError("joint outcome states must be unique")


def assert_compatible(forecasts: Tuple[SpecialistForecast, ...]) -> None:
    if not forecasts:
        raise ValueError("at least one specialist forecast is required")
    expected = forecasts[0].outcome_space
    expected_joint = (forecasts[0].dimensions, forecasts[0].outcome_states)
    for forecast in forecasts:
        if forecast.outcome_space != expected:
            raise ValueError("specialist outcome spaces and class order must match")
        if (forecast.dimensions, forecast.outcome_states) != expected_joint:
            raise ValueError("specialists must describe identical joint state spaces")


def marginalize(forecast: SpecialistForecast, dimension: str) -> dict:
    """Return one declared marginal without discarding the joint distribution."""
    if dimension not in forecast.dimensions:
        raise ValueError("requested dimension is not declared in this joint forecast")
    index = forecast.dimensions.index(dimension)
    result = {}
    for state, probability in zip(forecast.outcome_states, forecast.probabilities):
        category = state[index]
        result[category] = result.get(category, 0.0) + probability
    return result
