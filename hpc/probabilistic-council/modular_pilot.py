#!/usr/bin/env python3
"""Run the modular council on a synthetic, chronologically partitioned fixture."""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Sequence, Tuple

from council.calibration import fit_temperature
from council import CouncilModel, LabeledCase, SpecialistForecast
from council.fusion import linear_opinion_pool
from pilot import fit_slope, make_rows, raw_probability


OUTCOMES = ("no", "yes")
SPECIALISTS = ("trend", "reversal")
FLOOR = 1e-12


def forecast_for(row: dict, slopes: Dict[str, float]) -> LabeledCase:
    forecast_time = (datetime(2020, 1, 1, tzinfo=timezone.utc)
                     + timedelta(days=row["index"])).isoformat()
    cutoff = (datetime.fromisoformat(forecast_time) - timedelta(days=1)).isoformat()
    valid_until = (datetime.fromisoformat(forecast_time) + timedelta(days=1)).isoformat()
    regime = str(row["regime"])
    forecasts = []
    for specialist in SPECIALISTS:
        probability = raw_probability(row, slopes, specialist)
        forecasts.append(SpecialistForecast(
            specialist_id=specialist,
            outcome_space=OUTCOMES,
            probabilities=(1.0 - probability, probability),
            context=regime,
            forecast_time=forecast_time,
            valid_until=valid_until,
            information_cutoff=cutoff,
            model_version="synthetic-logistic-0.1.0",
            data_version="synthetic-fixture-0.1.0",
        ))
    return LabeledCase(regime, row["outcome"], tuple(forecasts),
                       case_id="synthetic-row-{}".format(row["index"]))


