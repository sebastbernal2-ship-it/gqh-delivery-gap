#!/usr/bin/env python3
"""Synthetic-only reference path for calibrated specialist distributions and council fusion."""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from typing import Iterable


TEMPERATURES = (0.5, 0.7, 0.85, 1.0, 1.2, 1.5, 2.0, 3.0)
FLOOR = 1e-9


def sigmoid(value: float) -> float:
    if value >= 0:
        exp_value = math.exp(-value)
        return 1.0 / (1.0 + exp_value)
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)


def binary_log_loss(rows: Iterable[dict], probabilities: Iterable[float]) -> float:
    pairs = list(zip(rows, probabilities))
    return sum(
        -(row["outcome"] * math.log(max(FLOOR, min(1.0 - FLOOR, p)))
          + (1 - row["outcome"]) * math.log(max(FLOOR, min(1.0 - FLOOR, 1.0 - p))))
        for row, p in pairs
    ) / max(1, len(pairs))


def brier(rows: list[dict], probabilities: list[float]) -> float:
    return sum((row["outcome"] - p) ** 2 for row, p in zip(rows, probabilities)) / max(1, len(rows))


def ece(rows: list[dict], probabilities: list[float], bins: int = 10) -> float:
    buckets: list[list[tuple[int, float]]] = [[] for _ in range(bins)]
    for row, p in zip(rows, probabilities):
        index = min(bins - 1, int(p * bins))
        buckets[index].append((row["outcome"], p))
    total = max(1, len(rows))
    return sum(
        len(bucket) / total
        * abs(sum(y for y, _ in bucket) / len(bucket) - sum(p for _, p in bucket) / len(bucket))
        for bucket in buckets if bucket
    )


def make_rows(seed: int, count: int) -> list[dict]:
    rng = random.Random(seed)
    rows = []
    for i in range(count):
        regime = rng.randrange(2)
        feature = rng.gauss(0.0, 1.0)
        slope = 1.8 if regime == 0 else -1.8
        probability = sigmoid(slope * feature)
        outcome = int(rng.random() < probability)
        rows.append({"index": i, "regime": regime, "feature": feature, "outcome": outcome})
    return rows


def fit_slope(rows: list[dict], target_regime: int) -> float:
    """Fit a deliberately small, transparent grid-logistic specialist."""
    candidates = (0.0, 0.4, 0.8, 1.2, 1.6, 2.0, 2.4, 3.0)
    selected = 0.0
    best_loss = math.inf
    for magnitude in candidates:
        signed = magnitude if target_regime == 0 else -magnitude
        eligible = [row for row in rows if row["regime"] == target_regime]
        loss = binary_log_loss(eligible, (sigmoid(signed * row["feature"]) for row in eligible))
        if loss < best_loss:
            selected, best_loss = signed, loss
    return selected


def raw_probability(row: dict, slopes: dict[str, float], specialist: str) -> float:
    return sigmoid(slopes[specialist] * row["feature"])


def apply_temperature(probability: float, temperature: float) -> float:
    clipped = max(FLOOR, min(1.0 - FLOOR, probability))
    logit = math.log(clipped / (1.0 - clipped))
    return sigmoid(logit / temperature)


def distribution(probability_yes: float) -> list[float]:
    """Return a validated full distribution in the contract's [no, yes] class order."""
    values = [1.0 - probability_yes, probability_yes]
    if any(not math.isfinite(value) or value < 0.0 or value > 1.0 for value in values):
        raise ValueError("specialist output must be a finite probability distribution")
    if abs(sum(values) - 1.0) > 1e-9:
        raise ValueError("specialist probabilities must sum to one")
    return values


def fit_temperature(rows: list[dict], probabilities: list[float]) -> float:
    return min(
        TEMPERATURES,
        key=lambda temperature: binary_log_loss(
            rows, (apply_temperature(p, temperature) for p in probabilities)
        ),
    )


def reliability_weights(rows: list[dict], forecasts: dict[str, list[float]]) -> dict[int, dict[str, float]]:
    errors: dict[int, dict[str, float]] = defaultdict(dict)
    for regime in (0, 1):
        indexes = [i for i, row in enumerate(rows) if row["regime"] == regime]
        for name, values in forecasts.items():
            error = sum((rows[i]["outcome"] - values[i]) ** 2 for i in indexes) / max(1, len(indexes))
            errors[regime][name] = 1.0 / max(FLOOR, error)
        total = sum(errors[regime].values())
        errors[regime] = {name: value / total for name, value in errors[regime].items()}
    return errors


def weighted_pool(row: dict, forecasts: dict[str, float], weights: dict[int, dict[str, float]]) -> float:
    context_weights = weights[row["regime"]]
    return sum(context_weights[name] * probability for name, probability in forecasts.items())


