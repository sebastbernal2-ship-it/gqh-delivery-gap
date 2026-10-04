#!/usr/bin/env python3
"""Does a student trained on the teacher's probabilities beat the teacher, and do both beat the rivals?

Aidan's training design asks for teacher targets through forward chronological folds, a direct against
distilled comparison, and proper scoring losses. This runs exactly that on the surviving specialist's
own panel, plus the two rivals that bound how much the model adds at all:

  teacher        the walk-forward softmax, refit per annual origin on its own features
  distilled      the same features and form, trained on the teacher's probabilities rather than labels
  hard student   the same, trained on labels (identical in kind to the teacher; the honest control)
  rivals         every event at equal weight, and the unconditional class frequencies

Evaluation is the same folds for every arm, scored by log loss and accuracy, and each arm's conviction
becomes a sleeve under the identical rule, costs and window so the money question is answered too.

    python3 scripts/run_distillation_test.py
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.model import (apply_scaler, fit_scaler, fit_softmax, matrix_from_rows,  # noqa: E402
                                     predict_softmax, softmax)
from filing_specialist.portfolio_stats import month_blocked_interval, portfolio_metrics  # noqa: E402
from filing_specialist.rpo_model import FEATURES, prepare_rows  # noqa: E402
from run_sleeve_portfolio import COSTS, sleeve_daily  # noqa: E402
from run_walk_forward import ORIGINS, blocks  # noqa: E402

STEPS = 600
RATE = 0.5
L2 = 1.0


def fit_soft_targets(matrix: np.ndarray, targets: np.ndarray, steps: int = STEPS,
                     seed: int = 20261004) -> np.ndarray:
    """The same full-batch fitter, but the target is a probability vector rather than a one-hot label."""
    rng = np.random.default_rng(seed)
    parameters = rng.normal(scale=0.01, size=(matrix.shape[1] + 1, targets.shape[1]))
    design = np.column_stack([matrix, np.ones(len(matrix))])
    for _ in range(steps):
        probabilities = softmax(design @ parameters)
        gradient = design.T @ (probabilities - targets) / len(matrix)
        gradient[:-1] += L2 * parameters[:-1] / len(matrix)
        parameters -= RATE * gradient
    return parameters


def loss(probabilities: np.ndarray, labels: np.ndarray) -> float:
    picked = np.clip(probabilities[np.arange(len(labels)), labels], 1e-12, 1.0)
    return float(-np.log(picked).mean())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vintages", type=Path, default=ROOT / "results" / "revenue-vintages-pit.csv")
    parser.add_argument("--cache", type=Path, default=ROOT / "results" / "bar-cache")
    parser.add_argument("--baseline", type=Path, default=ROOT / "results" / "walk-forward-baseline.json")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "distillation-test.json")
    args = parser.parse_args()

    rows, _ = prepare_rows(list(csv.DictReader(args.vintages.open())))
    arms = ("teacher", "distilled", "hard_student")
    scores = {arm: {"log_loss": [], "accuracy": [], "rows": 0} for arm in arms}
    events = {arm: [] for arm in arms}
    events["rival_equal_weight"] = []
    folds = []
    for start, end in blocks(ORIGINS):
        train = [row for row in rows if str(row["label_available"])[:10] < start]
        later = [row for row in rows if start <= str(row["label_available"])[:10] < end]
        if len(train) < 40 or len(later) < 5:
            continue
        train_matrix, train_labels = matrix_from_rows(train, tuple(FEATURES))
        test_matrix, _ = matrix_from_rows(later, tuple(FEATURES))
        labels = np.array([int(row["label_bin"]) for row in later])
        classes = tuple(sorted({int(row["label_bin"]) for row in train}))
        stats = fit_scaler(train_matrix)
        scaled_train, scaled_test = apply_scaler(train_matrix, stats), apply_scaler(test_matrix, stats)
        teacher = fit_softmax(scaled_train, train_labels, classes)
        teacher_train = predict_softmax(teacher, scaled_train)
        distilled = fit_soft_targets(scaled_train, teacher_train)
        student = fit_softmax(scaled_train, train_labels, classes)
        predictions = {"teacher": predict_softmax(teacher, scaled_test),
                       "distilled": predict_softmax(distilled, scaled_test),
                       "hard_student": predict_softmax(student, scaled_test)}
        fold = {"block": start, "test": len(later)}
        for arm in arms:
            probabilities = predictions[arm]
            scored = {"log_loss": loss(probabilities, labels),
                      "accuracy": float((probabilities.argmax(axis=1) == labels).mean()),
                      "rows": len(later)}
            scores[arm]["log_loss"].append(scored["log_loss"])
            scores[arm]["accuracy"].append(scored["accuracy"])
            scores[arm]["rows"] += scored["rows"]
            fold[arm] = round(scored["log_loss"], 4)
            for row, values in zip(later, probabilities):
                expected = sum(k * float(p) for k, p in zip(classes, values))
                conviction = (expected - 2.0) / 2.0
                if abs(conviction) > 1e-9:
                    events[arm].append({"ticker": str(row["ticker"]),
                                        "decision": str(row["label_available"])[:10],
                                        "weight": conviction, "period_end": str(row["period_end"]),
                                        "block": start})
        for row in later:                      # the rival: every event, same direction, equal weight
            events["rival_equal_weight"].append({"ticker": str(row["ticker"]),
                                                 "decision": str(row["label_available"])[:10],
                                                 "weight": 1.0, "period_end": str(row["period_end"]),
                                                 "block": start})
        folds.append(fold)

    summary = {arm: {"log_loss": statistics.mean(values["log_loss"]),
                     "accuracy": statistics.mean(values["accuracy"]), "rows": values["rows"],
                     "log_loss_by_fold": values["log_loss"]} for arm, values in scores.items()}
    sleeves = {}
    for arm, arm_events in events.items():
        daily, info = sleeve_daily(arm_events, args.cache, COSTS["base"])
        sleeves[arm] = {"events": len(arm_events), "sessions": info.get("sessions"),
                        "metrics": portfolio_metrics(daily)}
    baseline_daily = json.loads(args.baseline.read_text())["portfolio_daily"]["without_capex_inverse_vol"]
    distilled_daily, _ = sleeve_daily(events["distilled"], args.cache, COSTS["base"])
    report = {"schema": "distillation-test-v1", "scope": "development_only",
              "protocol": "docs/plan/open-work.md", "folds": folds, "summary": summary,
              "sleeves": sleeves,
              "interval_distilled_minus_baseline": month_blocked_interval(distilled_daily, baseline_daily),
              "ready_for_performance_claim": False,
              "limitations": ["development only", "the distilled targets are in-sample teacher outputs, "
                              "so the test asks whether soft targets regularise, not whether the teacher "
                              "is better than labels", "one form, one window, one seed"]}
    args.output.write_text(json.dumps(report, indent=1) + "\n")

    print("%-14s log_loss  accuracy  rows" % "arm")
    for arm in arms:
        block = summary[arm]
        print("  %-12s %.4f   %.4f   %d" % (arm, block["log_loss"], block["accuracy"], block["rows"]))
    print("sleeves (revenue leg alone): net / sharpe / dd")
    for arm, block in sleeves.items():
        metrics = block["metrics"]
        print("  %-20s events %4d net %+.2f%% sharpe %+.3f dd %+.1f%%" % (
            arm, block["events"], metrics["annual_return"] * 100, metrics["sharpe"],
            metrics["max_drawdown"] * 100))
    interval = report["interval_distilled_minus_baseline"]
    print("distilled minus the published baseline composite: point %+.4f CI [%+.4f, %+.4f] share+ %.3f" % (
        interval["point"], interval["lower"], interval["upper"], interval["share_positive"]))
    print("written", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
