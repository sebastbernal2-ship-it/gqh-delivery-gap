"""Versioned probability objects shared by council specialists and fusion."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple


CONTRACT_VERSION = "council-distribution-0.3.0"
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


def _validate_identity(specialist_id: str, context: str, forecast_time: str, valid_until: str,
                       information_cutoff: str, model_version: str, data_version: str,
                       epistemic_uncertainty: Optional[float]) -> None:
    """Identity, clock and version checks shared by every forecast representation."""
    required = (specialist_id, context, forecast_time, valid_until, information_cutoff,
                model_version, data_version)
    if any(not value for value in required):
        raise ValueError("forecast identity, time, cutoff, and versions are required")
    try:
        forecast = datetime.fromisoformat(forecast_time)
        valid = datetime.fromisoformat(valid_until)
        cutoff = datetime.fromisoformat(information_cutoff)
    except ValueError as error:
        raise ValueError("forecast times must be ISO-8601 timestamps") from error
    if any(value.tzinfo is None or value.utcoffset() is None for value in (forecast, valid, cutoff)):
        raise ValueError("forecast timestamps must include a timezone")
    if not cutoff <= forecast < valid:
        raise ValueError("information cutoff <= forecast time < valid_until is required")
    if epistemic_uncertainty is not None and (
            not math.isfinite(epistemic_uncertainty) or epistemic_uncertainty < 0.0):
        raise ValueError("epistemic uncertainty must be finite and nonnegative")


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
        _validate_identity(self.specialist_id, self.context, self.forecast_time,
                           self.valid_until, self.information_cutoff, self.model_version,
                           self.data_version, self.epistemic_uncertainty)
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


@dataclass(frozen=True)
class QuantileForecast:
    """A marginal quantile function with the same provenance as a categorical forecast.

    This is the other half of the one specialist contract. The continuous execution-risk track
    emits quantiles, the council fits categorical distributions, and the conversion between the
    two representations is explicit and approximate rather than hidden in an adapter.
    """

    specialist_id: str
    levels: Tuple[float, ...]
    values: Tuple[float, ...]
    unit: str
    context: str
    forecast_time: str
    valid_until: str
    information_cutoff: str
    model_version: str
    data_version: str
    epistemic_uncertainty: Optional[float] = None
    abstain: bool = False

    def __post_init__(self) -> None:
        _validate_identity(self.specialist_id, self.context, self.forecast_time,
                           self.valid_until, self.information_cutoff, self.model_version,
                           self.data_version, self.epistemic_uncertainty)
        if not self.unit:
            raise ValueError("quantile forecasts need a unit")
        validate_quantiles(self.levels, self.values)


def validate_quantiles(levels: Sequence[float], values: Sequence[float]) -> None:
    """A quantile function needs increasing levels in (0, 1) and nondecreasing values."""
    if len(levels) != len(values) or len(levels) < 2:
        raise ValueError("at least two levels are required, one value each")
    if any(not math.isfinite(level) or level <= 0.0 or level >= 1.0 for level in levels):
        raise ValueError("levels must be finite and strictly inside (0, 1)")
    if any(levels[index] >= levels[index + 1] for index in range(len(levels) - 1)):
        raise ValueError("levels must be strictly increasing")
    if any(not math.isfinite(value) for value in values):
        raise ValueError("quantile values must be finite")
    if any(values[index] > values[index + 1] for index in range(len(values) - 1)):
        raise ValueError("quantile values must be nondecreasing")


def _level_at_value(levels: Sequence[float], values: Sequence[float], value: float) -> float:
    """Level whose quantile function equals the value.

    Inside the known levels the function is piecewise linear. Beyond the outermost levels the
    outermost segment is extended linearly until the level reaches zero or one, so tail mass is
    spread over the outer bins instead of being concentrated at the outermost quantile.
    """
    if value <= values[0]:
        slope = (levels[1] - levels[0]) / (values[1] - values[0]) if values[1] > values[0] else 0.0
        return max(0.0, levels[0] + (value - values[0]) * slope)
    if value >= values[-1]:
        slope = ((levels[-1] - levels[-2]) / (values[-1] - values[-2])
                 if values[-1] > values[-2] else 0.0)
        return min(1.0, levels[-1] + (value - values[-1]) * slope)
    for index in range(len(values) - 1):
        low, high = values[index], values[index + 1]
        if low <= value <= high:
            if high == low:
                return levels[index]
            return levels[index] + (value - low) / (high - low) * (levels[index + 1] - levels[index])
    return 1.0


def _check_edges(edges: Sequence[float]) -> Tuple[float, ...]:
    edges = tuple(edges)
    if len(edges) < 1 or any(not math.isfinite(edge) for edge in edges):
        raise ValueError("at least one finite edge is required")
    if any(edges[index] >= edges[index + 1] for index in range(len(edges) - 1)):
        raise ValueError("edges must be strictly increasing")
    return edges


def quantiles_to_probabilities(levels: Sequence[float], values: Sequence[float],
                               edges: Sequence[float]) -> Tuple[float, ...]:
    """Mass of each bin [-inf, e0), [e0, e1), ..., [e_last, +inf).

    Exact under the declared piecewise-linear quantile function with its linear tail extension.
    The two open outer bins receive the mass beyond the outermost known quantiles.
    """
    validate_quantiles(levels, values)
    edges = _check_edges(edges)
    boundaries = [0.0] + [_level_at_value(levels, values, edge) for edge in edges] + [1.0]
    masses = [max(0.0, high - low) for low, high in zip(boundaries, boundaries[1:])]
    total = sum(masses)
    if total <= 0.0:
        raise ValueError("conversion produced no mass")
    return tuple(mass / total for mass in masses)


def probabilities_to_quantiles(probabilities: Sequence[float], edges: Sequence[float],
                               levels: Sequence[float]) -> Tuple[float, ...]:
    """Approximate quantiles of a binned distribution.

    Mass is uniform within a finite bin. The two open outer bins are handled by extending the
    outermost quantile segment linearly until the level reaches zero or one. That tail shape is an
    assumption, not data, and the round trip error is measured in the representation tests.
    """
    probabilities = tuple(probabilities)
    edges = _check_edges(edges)
    if len(probabilities) != len(edges) + 1:
        raise ValueError("one probability per bin: len(edges) + 1")
    if any(not math.isfinite(mass) or mass < 0.0 for mass in probabilities):
        raise ValueError("probabilities must be finite and nonnegative")
    if abs(sum(probabilities) - 1.0) > 1e-9:
        raise ValueError("probabilities must sum to one")
    if any(not math.isfinite(level) or level <= 0.0 or level >= 1.0 for level in levels):
        raise ValueError("levels must be finite and strictly inside (0, 1)")
    if any(levels[index] >= levels[index + 1] for index in range(len(levels) - 1)):
        raise ValueError("levels must be strictly increasing")
    cumulative = []
    running = 0.0
    for mass in probabilities:
        running += mass
        cumulative.append(running)
    result = []
    for level in levels:
        index = next(position for position, bound in enumerate(cumulative) if level <= bound)
        below = cumulative[index - 1] if index > 0 else 0.0
        mass = probabilities[index]
        if index == 0:
            result.append(edges[0])
        elif index == len(probabilities) - 1:
            result.append(edges[-1])
        elif mass <= 0.0:
            result.append(edges[index - 1])
        else:
            low, high = edges[index - 1], edges[index]
            result.append(low + (level - below) / mass * (high - low))
    return tuple(result)


def bin_labels(edges: Sequence[float]) -> Tuple[str, ...]:
    """Labels for the bins a quantile conversion produces."""
    edges = _check_edges(edges)
    labels = [f"<{edges[0]:g}"]
    labels.extend(f"[{low:g},{high:g})" for low, high in zip(edges, edges[1:]))
    labels.append(f">={edges[-1]:g}")
    return tuple(labels)


def to_categorical(forecast: QuantileForecast, edges: Sequence[float],
                   outcomes: Optional[Sequence[str]] = None) -> SpecialistForecast:
    """Convert a quantile forecast into the categorical contract the council fits."""
    edges = _check_edges(edges)
    probabilities = quantiles_to_probabilities(forecast.levels, forecast.values, edges)
    return SpecialistForecast(
        specialist_id=forecast.specialist_id,
        outcome_space=tuple(outcomes) if outcomes is not None else bin_labels(edges),
        probabilities=probabilities,
        context=forecast.context,
        forecast_time=forecast.forecast_time,
        valid_until=forecast.valid_until,
        information_cutoff=forecast.information_cutoff,
        model_version=forecast.model_version,
        data_version=forecast.data_version,
        epistemic_uncertainty=forecast.epistemic_uncertainty,
        abstain=forecast.abstain,
    )


def from_categorical(forecast: SpecialistForecast, edges: Sequence[float],
                     levels: Sequence[float], unit: str) -> QuantileForecast:
    """Approximate quantiles of a categorical forecast, for quantile-scale scoring."""
    return QuantileForecast(
        specialist_id=forecast.specialist_id,
        levels=tuple(levels),
        values=probabilities_to_quantiles(forecast.probabilities, edges, levels),
        unit=unit,
        context=forecast.context,
        forecast_time=forecast.forecast_time,
        valid_until=forecast.valid_until,
        information_cutoff=forecast.information_cutoff,
        model_version=forecast.model_version,
        data_version=forecast.data_version,
        epistemic_uncertainty=forecast.epistemic_uncertainty,
        abstain=forecast.abstain,
    )
