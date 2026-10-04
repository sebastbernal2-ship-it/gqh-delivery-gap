#!/usr/bin/env python3
"""Does a shared issuer-state encoder with per-concept decoders beat the single-concept model?

The complex holds 7,779 measured expectations across four concepts (revenue 1,706, assets 3,009,
operating income 2,267, capex 797) but the surviving sleeve learns from the revenue labels alone.
This tests the encoder-decoder hypothesis in its honest form on this dataset size:

  A1  linear softmax,  revenue labels only            (the baseline family)
  A2  linear heads,    all concepts jointly           (multitask alone, shared linear trunk)
  A3  one hidden layer, revenue labels only           (capacity alone, no transfer)
  A4  one hidden layer, all concepts jointly          (the shared encoder with per-concept decoders)

Every arm sees the same point-in-time issuer state: for each concept, the last surprise, the mean of
the last three, the last change, days since the prior event and the prior count. A4-A3 is the transfer
effect and A4-A2 the capacity effect. Evaluation is the revenue head on the same walk-forward folds.

    python3 scripts/run_state_transfer_test.py
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
from filing_specialist.rpo_model import prepare_rows  # noqa: E402
from run_walk_forward import ORIGINS, blocks  # noqa: E402

CONCEPTS = {"revenue": "revenue-vintages-pit.csv", "assets": "assets-vintages.csv",
            "operating_income": "margins-vintages.csv", "capex": "capex-vintages-pit.csv"}
STATE_FEATURES = ("last_surprise", "mean_surprise_3", "last_change", "days_since", "prior_count")
CLASSES = (0, 1, 2, 3, 4)
HIDDEN = 24
STEPS = 900
RATE = 0.15
L2 = 1e-3


def load_panels() -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    """Prepared label rows per concept plus the raw point-in-time state updates per concept."""
    labels, updates = {}, {}
    for concept, name in CONCEPTS.items():
        vintages = list(csv.DictReader((ROOT / "results" / name).open()))
        rows, _ = prepare_rows(vintages)
        labels[concept] = rows
        stream = []
        for row in vintages:
            if (row.get("expectation_status") or "") != "measured":
                continue
            try:
                surprise = float(row["relative_surprise_pit"])
                change = float(row["change"]) / abs(float(row["previous_value"]))
            except (KeyError, TypeError, ValueError, ZeroDivisionError):
                continue
            stream.append((str(row.get("availability") or "")[:10], str(row["ticker"]).strip(),
                           surprise, change))
        updates[concept] = sorted(stream)
    return labels, updates


def state_at(updates: dict[str, list[dict]], concept: str, ticker: str, day: str) -> list[float]:
    features = []
    for other in CONCEPTS:
        history = [entry for entry in updates[other]
                   if entry[1] == ticker and entry[0] < day]
        surprises = [entry[2] for entry in history]
        changes = [entry[3] for entry in history]
        features.extend([
            surprises[-1] if surprises else 0.0,
            statistics.mean(surprises[-3:]) if surprises else 0.0,
            changes[-1] if changes else 0.0,
            float(min((np.datetime64(day) - np.datetime64(history[-1][0])).astype(int), 999))
            if history else 0.0,
            float(len(history)),
        ])
    return features


def one_hot(labels: np.ndarray, size: int = len(CLASSES)) -> np.ndarray:
    out = np.zeros((len(labels), size))
    out[np.arange(len(labels)), labels] = 1.0
    return out


def softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    weights = np.exp(shifted)
    return weights / weights.sum(axis=1, keepdims=True)


def sample_stats(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return matrix.mean(axis=0), matrix.std(axis=0) + 1e-6


def standardize(matrix: np.ndarray, stats: tuple[np.ndarray, np.ndarray]) -> np.ndarray:
    mean, deviation = stats
    return np.clip((matrix - mean) / deviation, -5.0, 5.0)


def train_arm(x_train: np.ndarray, head_rows: dict[str, tuple[np.ndarray, np.ndarray]],
              hidden: bool, width: int = HIDDEN, seed: int = 20261004) -> dict:
    """Joint training with a shared trunk and one linear decoder per concept head.

    The trunk sees every concept's rows; each decoder is trained only on its own labelled slice of the
    shared representation, which is the correct masked-label multitask setup. Every arm has the same
    trunk width, so the hidden flag alone decides whether a tanh sits inside the trunk.
    """
    rng = np.random.default_rng(seed)
    stats = sample_stats(x_train)
    x = standardize(x_train, stats)
    trunk_w = rng.normal(scale=0.05, size=(x.shape[1], width))
    trunk_b = np.zeros(width)
    names = tuple(head_rows)
    head_w = {name: rng.normal(scale=0.05, size=(width, len(CLASSES))) for name in names}
    head_b = {name: np.zeros(len(CLASSES)) for name in names}
    targets = {name: one_hot(labels) for name, (_, labels) in head_rows.items()}
    for _ in range(STEPS):
        activation = x @ trunk_w + trunk_b
        representation = np.tanh(activation) if hidden else activation
        grad_w1 = np.zeros_like(trunk_w)
        grad_b1 = np.zeros_like(trunk_b)
        for name in names:
            indices, _ = head_rows[name]
            slice_representation = representation[indices]
            probabilities = softmax(slice_representation @ head_w[name] + head_b[name])
            error = (probabilities - targets[name]) / len(indices)
            grad_w2 = slice_representation.T @ error
            grad_b2 = error.sum(axis=0)
            grad_representation = error @ head_w[name].T
            grad_activation = (grad_representation * (1.0 - slice_representation ** 2)
                               if hidden else grad_representation)
            scatter = np.zeros_like(representation)
            scatter[indices] = grad_activation
            grad_w1 += x.T @ scatter
            grad_b1 += grad_activation.sum(axis=0)
            head_w[name] -= RATE * (grad_w2 + L2 * head_w[name])
            head_b[name] -= RATE * grad_b2
        trunk_w -= RATE * (grad_w1 / len(names) + L2 * trunk_w)
        trunk_b -= RATE * (grad_b1 / len(names))
    return {"trunk_w": trunk_w, "trunk_b": trunk_b, "head_w": head_w, "head_b": head_b,
            "hidden": hidden, "stats": stats}


def predict(model: dict, x: np.ndarray, head: str) -> np.ndarray:
    x = standardize(x, model["stats"])
    activation = x @ model["trunk_w"] + model["trunk_b"]
    representation = np.tanh(activation) if model["hidden"] else activation
    return softmax(representation @ model["head_w"][head] + model["head_b"][head])



def score(probabilities: np.ndarray, labels: np.ndarray) -> dict:
    picked = np.clip(probabilities[np.arange(len(labels)), labels], 1e-12, 1.0)
    return {"rows": len(labels), "log_loss": float(-np.log(picked).mean()),
            "accuracy": float((probabilities.argmax(axis=1) == labels).mean())}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "state-transfer.json")
    args = parser.parse_args()
    labels, updates = load_panels()
    print("concept labels:", {name: len(rows) for name, rows in labels.items()})

    arms = ("A1_linear_single", "A2_linear_multi", "A3_hidden_single", "A4_hidden_multi")
    results = {arm: {"log_loss": [], "accuracy": [], "rows": 0} for arm in arms}
    folds = []
    for start, end in blocks(ORIGINS):
        train_by_concept, test_rows = {}, []
        for concept, rows in labels.items():
            train_by_concept[concept] = [row for row in rows
                                         if str(row["label_available"])[:10] < start]
            if concept == "revenue":
                test_rows = [row for row in rows
                             if start <= str(row["label_available"])[:10] < end]
        if len(test_rows) < 5 or len(train_by_concept["revenue"]) < 40:
            continue
        x_test = np.array([state_at(updates, "revenue", str(row["ticker"]),
                                    str(row["label_available"])[:10]) for row in test_rows])
        y_test = np.array([int(row["label_bin"]) for row in test_rows])
        x_train = {concept: np.array([state_at(updates, concept, str(row["ticker"]),
                                               str(row["label_available"])[:10]) for row in rows])
                   for concept, rows in train_by_concept.items()}
        y_train = {concept: np.array([int(row["label_bin"]) for row in rows])
                   for concept, rows in train_by_concept.items()}
        fold_report = {"block": start, "train": {c: len(r) for c, r in train_by_concept.items()},
                       "test": len(test_rows)}
        stacked = np.vstack([x_train[concept] for concept in y_train])
        slices, cursor = {}, 0
        for concept in y_train:
            length = len(x_train[concept])
            slices[concept] = (np.arange(cursor, cursor + length), y_train[concept])
            cursor += length
        single_rows = {"revenue": (np.arange(len(x_train["revenue"])), y_train["revenue"])}
        for arm in arms:
            if arm == "A1_linear_single":
                model = train_arm(x_train["revenue"], single_rows, hidden=False)
            elif arm == "A2_linear_multi":
                model = train_arm(stacked, slices, hidden=False)
            elif arm == "A3_hidden_single":
                model = train_arm(x_train["revenue"], single_rows, hidden=True)
            else:
                model = train_arm(stacked, slices, hidden=True)
            scored = score(predict(model, x_test, "revenue"), y_test)
            fold_report[arm] = scored
            results[arm]["log_loss"].append(scored["log_loss"])
            results[arm]["accuracy"].append(scored["accuracy"])
            results[arm]["rows"] += scored["rows"]
        folds.append(fold_report)
        print("block %s test %3d | %s" % (start, len(test_rows), " ".join(
            "%s %.4f/%.3f" % (arm.split("_")[0], fold_report[arm]["log_loss"],
                              fold_report[arm]["accuracy"]) for arm in arms)))

    # the money question: does the best arm trade better than the surviving sleeve on the same folds?
    events = []
    for fold in folds:
        pass
    for start, end in blocks(ORIGINS):
        train_by_concept, test_rows = {}, []
        for concept, rows in labels.items():
            train_by_concept[concept] = [row for row in rows
                                         if str(row["label_available"])[:10] < start]
            if concept == "revenue":
                test_rows = [row for row in rows
                             if start <= str(row["label_available"])[:10] < end]
        if len(test_rows) < 5 or len(train_by_concept["revenue"]) < 40:
            continue
        x_train = {concept: np.array([state_at(updates, concept, str(row["ticker"]),
                                               str(row["label_available"])[:10]) for row in rows])
                   for concept, rows in train_by_concept.items()}
        y_train = {concept: np.array([int(row["label_bin"]) for row in rows])
                   for concept, rows in train_by_concept.items()}
        x_test = np.array([state_at(updates, "revenue", str(row["ticker"]),
                                    str(row["label_available"])[:10]) for row in test_rows])
        stacked = np.vstack([x_train[concept] for concept in y_train])
        slices, cursor = {}, 0
        for concept in y_train:
            length = len(x_train[concept])
            slices[concept] = (np.arange(cursor, cursor + length), y_train[concept])
            cursor += length
        model = train_arm(stacked, slices, hidden=True)
        probabilities = predict(model, x_test, "revenue")
        for row, values in zip(test_rows, probabilities):
            expected = sum(k * float(p) for k, p in zip(CLASSES, values))
            conviction = (expected - 2.0) / 2.0
            if abs(conviction) < 1e-9:
                continue
            events.append({"ticker": str(row["ticker"]),
                           "decision": str(row["label_available"])[:10], "weight": conviction,
                           "period_end": str(row["period_end"]), "block": start})

    from run_sleeve_portfolio import COSTS, sleeve_daily
    from run_walk_forward import sleeve_walk_forward
    from filing_specialist.portfolio_stats import month_blocked_interval, portfolio_metrics
    cache = ROOT / "results" / "bar-cache"
    transfer_daily, transfer_info = sleeve_daily(events, cache, COSTS["base"])
    baseline_events, _, _ = sleeve_walk_forward(ROOT / "results" / "revenue-vintages-pit.csv", 1.0)
    baseline_daily, baseline_info = sleeve_daily(baseline_events, cache, COSTS["base"])
    sleeve_comparison = {
        "transfer": {"events": len(events), "sessions": transfer_info.get("sessions"),
                     "metrics": portfolio_metrics(transfer_daily)},
        "baseline": {"events": len(baseline_events), "sessions": baseline_info.get("sessions"),
                     "metrics": portfolio_metrics(baseline_daily)},
        "interval": month_blocked_interval(transfer_daily, baseline_daily)}
    print("sleeve comparison: transfer net %+.2f%% sharpe %+.3f dd %+.1f%% | baseline net %+.2f%% "
          "sharpe %+.3f dd %+.1f%% | difference share+ %.3f" % (
              sleeve_comparison["transfer"]["metrics"]["annual_return"] * 100,
              sleeve_comparison["transfer"]["metrics"]["sharpe"],
              sleeve_comparison["transfer"]["metrics"]["max_drawdown"] * 100,
              sleeve_comparison["baseline"]["metrics"]["annual_return"] * 100,
              sleeve_comparison["baseline"]["metrics"]["sharpe"],
              sleeve_comparison["baseline"]["metrics"]["max_drawdown"] * 100,
              sleeve_comparison["interval"]["share_positive"]))

    summary = {arm: {"log_loss": statistics.mean(values["log_loss"]),
                     "log_loss_by_fold": values["log_loss"],
                     "accuracy": statistics.mean(values["accuracy"]), "rows": values["rows"]}
               for arm, values in results.items()}
    report = {"schema": "state-transfer-v1", "scope": "development_only",
              "protocol": "docs/plan/open-work.md",
              "design": {"concepts": list(CONCEPTS), "state_features_per_concept": list(STATE_FEATURES),
                         "hidden": HIDDEN, "steps": STEPS, "rate": RATE, "l2": L2,
                         "matrix": {"A1": "linear, revenue labels only",
                                    "A2": "linear trunk, all concepts jointly",
                                    "A3": "one hidden layer, revenue labels only",
                                    "A4": "one hidden layer, all concepts jointly"}},
              "summary": summary, "folds": folds,
              "controlled_effects": {
                  "transfer_linear": summary["A2_linear_multi"]["log_loss"] - summary["A1_linear_single"]["log_loss"],
                  "capacity": summary["A3_hidden_single"]["log_loss"] - summary["A1_linear_single"]["log_loss"],
                  "transfer_with_capacity": summary["A4_hidden_multi"]["log_loss"] - summary["A3_hidden_single"]["log_loss"],
                  "both": summary["A4_hidden_multi"]["log_loss"] - summary["A1_linear_single"]["log_loss"]},
              "ready_for_performance_claim": False,
              "limitations": ["development only", "one hidden layer at 24 units on a few thousand rows",
                              "the state uses only own-history features, so no new information enters; "
                              "the question is whether shared training organises what is already there"],
              "sleeve_comparison": sleeve_comparison}
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    print("summary (revenue head, mean across folds):")
    for arm in arms:
        print("  %-18s log_loss %.4f accuracy %.4f rows %d" % (
            arm, summary[arm]["log_loss"], summary[arm]["accuracy"], summary[arm]["rows"]))
    print("effects:", json.dumps(report["controlled_effects"]))
    print("written", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
