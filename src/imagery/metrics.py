"""Small offline metrics for reviewed imagery labels."""
from __future__ import annotations


def classification_metrics(actual: list[int], predicted: list[int]) -> dict[str, float]:
    if len(actual) != len(predicted) or not actual:
        raise ValueError("actual and predicted labels must have equal nonzero length")
    if any(value not in (0, 1) for value in actual + predicted):
        raise ValueError("labels must be binary")
    tp = sum(a == p == 1 for a, p in zip(actual, predicted))
    fp = sum(a == 0 and p == 1 for a, p in zip(actual, predicted))
    fn = sum(a == 1 and p == 0 for a, p in zip(actual, predicted))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"n": len(actual), "accuracy": sum(a == p for a, p in zip(actual, predicted)) / len(actual),
            "precision": precision, "recall": recall}
