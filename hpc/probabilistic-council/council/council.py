"""Trainable specialist calibration, context gate, fusion, and final calibration."""

from __future__ import annotations

import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, Mapping, Optional, Sequence, Tuple

from .calibration import TemperatureCalibrator, fit_temperature
from .distributions import SpecialistForecast, assert_compatible
from .fusion import disagreement, linear_opinion_pool, logarithmic_opinion_pool
from .gating import ReliabilityGate, fit_reliability_gate


@dataclass(frozen=True)
class LabeledCase:
    context: str
    label: int
    forecasts: Tuple[SpecialistForecast, ...]
    case_id: str

    def __post_init__(self) -> None:
        if not self.context or not self.forecasts or not self.case_id:
            raise ValueError("labeled cases need an id, context, and specialist forecasts")
        assert_compatible(self.forecasts)
        if self.label < 0 or self.label >= len(self.forecasts[0].outcome_space):
            raise ValueError("label index is outside the outcome space")
        names = [forecast.specialist_id for forecast in self.forecasts]
        if len(names) != len(set(names)):
            raise ValueError("a case cannot contain duplicate specialist ids")
        if any(forecast.context != self.context for forecast in self.forecasts):
            raise ValueError("case and specialist contexts must match")
        if len({forecast.forecast_time for forecast in self.forecasts}) != 1:
            raise ValueError("all specialists in a case must target the same forecast time")


@dataclass(frozen=True)
class CouncilPrediction:
    outcome_space: Tuple[str, ...]
    probabilities: Tuple[float, ...]
    forecast_time: str
    active_specialists: Tuple[str, ...]
    abstained_specialists: Tuple[str, ...]
    gate_weights: Mapping[str, float]
    predictive_entropy: float
    between_model_disagreement: float
    weighted_input_epistemic_uncertainty: Optional[float]
    fusion_method: str
    dimensions: Tuple[str, ...]
    outcome_states: Tuple[Tuple[str, ...], ...]


def _by_specialist(cases: Sequence[LabeledCase]) -> Dict[str, list]:
    collected: Dict[str, list] = {}
    for case in cases:
        for forecast in case.forecasts:
            if forecast.abstain:
                continue
            collected.setdefault(forecast.specialist_id, []).append(
                (case.context, case.label, forecast.probabilities)
            )
    return collected


def _fit_calibration_bank(cases: Sequence[LabeledCase],
                          minimum_context_rows: int) -> Tuple[
                              Dict[str, TemperatureCalibrator],
                              Dict[Tuple[str, str], TemperatureCalibrator]]:
    collected = _by_specialist(cases)
    global_calibrators = {}
    context_calibrators = {}
    for specialist, rows in collected.items():
        global_calibrators[specialist] = fit_temperature(
            [row[2] for row in rows], [row[1] for row in rows]
        )
        contexts = sorted(set(row[0] for row in rows))
        for context in contexts:
            subset = [row for row in rows if row[0] == context]
            if len(subset) >= minimum_context_rows:
                context_calibrators[(specialist, context)] = fit_temperature(
                    [row[2] for row in subset], [row[1] for row in subset]
                )
    if not global_calibrators:
        raise ValueError("calibration partition contains no active specialist forecasts")
    return global_calibrators, context_calibrators