def metrics(rows: list[dict], probabilities: list[float]) -> dict[str, float]:
    return {
        "log_loss": round(binary_log_loss(rows, probabilities), 6),
        "brier": round(brier(rows, probabilities), 6),
        "ece_10_equal_width_bins": round(ece(rows, probabilities), 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20261003)
    parser.add_argument("--rows", type=int, default=12000)
    args = parser.parse_args()
    if args.rows < 400:
        parser.error("--rows must be at least 400 so all four partitions have observations")

    rows = make_rows(args.seed, args.rows)
    first = args.rows // 2
    second = first + args.rows * 15 // 100
    third = second + args.rows * 15 // 100
    fourth = third + args.rows * 10 // 100
    train, calibration, gate_fit, pool_calibration, evaluation = (
        rows[:first], rows[first:second], rows[second:third], rows[third:fourth], rows[fourth:]
    )
    specialists = ("trend", "reversal")
    target_regimes = {"trend": 0, "reversal": 1}
    slopes = {name: fit_slope(train, target_regimes[name]) for name in specialists}

    calibration_raw = {
        name: [raw_probability(row, slopes, name) for row in calibration]
        for name in specialists
    }
    temperatures = {
        name: {
            regime: fit_temperature(
                [row for row in calibration if row["regime"] == regime],
                [probability for row, probability in zip(calibration, calibration_raw[name])
                 if row["regime"] == regime],
            )
            for regime in (0, 1)
        }
        for name in specialists
    }

    def calibrated(name: str, row: dict) -> float:
        return apply_temperature(
            raw_probability(row, slopes, name), temperatures[name][row["regime"]]
        )

    gate_forecasts = {
        name: [calibrated(name, row) for row in gate_fit] for name in specialists
    }
    weights = reliability_weights(gate_fit, gate_forecasts)
    pool_calibration_equal = [
        sum(calibrated(name, row) for name in specialists) / len(specialists)
        for row in pool_calibration
    ]
    pool_calibration_gated = [
        weighted_pool(
            row, {name: calibrated(name, row) for name in specialists}, weights
        )
        for row in pool_calibration
    ]
    equal_pool_temperature = fit_temperature(pool_calibration, pool_calibration_equal)
    gated_pool_temperature = fit_temperature(pool_calibration, pool_calibration_gated)
    evaluation_distributions = {
        name: [distribution(calibrated(name, row)) for row in evaluation]
        for name in specialists
    }
    evaluation_forecasts = {
        name: [values[1] for values in specialist_distributions]
        for name, specialist_distributions in evaluation_distributions.items()
    }
    equal_pool_raw = [sum(evaluation_forecasts[name][i] for name in specialists) / len(specialists)
                      for i in range(len(evaluation))]
    gated_pool_raw = [
        weighted_pool(row, {name: evaluation_forecasts[name][i] for name in specialists}, weights)
        for i, row in enumerate(evaluation)
    ]
    equal_pool = [apply_temperature(p, equal_pool_temperature) for p in equal_pool_raw]
    gated_pool = [apply_temperature(p, gated_pool_temperature) for p in gated_pool_raw]
    prevalence = sum(row["outcome"] for row in train) / len(train)
    climatology = [prevalence] * len(evaluation)

    report = {
        "contract": "synthetic-council-0.1.0",
        "data": "synthetic_iid_fixture_only",
        "seed": args.seed,
        "rows": {"fit": len(train), "specialist_calibration": len(calibration),
                 "gate_fit": len(gate_fit), "pool_calibration": len(pool_calibration),
                 "evaluation": len(evaluation)},
        "pool_calibration_temperatures": {
            "equal_pool": equal_pool_temperature,
            "regime_gated_pool": gated_pool_temperature,
        },
        "outcome_order": ["no", "yes"],
        "specialists": {
            name: {"fitted_slope": round(slopes[name], 6),
                  "temperature_by_regime": {
                      str(regime): temperatures[name][regime] for regime in (0, 1)
                  },
                  "first_evaluation_distribution": [
                      round(value, 8) for value in evaluation_distributions[name][0]
                  ],
                  "gate_weights_by_regime": {
                      str(regime): round(weights[regime][name], 6) for regime in (0, 1)
                  }}
            for name in specialists
        },
        "evaluation_metrics": {
            "training_prevalence_baseline": metrics(evaluation, climatology),
            "equal_pool_before_final_calibration": metrics(evaluation, equal_pool_raw),
            "equal_probability_pool": metrics(evaluation, equal_pool),
            "gated_pool_before_final_calibration": metrics(evaluation, gated_pool_raw),
            "regime_gated_probability_pool": metrics(evaluation, gated_pool),
        },
        "first_fused_distribution": [round(1.0 - gated_pool[0], 8), round(gated_pool[0], 8)],
        "limitations": [
            "synthetic data only; no market data or financial target",
            "no JevLike checkpoint or neural training in this synthetic council fixture",
            "evaluation partition is not the competition sealed OOS period",
            "linear opinion pool is a baseline and does not reconstruct general joint dependence",
        ],
    }
    print(json.dumps(report, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
