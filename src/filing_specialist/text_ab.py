"""Does document text add anything beyond filing metadata, on the same rows and split?

Three models on one chronological split: metadata only, text embedding only, and both. The text
embedding is reduced by training-only PCA, because a few hundred dimensions on fifty-eight
training rows would otherwise be pure overfitting. The reduction is declared and fitted on
training rows only.
"""
from __future__ import annotations

import numpy as np

from .model import (apply_scaler, chronological_split, fit_scaler, fit_softmax, fill_missing,
                    predict_softmax, prevalence, score)

DEFAULT_COMPONENTS = 8


def pca_fit(matrix: np.ndarray, components: int = DEFAULT_COMPONENTS) -> tuple[np.ndarray, np.ndarray]:
    """Training-only PCA via SVD; returns (mean, projection matrix) with rows as components."""
    center = matrix.mean(axis=0)
    _, _, right = np.linalg.svd(matrix - center, full_matrices=False)
    return center, right[:components]


def pca_apply(matrix: np.ndarray, center: np.ndarray, projection: np.ndarray) -> np.ndarray:
    return (matrix - center) @ projection.T


def _metadata_matrix(rows: list[dict], features: tuple[str, ...]) -> np.ndarray:
    return np.array([[fill_missing(row.get(name)) for name in features] for row in rows], dtype=float)


def _fit_score(train_matrix: np.ndarray, train_labels: np.ndarray, test_matrix: np.ndarray,
               test_labels: np.ndarray, classes: tuple[int, ...], steps: int = 600,
               seed: int = 20261004) -> dict:
    stats = fit_scaler(train_matrix)
    parameters = fit_softmax(apply_scaler(train_matrix, stats), train_labels, classes,
                             steps=steps, seed=seed)
    return score(predict_softmax(parameters, apply_scaler(test_matrix, stats)), test_labels, classes)


def three_way(rows: list[dict], metadata_features: tuple[str, ...], embeddings: np.ndarray,
              fraction: float = 0.7, components: int = DEFAULT_COMPONENTS,
              steps: int = 600, seed: int = 20261004) -> dict:
    """Compare metadata only, text only and both on one chronological split."""
    if len(rows) != len(embeddings):
        raise ValueError("one embedding row per panel row is required")
    train_rows, test_rows = chronological_split(rows, fraction)
    train_index = [rows.index(row) for row in train_rows]
    test_index = [rows.index(row) for row in test_rows]
    train_labels = np.array([int(row["label_bin"]) for row in train_rows], dtype=int)
    test_labels = np.array([int(row["label_bin"]) for row in test_rows], dtype=int)
    classes = tuple(sorted(set(int(label) for label in train_labels)))
    prior = prevalence(train_rows, classes)

    metadata = _metadata_matrix(rows, metadata_features)
    text = np.asarray(embeddings, dtype=float)
    center, projection = pca_fit(text[train_index], components)
    reduced = pca_apply(text, center, projection)

    both = np.column_stack([metadata, reduced])
    return {
        "split": {"train_rows": len(train_rows), "test_rows": len(test_rows),
                  "train_through": max(row["label_available"] for row in train_rows),
                  "test_from": min(row["label_available"] for row in test_rows),
                  "classes": list(classes)},
        "components": components,
        "prevalence": score(np.tile(prior, (len(test_labels), 1)), test_labels, classes),
        "metadata_only": _fit_score(metadata[train_index], train_labels, metadata[test_index],
                                    test_labels, classes, steps, seed),
        "text_only": _fit_score(reduced[train_index], train_labels, reduced[test_index],
                                test_labels, classes, steps, seed),
        "metadata_and_text": _fit_score(both[train_index], train_labels, both[test_index],
                                        test_labels, classes, steps, seed),
    }
