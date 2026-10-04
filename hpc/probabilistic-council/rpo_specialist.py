#!/usr/bin/env python3
"""The RPO surprise model as a council specialist.

One fitted model, one forecast per disclosure, carrying the clock and provenance the council
contract requires. A disclosure with no prior history abstains instead of inventing a forecast.

The forecast is for the disclosure's own surprise, made from strictly earlier disclosures, so its
window ends exactly at the reveal: information_cutoff is the latest prior clock used, forecast_time
is one second before the disclosure, and valid_until is the disclosure itself.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from pathlib import Path
import sys

import numpy as np

COUNCIL = Path(__file__).resolve().parent
ROOT = COUNCIL.parents[1]
sys.path.insert(0, str(COUNCIL))
sys.path.insert(0, str(ROOT / "src"))
from council.distributions import SpecialistForecast  # noqa: E402
from filing_specialist.model import (apply_scaler, fit_scaler, fit_softmax,  # noqa: E402
                                     matrix_from_rows, predict_softmax)
from filing_specialist.rpo_model import BIN_LABELS  # noqa: E402


@dataclass(frozen=True)
class FittedRpoSpecialist:
    feature_names: tuple[str, ...]
    classes: tuple[int, ...]
    medians: tuple[float, ...]
    means: tuple[float, ...]
    scales: tuple[float, ...]
    parameters: tuple[tuple[float, ...], ...]
    model_version: str
    data_version: str

    def probability_vector(self, row: dict) -> tuple[float, ...]:
        """Full five-bin distribution; a class absent from the fit holds zero mass."""
        matrix, _ = matrix_from_rows([row], self.feature_names)
        stats = (np.array(self.medians), np.array(self.means), np.array(self.scales))
        parameters = np.array(self.parameters)
        fitted = predict_softmax(parameters, apply_scaler(matrix, stats))[0]
        vector = [0.0] * len(BIN_LABELS)
        for position, label in enumerate(self.classes):
            vector[int(label)] = float(fitted[position])
        total = sum(vector)
        if total <= 0.0:
            raise ValueError("the fitted model produced no mass")
        return tuple(value / total for value in vector)

    def forecast(self, row: dict, context: str, information_cutoff: str, forecast_time: str,
                 valid_until: str) -> SpecialistForecast:
        return SpecialistForecast(
            specialist_id=f"rpo-surprise:{self.model_version}",
            outcome_space=BIN_LABELS,
            probabilities=self.probability_vector(row),
            context=context,
            forecast_time=forecast_time,
            valid_until=valid_until,
            information_cutoff=information_cutoff,
            model_version=self.model_version,
            data_version=self.data_version,
            abstain=bool(row.get("missing_prior")),
        )


def fit_rpo_specialist(rows: list[dict], feature_names: tuple[str, ...], model_version: str,
                       data_version: str, steps: int = 600, seed: int = 20261004) -> FittedRpoSpecialist:
    classes = tuple(sorted({int(row["label_bin"]) for row in rows}))
    matrix, labels = matrix_from_rows(rows, feature_names)
    medians, means, scales = fit_scaler(matrix)
    parameters = fit_softmax(apply_scaler(matrix, (medians, means, scales)), labels, classes,
                             steps=steps, seed=seed)
    return FittedRpoSpecialist(
        feature_names=tuple(feature_names),
        classes=classes,
        medians=tuple(float(value) for value in medians),
        means=tuple(float(value) for value in means),
        scales=tuple(float(value) for value in scales),
        parameters=tuple(tuple(float(value) for value in row) for row in parameters),
        model_version=model_version,
        data_version=data_version,
    )


def disclosure_window(row: dict, prior_available: str | None) -> tuple[str, str, str]:
    """(information_cutoff, forecast_time, valid_until) for one disclosure."""
    reveal = datetime.datetime.fromisoformat(row["label_available"])
    forecast_time = (reveal - datetime.timedelta(seconds=1)).isoformat()
    cutoff = prior_available or (reveal - datetime.timedelta(days=365)).isoformat()
    return cutoff, forecast_time, row["label_available"]