class CouncilModel:
    """A fitted council. Each fit partition has a single, separate role."""

    def __init__(self, outcome_space: Tuple[str, ...],
                 specialist_calibrators: Mapping[str, TemperatureCalibrator],
                 context_calibrators: Mapping[Tuple[str, str], TemperatureCalibrator],
                 gate: ReliabilityGate,
                 pool_calibrator: TemperatureCalibrator,
                 context_pool_calibrators: Mapping[str, TemperatureCalibrator],
                 fusion_method: str, fit_through: str):
        if fusion_method not in ("linear", "logarithmic"):
            raise ValueError("fusion_method must be linear or logarithmic")
        self.outcome_space = outcome_space
        self.specialist_calibrators = dict(specialist_calibrators)
        self.context_calibrators = dict(context_calibrators)
        self.gate = gate
        self.pool_calibrator = pool_calibrator
        self.context_pool_calibrators = dict(context_pool_calibrators)
        self.fusion_method = fusion_method
        self.fit_through = fit_through
        self.specialists = tuple(sorted(self.specialist_calibrators))

    @classmethod
    def fit(cls, calibration_cases: Sequence[LabeledCase],
            gate_cases: Sequence[LabeledCase],
            pool_calibration_cases: Sequence[LabeledCase],
            fusion_method: str = "linear",
            minimum_context_rows: int = 40) -> "CouncilModel":
        """Fit components on distinct partitions; evaluation data never enters this method."""
        partitions = (calibration_cases, gate_cases, pool_calibration_cases)
        if any(not cases for cases in partitions):
            raise ValueError("specialist calibration, gate fit, and pool calibration are required")
        case_id_sets = [set(case.case_id for case in cases) for cases in partitions]
        if any(len(case_ids) != len(cases)
               for case_ids, cases in zip(case_id_sets, partitions)):
            raise ValueError("case ids must be unique within each fit partition")
        if any(case_id_sets[i] & case_id_sets[j]
               for i in range(len(case_id_sets)) for j in range(i + 1, len(case_id_sets))):
            raise ValueError("fit partitions must not share case ids")

        def case_time(case: LabeledCase) -> datetime:
            return datetime.fromisoformat(case.forecasts[0].forecast_time)

        calibration_end = max(case_time(case) for case in calibration_cases)
        gate_start = min(case_time(case) for case in gate_cases)
        gate_end = max(case_time(case) for case in gate_cases)
        pool_start = min(case_time(case) for case in pool_calibration_cases)
        if not calibration_end < gate_start or not gate_end < pool_start:
            raise ValueError("calibration, gate, and pool-calibration partitions must be chronological")
        outcome_space = calibration_cases[0].forecasts[0].outcome_space
        joint_space = (calibration_cases[0].forecasts[0].dimensions,
                       calibration_cases[0].forecasts[0].outcome_states)
        for cases in partitions:
            for case in cases:
                if case.forecasts[0].outcome_space != outcome_space:
                    raise ValueError("all council partitions must share one ordered outcome space")
                if (case.forecasts[0].dimensions,
                        case.forecasts[0].outcome_states) != joint_space:
                    raise ValueError("all council partitions must share one joint state schema")

        specialist_calibrators, context_calibrators = _fit_calibration_bank(
            calibration_cases, minimum_context_rows
        )
        specialist_ids = set(specialist_calibrators)

        def calibrated_case(case: LabeledCase) -> Dict[str, Tuple[float, ...]]:
            result = {}
            for forecast in case.forecasts:
                if forecast.specialist_id not in specialist_ids or forecast.abstain:
                    continue
                calibrator = context_calibrators.get(
                    (forecast.specialist_id, case.context),
                    specialist_calibrators[forecast.specialist_id],
                )
                result[forecast.specialist_id] = calibrator.apply(forecast.probabilities)
            return result

        gate_contexts = []
        gate_labels = []
        gate_forecasts = {name: [] for name in specialist_ids}
        for case in gate_cases:
            rows = calibrated_case(case)
            if set(rows) != specialist_ids:
                raise ValueError("gate-fit rows must cover every calibrated specialist")
            gate_contexts.append(case.context)
            gate_labels.append(case.label)
            for name in specialist_ids:
                gate_forecasts[name].append(rows[name])
        gate = fit_reliability_gate(
            gate_contexts, gate_labels, gate_forecasts,
            minimum_context_rows=minimum_context_rows,
        )

        def raw_pool(case: LabeledCase) -> Tuple[float, ...]:
            rows = calibrated_case(case)
            if not rows:
                raise ValueError("pool calibration case has no active specialist")
            weights = gate.weights_for(case.context, tuple(rows))
            return cls._fuse(rows, weights, fusion_method)

        pool_rows = [raw_pool(case) for case in pool_calibration_cases]
        pool_labels = [case.label for case in pool_calibration_cases]
        pool_calibrator = fit_temperature(pool_rows, pool_labels)
        context_pool_calibrators = {}
        for context in sorted(set(case.context for case in pool_calibration_cases)):
            indexes = [i for i, case in enumerate(pool_calibration_cases)
                       if case.context == context]
            if len(indexes) >= minimum_context_rows:
                context_pool_calibrators[context] = fit_temperature(
                    [pool_rows[i] for i in indexes], [pool_labels[i] for i in indexes]
                )
        fit_through = max(case_time(case) for case in pool_calibration_cases).isoformat()
        return cls(outcome_space, specialist_calibrators, context_calibrators,
                   gate, pool_calibrator, context_pool_calibrators, fusion_method,
                   fit_through)

    @staticmethod
    def _fuse(rows: Mapping[str, Tuple[float, ...]], weights: Mapping[str, float],
              method: str) -> Tuple[float, ...]:
        if method == "linear":
            return linear_opinion_pool(rows, weights)
        if method == "logarithmic":
            return logarithmic_opinion_pool(rows, weights)
        raise ValueError("fusion_method must be linear or logarithmic")

    def predict(self, forecasts: Sequence[SpecialistForecast]) -> CouncilPrediction:
        if not forecasts:
            raise ValueError("prediction requires at least one specialist output")
        assert_compatible(tuple(forecasts))
        specialist_names = [forecast.specialist_id for forecast in forecasts]
        if len(specialist_names) != len(set(specialist_names)):
            raise ValueError("a prediction cannot contain duplicate specialist ids")
        if forecasts[0].outcome_space != self.outcome_space:
            raise ValueError("prediction outcome space differs from the fitted council")
        times = {forecast.forecast_time for forecast in forecasts}
        if len(times) != 1:
            raise ValueError("specialist forecasts must target the same forecast time")
        prediction_time = datetime.fromisoformat(next(iter(times)))
        if prediction_time <= datetime.fromisoformat(self.fit_through):
            raise ValueError("prediction time must be later than all council fit partitions")
        contexts = {forecast.context for forecast in forecasts}
        if len(contexts) != 1:
            raise ValueError("specialist forecasts must use the same gating context")
        unknown = {forecast.specialist_id for forecast in forecasts} - set(self.specialists)
        if unknown:
            raise ValueError("council received an unfitted specialist: " + ", ".join(sorted(unknown)))
        active = [forecast for forecast in forecasts if not forecast.abstain]
        if not active:
            raise ValueError("all specialists abstained; no fallback forecast is configured")

        raw = {}
        for forecast in active:
            calibrator = self.context_calibrators.get(
                (forecast.specialist_id, forecast.context),
                self.specialist_calibrators[forecast.specialist_id],
            )
            raw[forecast.specialist_id] = calibrator.apply(forecast.probabilities)
        weights = self.gate.weights_for(active[0].context, tuple(raw))
        pooled = self._fuse(raw, weights, self.fusion_method)
        final_calibrator = self.context_pool_calibrators.get(
            active[0].context, self.pool_calibrator
        )
        probabilities = final_calibrator.apply(pooled)
        entropy = -sum(p * math.log(max(1e-12, p)) for p in probabilities)
        epistemic_inputs = [(weights[f.specialist_id], f.epistemic_uncertainty)
                            for f in active if f.epistemic_uncertainty is not None]
        weighted_epistemic = None
        if epistemic_inputs:
            denominator = sum(weight for weight, _ in epistemic_inputs)
            weighted_epistemic = sum(weight * value for weight, value in epistemic_inputs) / denominator
        return CouncilPrediction(
            self.outcome_space, probabilities, active[0].forecast_time,
            tuple(f.specialist_id for f in active),
            tuple(f.specialist_id for f in forecasts if f.abstain),
            weights, entropy, disagreement(raw, weights, pooled), weighted_epistemic,
            self.fusion_method, active[0].dimensions, active[0].outcome_states,
        )

    def predict_parallel(self, forecast_tasks: Mapping[str, Callable[[], SpecialistForecast]],
                         max_workers: Optional[int] = None) -> CouncilPrediction:
        """Run independent specialist calls concurrently, then fuse their distributions."""
        if not forecast_tasks:
            raise ValueError("parallel prediction needs at least one specialist task")
        unknown = set(forecast_tasks) - set(self.specialists)
        if unknown:
            raise ValueError("parallel task names are not fitted specialists: "
                             + ", ".join(sorted(unknown)))
        workers = min(8, len(forecast_tasks)) if max_workers is None else max_workers
        if workers < 1:
            raise ValueError("max_workers must be positive")
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {name: executor.submit(task)
                       for name, task in forecast_tasks.items()}
            forecasts = []
            for name, future in futures.items():
                try:
                    forecast = future.result()
                except Exception as error:
                    for pending in futures.values():
                        pending.cancel()
                    raise RuntimeError("specialist inference failed: " + name) from error
                if forecast.specialist_id != name:
                    raise ValueError("parallel task key must match forecast specialist_id")
                forecasts.append(forecast)
        return self.predict(forecasts)

    def marginal(self, dimension: str) -> Dict[str, float]:
        """Marginalize the final joint distribution by a declared state dimension."""
        if dimension not in self.dimensions:
            raise ValueError("requested dimension is not declared in this council output")
        index = self.dimensions.index(dimension)
        result: Dict[str, float] = {}
        for state, probability in zip(self.outcome_states, self.probabilities):
            value = state[index]
            result[value] = result.get(value, 0.0) + probability
        return result
