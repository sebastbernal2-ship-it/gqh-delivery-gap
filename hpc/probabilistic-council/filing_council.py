#!/usr/bin/env python3
"""Two evidence blocks, one council, honest partitions.

The metadata block and the text block each become a council specialist. Both are fitted on the
earliest rows, the council calibrates, gates and pools on the next three small blocks, and the
comparison is scored on the final block. Every forecast carries the clock the contract requires.

This module is pure NumPy; the caller supplies the text embedding matrix.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Sequence

import numpy as np

COUNCIL = Path(__file__).resolve().parent
ROOT = COUNCIL.parents[1]
sys.path.insert(0, str(COUNCIL))
sys.path.insert(0, str(ROOT / "src"))
from council.council import CouncilModel, LabeledCase  # noqa: E402
from council.distributions import SpecialistForecast  # noqa: E402
from filing_specialist.model import (apply_scaler, fit_scaler, fit_softmax,  # noqa: E402
                                     predict_softmax, prevalence, score)
from filing_specialist.panel import BIN_LABELS  # noqa: E402


def as_matrix(values: Sequence[Sequence[float | None]]) -> np.ndarray:
    return np.array([[float("nan") if value is None else float(value) for value in row]
                     for row in values], dtype=float)


@dataclass(frozen=True)
class BlockSpecialist:
    specialist_id: str
    model_version: str
    data_version: str
    classes: tuple[int, ...]
    medians: tuple[float, ...]
    means: tuple[float, ...]
    scales: tuple[float, ...]
    parameters: tuple[tuple[float, ...], ...]

    def probability_vector(self, values: Sequence[float | None]) -> tuple[float, ...]:
        matrix = as_matrix([values])
        medians = np.array(self.medians)
        filled = np.where(np.isnan(matrix), medians, matrix)
        stats = (medians, np.array(self.means), np.array(self.scales))
        fitted = predict_softmax(np.array(self.parameters), apply_scaler(matrix, stats))[0]
        vector = [0.0] * len(BIN_LABELS)
        for position, label in enumerate(self.classes):
            vector[int(label)] = float(fitted[position])
        total = sum(vector)
        if total <= 0.0:
            raise ValueError("the block specialist produced no mass")
        return tuple(value / total for value in vector)

    def forecast(self, values: Sequence[float | None], context: str, information_cutoff: str,
                 forecast_time: str, valid_until: str, abstain: bool = False) -> SpecialistForecast:
        return SpecialistForecast(
            specialist_id=self.specialist_id,
            outcome_space=BIN_LABELS,
            probabilities=self.probability_vector(values),
            context=context,
            forecast_time=forecast_time,
            valid_until=valid_until,
            information_cutoff=information_cutoff,
            model_version=self.model_version,
            data_version=self.data_version,
            abstain=abstain,
        )


def fit_block(matrix: np.ndarray, labels: np.ndarray, specialist_id: str, model_version: str,
              data_version: str, steps: int = 600, seed: int = 20261004) -> BlockSpecialist:
    classes = tuple(sorted({int(label) for label in labels}))
    medians, means, scales = fit_scaler(matrix)
    parameters = fit_softmax(apply_scaler(matrix, (medians, means, scales)), labels, classes,
                             steps=steps, seed=seed)
    return BlockSpecialist(
        specialist_id=specialist_id, model_version=model_version, data_version=data_version,
        classes=classes,
        medians=tuple(float(value) for value in medians),
        means=tuple(float(value) for value in means),
        scales=tuple(float(value) for value in scales),
        parameters=tuple(tuple(float(value) for value in row) for row in parameters),
    )


def four_way(rows: list[dict], fractions: tuple[float, float, float, float] = (0.42, 0.10, 0.10, 0.10)
             ) -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict]]:
    """training, calibration, gate, pool, evaluation, in chronological order.

    A boundary never splits a shared timestamp: rows with the same clock stay in the earlier
    block, because the council requires strictly chronological partitions.
    """
    if abs(sum(fractions) - 0.72) > 1e-9:
        raise ValueError("training plus three small blocks must be 0.72 of the rows")
    total = len(rows)
    bounds = []
    running = 0
    for fraction in fractions:
        running += max(1, int(round(total * fraction)))
        while running < total and rows[running]["label_available"] == rows[running - 1]["label_available"]:
            running += 1
        bounds.append(running)
    bounds.append(total)
    cuts = [0] + bounds
    blocks = [rows[cuts[index]:cuts[index + 1]] for index in range(5)]
    if any(not block for block in blocks):
        raise ValueError("every block must be nonempty")
    return tuple(blocks)  # type: ignore[return-value]


def case_from(row: dict, index: int, forecasts: tuple[SpecialistForecast, ...],
              block: str) -> LabeledCase:
    return LabeledCase(context=f"{block}-{index}", label=int(row["label_bin"]),
                       forecasts=forecasts, case_id=f"{block}-{index}")


def clock(row: dict, previous_available: str | None) -> tuple[str, str, str]:
    """(information_cutoff, forecast_time, valid_until) ending at the reveal.

    A prior row that is not strictly earlier than the forecast instant cannot serve as the cutoff,
    which happens whenever two decisions share a timestamp; the fallback is a declared year-long
    conservative window.
    """
    import datetime

    reveal = datetime.datetime.fromisoformat(row["label_available"])
    forecast_time = reveal - datetime.timedelta(seconds=1)
    cutoff = None
    if previous_available:
        candidate = datetime.datetime.fromisoformat(previous_available)
        if candidate < forecast_time:
            cutoff = candidate
    if cutoff is None:
        cutoff = reveal - datetime.timedelta(days=365)
    return cutoff.isoformat(), forecast_time.isoformat(), reveal.isoformat()


def evaluate_council(blocks: tuple[list[dict], ...], metadata: np.ndarray, text: np.ndarray,
                     metadata_features: tuple[str, ...], steps: int = 600,
                     seed: int = 20261004) -> dict:
    """Fit both blocks on the training rows, the council on the small blocks, score the last."""
    training, calibration, gate, pool, evaluation = blocks
    train_labels = np.array([int(row["label_bin"]) for row in training], dtype=int)
    classes = tuple(sorted({int(label) for label in train_labels}))

    meta_specialist = fit_block(metadata[:len(training)], train_labels, "evidence:metadata",
                                "metadata-softmax-v1", "filing-panel-v1", steps, seed)
    text_specialist = fit_block(text[:len(training)], train_labels, "evidence:text",
                                "text-pca-softmax-v1", "text-embeddings-v1", steps, seed)

    meta_offset = len(training)
    calibration_cases = []
    for position, row in enumerate(calibration):
        index = meta_offset + position
        prior = calibration[position - 1]["label_available"] if position else None
        cutoff, forecast_time, valid_until = clock(row, prior)
        calibration_cases.append(case_from(row, index, (
            meta_specialist.forecast(list(metadata[index]), f"calibration-{index}", cutoff,
                                     forecast_time, valid_until),
            text_specialist.forecast(list(text[index]), f"calibration-{index}", cutoff,
                                     forecast_time, valid_until)), "calibration"))
    gate_cases = []
    gate_offset = meta_offset + len(calibration)
    for position, row in enumerate(gate):
        index = gate_offset + position
        prior = gate[position - 1]["label_available"] if position else None
        cutoff, forecast_time, valid_until = clock(row, prior)
        gate_cases.append(case_from(row, index, (
            meta_specialist.forecast(list(metadata[index]), f"gate-{index}", cutoff,
                                     forecast_time, valid_until),
            text_specialist.forecast(list(text[index]), f"gate-{index}", cutoff,
                                     forecast_time, valid_until)), "gate"))
    pool_cases = []
    pool_offset = gate_offset + len(gate)
    for position, row in enumerate(pool):
        index = pool_offset + position
        prior = pool[position - 1]["label_available"] if position else None
        cutoff, forecast_time, valid_until = clock(row, prior)
        pool_cases.append(case_from(row, index, (
            meta_specialist.forecast(list(metadata[index]), f"pool-{index}", cutoff,
                                     forecast_time, valid_until),
            text_specialist.forecast(list(text[index]), f"pool-{index}", cutoff,
                                     forecast_time, valid_until)), "pool"))
    council = CouncilModel.fit(calibration_cases, gate_cases, pool_cases, fusion_method="linear")

    evaluation_offset = pool_offset + len(pool)
    evaluation_labels = np.array([int(row["label_bin"]) for row in evaluation], dtype=int)
    council_rows, meta_rows, text_rows = [], [], []
    for position, row in enumerate(evaluation):
        index = evaluation_offset + position
        prior = evaluation[position - 1]["label_available"] if position else None
        cutoff, forecast_time, valid_until = clock(row, prior)
        meta_forecast = meta_specialist.forecast(list(metadata[index]), f"evaluation-{index}",
                                                 cutoff, forecast_time, valid_until)
        text_forecast = text_specialist.forecast(list(text[index]), f"evaluation-{index}",
                                                 cutoff, forecast_time, valid_until)
        council_rows.append(council.predict((meta_forecast, text_forecast)).probabilities)
        meta_rows.append(meta_forecast.probabilities)
        text_rows.append(text_forecast.probabilities)

    prior = prevalence(training, classes)
    concatenated = np.column_stack([metadata, text])
    concatenated_specialist = fit_block(concatenated[:len(training)], train_labels,
                                        "evidence:concatenated", "concatenated-v1", "both-v1",
                                        steps, seed)
    concatenated_rows = [concatenated_specialist.probability_vector(list(concatenated[index]))
                         for index in range(evaluation_offset, evaluation_offset + len(evaluation))]
    return {
        "blocks": {"training": len(training), "calibration": len(calibration), "gate": len(gate),
                   "pool": len(pool), "evaluation": len(evaluation)},
        "evaluation_window": {"from": evaluation[0]["label_available"],
                              "to": evaluation[-1]["label_available"]},
        "prevalence": score(np.tile(prior, (len(evaluation_labels), 1)), evaluation_labels, classes),
        "metadata_only": score(np.array(meta_rows), evaluation_labels, classes),
        "text_only": score(np.array(text_rows), evaluation_labels, classes),
        "concatenated": score(np.array(concatenated_rows), evaluation_labels, classes),
        "council": score(np.array(council_rows), evaluation_labels, classes),
        "gate_weights": dict(council.gate.weights_for("calibration-0", council.specialists))
        if calibration_cases else {},
        "specialists": list(council.specialists),
        "metadata_features": list(metadata_features),
    }
