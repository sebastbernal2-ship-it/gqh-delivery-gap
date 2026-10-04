"""Small multinomial baseline and proper scores for the filing specialist.

Fitted on typed rows from `panel.py`: standardisation and imputation use training rows only,
the split is chronological, and the prevalence reference is always reported next to the fit.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

EPSILON = 1e-12


@dataclass(frozen=True)
class Prepared:
    matrix: np.ndarray
    labels: np.ndarray
    classes: tuple[int, ...]


def matrix_from_rows(rows: list[dict], features: tuple[str, ...]) -> tuple[np.ndarray, np.ndarray]:
    values = np.array([[fill_missing(row.get(name)) for name in features] for row in rows],
                      dtype=float)
    labels = np.array([int(row["label_bin"]) for row in rows], dtype=int)
    return values, labels


def fill_missing(value) -> float:
    """CSV round trips empty strings; an empty or unparseable value is missing, never zero."""
    if value is None:
        return float("nan")
    if isinstance(value, str):
        value = value.strip()
        if value == "":
            return float("nan")
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def fit_scaler(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Training-only median imputation and standardisation."""
    medians = np.nanmedian(matrix, axis=0)
    medians = np.where(np.isfinite(medians), medians, 0.0)
    filled = np.where(np.isnan(matrix), medians, matrix)
    mean = filled.mean(axis=0)
    scale = filled.std(axis=0)
    scale = np.where(scale > 1e-12, scale, 1.0)
    return medians, mean, scale


def apply_scaler(matrix: np.ndarray, stats: tuple[np.ndarray, np.ndarray, np.ndarray]) -> np.ndarray:
    medians, mean, scale = stats
    return (np.where(np.isnan(matrix), medians, matrix) - mean) / scale


def softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    weights = np.exp(shifted)
    return weights / weights.sum(axis=1, keepdims=True)


def fit_softmax(matrix: np.ndarray, labels: np.ndarray, classes: tuple[int, ...],
                steps: int = 600, learning_rate: float = 0.5, l2: float = 1.0,
                seed: int = 20261004) -> np.ndarray:
    """Full-batch multinomial logistic regression with an L2 penalty on the weights."""
    rng = np.random.default_rng(seed)
    parameters = rng.normal(scale=0.01, size=(matrix.shape[1] + 1, len(classes)))
    index = {label: position for position, label in enumerate(classes)}
    targets = np.zeros((len(labels), len(classes)))
    for row, label in enumerate(labels):
        targets[row, index[int(label)]] = 1.0
    design = np.column_stack([matrix, np.ones(len(matrix))])
    for _ in range(steps):
        probabilities = softmax(design @ parameters)
        gradient = design.T @ (probabilities - targets) / len(matrix)
        gradient[:-1] += l2 * parameters[:-1] / len(matrix)
        parameters -= learning_rate * gradient
    return parameters


def predict_softmax(parameters: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    design = np.column_stack([matrix, np.ones(len(matrix))])
    return softmax(design @ parameters)


def prevalence(rows: list[dict], classes: tuple[int, ...]) -> np.ndarray:
    counts = np.ones(len(classes))
    index = {label: position for position, label in enumerate(classes)}
    for row in rows:
        counts[index[int(row["label_bin"])]] += 1.0
    return counts / counts.sum()


def score(probabilities: np.ndarray, labels: np.ndarray, classes: tuple[int, ...]) -> dict:
    index = {label: position for position, label in enumerate(classes)}
    positions = np.array([index[int(label)] for label in labels])
    chosen = probabilities[np.arange(len(labels)), positions]
    one_hot = np.zeros_like(probabilities)
    one_hot[np.arange(len(labels)), positions] = 1.0
    return {
        "rows": int(len(labels)),
        "log_loss": float(-np.mean(np.log(np.maximum(EPSILON, chosen)))),
        "brier": float(np.mean(np.sum((probabilities - one_hot) ** 2, axis=1))),
        "accuracy": float(np.mean(np.argmax(probabilities, axis=1) == positions)),
        "class_support": {int(label): int((labels == label).sum()) for label in classes},
    }


def chronological_split(rows: list[dict], fraction: float = 0.7) -> tuple[list[dict], list[dict]]:
    """Split by label time, never across a shared timestamp."""
    ordered = sorted(rows, key=lambda row: row["label_available"])
    cut = max(1, min(len(ordered) - 1, int(round(len(ordered) * fraction))))
    while cut < len(ordered) - 1 and ordered[cut]["label_available"] == ordered[cut - 1]["label_available"]:
        cut += 1
    return ordered[:cut], ordered[cut:]


def compare(rows: list[dict], features: tuple[str, ...], fraction: float = 0.7) -> dict:
    """Prevalence reference versus the fitted baseline on the same chronological split."""
    train, test = chronological_split(rows, fraction)
    if not train or not test:
        raise ValueError("both splits must be nonempty")
    classes = tuple(sorted({int(row["label_bin"]) for row in train}))
    prior = prevalence(train, classes)
    train_matrix, train_labels = matrix_from_rows(train, features)
    test_matrix, test_labels = matrix_from_rows(test, features)
    stats = fit_scaler(train_matrix)
    parameters = fit_softmax(apply_scaler(train_matrix, stats), train_labels, classes)
    return {
        "split": {"train_rows": len(train), "test_rows": len(test),
                  "train_through": max(row["label_available"] for row in train),
                  "test_from": min(row["label_available"] for row in test),
                  "classes": list(classes)},
        "features": list(features),
        "prevalence": score(np.tile(prior, (len(test), 1)), test_labels, classes),
        "softmax": score(predict_softmax(parameters, apply_scaler(test_matrix, stats)),
                         test_labels, classes),
        "training_prevalence": {int(label): float(value) for label, value in zip(classes, prior)},
        "coefficients": parameters.tolist(),
    }
