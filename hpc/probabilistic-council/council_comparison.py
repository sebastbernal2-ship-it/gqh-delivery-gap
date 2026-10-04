#!/usr/bin/env python3
"""Declared comparison: the calibrated council against every single checkpoint and the references.

Protocol: docs/plan/jev-council-comparison.md. Development only: the evaluation role was already
inspected during the checkpoint campaign, so it is not a fresh holdout and nothing here is a
trading claim.

    python3 council_comparison.py --cache <cache> \
      --checkpoints checkpoints/hpg-44665003 --output /private/staging/comparison-001
"""
from __future__ import annotations

import argparse
import bisect
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from council.council import CouncilModel, LabeledCase  # noqa: E402
from council.distributions import probabilities_to_quantiles  # noqa: E402
from council.risk_adapter import QUANTILE_LEVELS, SIDES, TASKS, risk_forecasts  # noqa: E402
from execution_action_model import QUANTILES, pinball_loss  # noqa: E402
from execution_dataset import ADVERSE_EDGES, TERMINAL_EDGES, HORIZONS  # noqa: E402
from execution_risk_predict import ExecutionRiskPredictor  # noqa: E402

PARTITIONS = ("training", "specialist_calibration", "gate_fit", "pool_calibration", "evaluation")
EDGES = {"terminal_loss": TERMINAL_EDGES, "observed_adverse": ADVERSE_EDGES}
FIELDS = ("features", "targets", "roles", "clocks")


def iso(nanoseconds: int) -> str:
    return datetime.fromtimestamp(nanoseconds / 1e9, timezone.utc).isoformat()


def load_cache(path: Path) -> dict:
    spec = json.loads((path / "manifest.json").read_text())
    arrays = {name: np.load(path / f"{name}.npy", allow_pickle=False) for name in FIELDS}
    features, targets = arrays["features"], arrays["targets"]
    roles, clocks = arrays["roles"], arrays["clocks"]
    if features.ndim != 3 or features.shape[1:] != (16, 24):
        raise ValueError("features must be (cases, 16, 24)")
    if targets.shape != (features.shape[0], len(HORIZONS), len(SIDES), len(TASKS)):
        raise ValueError("targets must be (cases, horizons, sides, tasks)")
    if roles.shape != (features.shape[0],) or clocks.shape != (features.shape[0], 2):
        raise ValueError("roles and clocks must have one row per case")
    if ((roles < 0) | (roles > 4)).any() or clocks.dtype != np.int64:
        raise ValueError("roles must be 0 to 4 and clocks must be int64")
    if (np.diff(clocks[:, 0]) <= 0).any():
        raise ValueError("cases must be in chronological order")
    return {"spec": spec, "features": features, "targets": targets,
            "roles": roles.astype(int), "clocks": clocks}


def bin_index(target_bps: float, edges) -> int:
    """Same left-closed convention as execution_risk_dataset.py."""
    return int(bisect.bisect_right(edges, float(target_bps)))


def marginal_pinball(predictions, targets) -> float:
    """Mean pinball in basis points for a stack of marginal forecasts."""
    prediction = torch.as_tensor(np.asarray(predictions, dtype=float))
    target = torch.as_tensor(np.asarray(targets, dtype=float))
    if prediction.ndim == 1:
        prediction = prediction.reshape(1, -1)
        target = target.reshape(1)
    return float(pinball_loss(prediction, target, quantiles=QUANTILES))


def load_specialists(checkpoints: Path, manifest: dict, device: str = "cpu") -> dict:
    return {name.removesuffix(".pt"): ExecutionRiskPredictor(checkpoints / name, entry["sha256"], device)
            for name, entry in sorted(manifest["checkpoints"].items())}


def predict_all(cache: dict, specialists: dict, limit: int | None = None) -> dict:
    cases = cache["features"].shape[0] if limit is None else min(limit, cache["features"].shape[0])
    predictions = {}
    for name, predictor in specialists.items():
        cube = np.empty((cases, len(HORIZONS), len(SIDES), len(TASKS), len(QUANTILES)))
        for index in range(cases):
            cube[index] = np.asarray(predictor.risk(cache["features"][index]), dtype=float)
        if not np.isfinite(cube).all():
            raise ValueError(f"{name} produced nonfinite risk quantiles")
        predictions[name] = cube
    return predictions


def pinball_table(predictions: dict, cache: dict) -> dict:
    """Native pinball in basis points per specialist, marginal and role."""
    roles = cache["roles"][:next(iter(predictions.values())).shape[0]]
    table = {}
    for name, cube in predictions.items():
        per_role = {}
        for role, label in enumerate(PARTITIONS):
            if role == 0:
                continue
            rows = []
            for horizon in range(len(HORIZONS)):
                for side in range(len(SIDES)):
                    for task in range(len(TASKS)):
                        mask = roles == role
                        if not mask.any():
                            continue
                        loss = marginal_pinball(cube[mask, horizon, side, task],
                                                cache["targets"][mask, horizon, side, task])
                        rows.append((f"{HORIZONS[horizon]}s:{SIDES[side]}:{TASKS[task]}", loss))
            per_role[label] = dict(rows)
        table[name] = per_role
    return table