def metric(rows: Sequence[LabeledCase], predictions: Sequence[Tuple[float, ...]]) -> dict:
    labels = [row.label for row in rows]
    if len(rows) != len(predictions) or not rows:
        raise ValueError("metrics need equally sized nonempty cases and predictions")
    log_loss = sum(-math.log(max(FLOOR, p[label]))
                   for p, label in zip(predictions, labels)) / len(rows)
    brier = sum(sum((probability - (1.0 if i == label else 0.0)) ** 2
                    for i, probability in enumerate(p))
                for p, label in zip(predictions, labels)) / len(rows)
    bins: List[List[Tuple[int, float]]] = [[] for _ in range(10)]
    for probabilities, label in zip(predictions, labels):
        confidence = max(probabilities)
        predicted = probabilities.index(confidence)
        bins[min(9, int(confidence * 10))].append((int(predicted == label), confidence))
    ece = sum(
        len(bucket) / len(rows)
        * abs(sum(correct for correct, _ in bucket) / len(bucket)
              - sum(confidence for _, confidence in bucket) / len(bucket))
        for bucket in bins if bucket
    )
    return {"log_loss": round(log_loss, 6), "multiclass_brier": round(brier, 6),
            "top_label_ece_10_bins": round(ece, 6)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20261003)
    parser.add_argument("--rows", type=int, default=12000)
    args = parser.parse_args()
    if args.rows < 1000:
        parser.error("--rows must be at least 1000 for the five disjoint partitions")
    all_rows = make_rows(args.seed, args.rows)
    i_train = args.rows // 2
    i_cal = i_train + args.rows * 15 // 100
    i_gate = i_cal + args.rows * 15 // 100
    i_pool = i_gate + args.rows * 10 // 100
    training = all_rows[:i_train]
    calibration_rows = all_rows[i_train:i_cal]
    gate_rows = all_rows[i_cal:i_gate]
    pool_rows = all_rows[i_gate:i_pool]
    evaluation_rows = all_rows[i_pool:]

    slopes = {
        "trend": fit_slope(training, 0),
        "reversal": fit_slope(training, 1),
    }
    calibration = [forecast_for(row, slopes) for row in calibration_rows]
    gate_fit = [forecast_for(row, slopes) for row in gate_rows]
    pool_calibration = [forecast_for(row, slopes) for row in pool_rows]
    evaluation = [forecast_for(row, slopes) for row in evaluation_rows]
    linear_model = CouncilModel.fit(calibration, gate_fit, pool_calibration,
                                    fusion_method="linear")
    log_model = CouncilModel.fit(calibration, gate_fit, pool_calibration,
                                 fusion_method="logarithmic")

    linear_predictions = [linear_model.predict(case.forecasts) for case in evaluation]
    log_predictions = [log_model.predict(case.forecasts) for case in evaluation]

    def equal_pool(case: LabeledCase, model: CouncilModel) -> Tuple[float, ...]:
        calibrated = {}
        for forecast in case.forecasts:
            calibrator = model.context_calibrators.get(
                (forecast.specialist_id, case.context),
                model.specialist_calibrators[forecast.specialist_id],
            )
            calibrated[forecast.specialist_id] = calibrator.apply(forecast.probabilities)
        return linear_opinion_pool(calibrated, {name: 1.0 for name in calibrated})

    equal_pool_calibration = [equal_pool(case, linear_model) for case in pool_calibration]
    equal_temperature = fit_temperature(
        equal_pool_calibration, [case.label for case in pool_calibration]
    )
    equal_predictions = [
        equal_temperature.apply(equal_pool(case, linear_model)) for case in evaluation
    ]

    training_prevalence = sum(row["outcome"] for row in training) / len(training)
    climatology = [(1.0 - training_prevalence, training_prevalence)] * len(evaluation)
    first = linear_predictions[0]
    ablated = [replace(f, abstain=(f.specialist_id == "reversal"))
               for f in evaluation[0].forecasts]
    ablation_prediction = linear_model.predict(ablated)
    report = {
        "contract": "council-distribution-0.2.0",
        "data": "synthetic_regime_dependent_binary_fixture_only",
        "seed": args.seed,
        "rows": {"training": len(training), "specialist_calibration": len(calibration),
                 "gate_fit": len(gate_fit), "pool_calibration": len(pool_calibration),
                 "evaluation": len(evaluation)},
        "fitted_specialist_temperatures": {
            name: {"global": cal.temperature,
                  "by_regime": {
                      context: model.temperature
                      for (specialist, context), model in linear_model.context_calibrators.items()
                      if specialist == name
                  }}
            for name, cal in linear_model.specialist_calibrators.items()
        },
        "gate_weights_by_regime": linear_model.gate.context_weights,
        "pool_temperature": linear_model.pool_calibrator.temperature,
        "evaluation_metrics": {
            "training_prevalence": metric(evaluation, climatology),
            "equal_probability_pool_calibrated": metric(evaluation, equal_predictions),
            "context_gated_linear_pool": metric(
                evaluation, [prediction.probabilities for prediction in linear_predictions]
            ),
            "context_gated_logarithmic_pool": metric(
                evaluation, [prediction.probabilities for prediction in log_predictions]
            ),
        },
        "first_fused_distribution": {
            "outcome_order": list(linear_model.outcome_space),
            "probabilities": [round(value, 8) for value in first.probabilities],
            "gate_weights": linear_predictions[0].gate_weights,
            "predictive_entropy_nats": round(first.predictive_entropy, 8),
            "between_model_disagreement": round(first.between_model_disagreement, 8),
        },
        "abstention_ablation": {
            "active_specialists": list(ablation_prediction.active_specialists),
            "abstained_specialists": list(ablation_prediction.abstained_specialists),
            "renormalized_gate_weights": ablation_prediction.gate_weights,
            "distribution": [round(value, 8) for value in ablation_prediction.probabilities],
        },
        "limitations": [
            "synthetic fixture only; no market observations, JevLike weights, or financial target",
            "categorical distributions; joint outcomes require a declared finite joint state space",
            "temperature calibration and Brier reliability weights are baselines, not production defaults",
            "linear and logarithmic opinion pools are alternatives; neither assumes independent votes",
            "abstention is handled by active-weight renormalization; all-abstain fallback is not configured",
            "evaluation rows are synthetic and are not the competition sealed out-of-sample window",
        ],
    }
    print(json.dumps(report, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