def marginal_cases(predictions: dict, cache: dict, task: str, role: int) -> list[LabeledCase]:
    """One labeled case per case, horizon and side; one forecast per specialist inside it."""
    cases = []
    task_index = TASKS.index(task)
    for index in np.flatnonzero(cache["roles"] == role):
        for horizon in range(len(HORIZONS)):
            for side in range(len(SIDES)):
                context = f"{HORIZONS[horizon]}s:{SIDES[side]}:{task}"
                forecasts = []
                for name, cube in predictions.items():
                    converted = risk_forecasts(cube[index], EDGES,
                                               context=context,
                                               forecast_time=iso(cache["clocks"][index, 1]),
                                               valid_until=iso(cache["clocks"][index, 1] + 60_000_000_000),
                                               information_cutoff=iso(cache["clocks"][index, 1] - 1_000_000_000),
                                               model_version=name, data_version="risk-cache",
                                               id_prefix=name, flat_id=True)
                    position = (horizon * len(SIDES) * len(TASKS)) + (side * len(TASKS)) + task_index
                    forecasts.append(converted[position])
                label = bin_index(cache["targets"][index, horizon, side, task_index], EDGES[task])
                cases.append(LabeledCase(context=context, label=label, forecasts=tuple(forecasts),
                                         case_id=f"{task}-{index}-{horizon}-{side}"))
    return cases


def prevalence_table(cache: dict) -> dict:
    """Training-role bin frequencies per horizon, side and task, with one pseudo-count per bin."""
    counts = {}
    training = cache["roles"] == 0
    for horizon in range(len(HORIZONS)):
        for side in range(len(SIDES)):
            for task, edges in EDGES.items():
                bins = len(edges) + 1
                histogram = np.ones(bins)
                task_index = TASKS.index(task)
                for index in np.flatnonzero(training):
                    histogram[bin_index(cache["targets"][index, horizon, side, task_index], edges)] += 1
                counts[f"{HORIZONS[horizon]}s:{SIDES[side]}:{task}"] = histogram / histogram.sum()
    return counts


def evaluate(cache: dict, predictions: dict, manifest: dict) -> dict:
    evaluation = cache["roles"] == 4
    if not evaluation.any():
        raise ValueError("the cache needs an evaluation role")
    per_task = {}
    for task in TASKS:
        cases = {role: marginal_cases(predictions, cache, task, role) for role in (1, 2, 3)}
        council = CouncilModel.fit(cases[1], cases[2], cases[3], fusion_method="linear")
        evaluation_cases = {case.case_id: case for case in marginal_cases(predictions, cache, task, 4)}
        prevalence = prevalence_table(cache)
        names = ("council", "prevalence", *predictions)
        scores = {name: {"log_loss": [], "pinball": []} for name in names}
        for index in np.flatnonzero(evaluation):
            for horizon in range(len(HORIZONS)):
                for side in range(len(SIDES)):
                    task_index = TASKS.index(task)
                    target = float(cache["targets"][index, horizon, side, task_index])
                    label = bin_index(target, EDGES[task])
                    case = evaluation_cases[f"{task}-{index}-{horizon}-{side}"]
                    probabilities = tuple(council.predict(case.forecasts).probabilities)
                    scores["council"]["log_loss"].append(-math.log(max(1e-12, probabilities[label])))
                    scores["council"]["pinball"].append(marginal_pinball(
                        probabilities_to_quantiles(probabilities, EDGES[task], QUANTILE_LEVELS), target))
                    prior = prevalence[f"{HORIZONS[horizon]}s:{SIDES[side]}:{task}"]
                    scores["prevalence"]["log_loss"].append(-math.log(max(1e-12, prior[label])))
                    scores["prevalence"]["pinball"].append(marginal_pinball(
                        probabilities_to_quantiles(prior, EDGES[task], QUANTILE_LEVELS), target))
                    for name, cube in predictions.items():
                        identifier = name
                        forecast = next(item for item in case.forecasts
                                        if item.specialist_id == identifier)
                        scores[name]["log_loss"].append(-math.log(max(1e-12, forecast.probabilities[label])))
                        scores[name]["pinball"].append(marginal_pinball(
                            cube[index, horizon, side, task_index], target))
        per_task[task] = {name: {"log_loss": float(np.mean(values["log_loss"])),
                                 "pinball": float(np.mean(values["pinball"]))}
                          for name, values in scores.items()}
    recomputation = {}
    for name, entry in manifest["checkpoints"].items():
        stem = name.removesuffix(".pt")
        if stem not in predictions:
            continue
        recomputed = float(np.mean(list(
            pinball_table({stem: predictions[stem]}, cache)[stem]["evaluation"].values())))
        published = float(entry["evaluation_pinball_bps"])
        recomputation[stem] = {"recomputed": recomputed, "published": published,
                               "absolute_difference": abs(recomputed - published)}
    return {"per_task": per_task, "recomputation": recomputation}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--checkpoints", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    cache = load_cache(args.cache)
    manifest = json.loads((args.checkpoints / "manifest.json").read_text())
    specialists = load_specialists(args.checkpoints, manifest)
    predictions = predict_all(cache, specialists, args.limit)
    report = {
        "schema": "council-comparison-v1",
        "scope": "development_only",
        "protocol": "docs/plan/jev-council-comparison.md",
        "published_pinball": pinball_table(predictions, cache),
        "comparison": evaluate(cache, predictions, manifest),
        "ready_for_performance_claim": False,
        "limitations": [
            "reused development data; the evaluation role was already inspected",
            "no fresh holdout, no filled orders, no trading claim",
            "the categorical scores depend on the declared bin edges and the linear tail conversion",
        ],
    }
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    comparison = report["comparison"]["per_task"]
    for task, rows in comparison.items():
        print(task)
        for name, values in sorted(rows.items(), key=lambda item: item[1]["pinball"]):
            print(f"  {name:24s} pinball {values['pinball']:.6f}  log loss {values['log_loss']:.6f}")
    worst = max((abs(value["absolute_difference"]) for value in report["comparison"]["recomputation"].values()),
                default=0.0)
    print(f"published pinball recomputation: worst absolute difference {worst:.2e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
