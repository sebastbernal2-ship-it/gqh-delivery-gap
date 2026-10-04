#!/usr/bin/env python3
"""Contracts for the metadata-versus-text comparison: split integrity and finite three-way scores."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.text_ab import pca_apply, pca_fit, three_way  # noqa: E402


def rows(count: int = 40, features: int = 3) -> list[dict]:
    out = []
    for index in range(count):
        record = {"label_available": f"2024-{index // 28 + 1:02d}-{index % 28 + 1:02d}T12:00:00+00:00",
                  "label_bin": index % 5}
        for position in range(features):
            record[f"f{position}"] = float((index * (position + 3)) % 11)
        out.append(record)
    return out


def test_pca_shapes_and_dominant_direction():
    rng = np.random.default_rng(3)
    base = rng.normal(size=(30, 1)) @ np.array([[1.0, -2.0, 0.5, 0.0]])
    matrix = base + 0.01 * rng.normal(size=(30, 4))
    center, projection = pca_fit(matrix, components=2)
    self_shapes = (center.shape, projection.shape)
    assert self_shapes == ((4,), (2, 4)), self_shapes
    reduced = pca_apply(matrix, center, projection)
    assert reduced.shape == (30, 2)
    # the first component must align with the planted direction
    planted = np.array([[1.0, -2.0, 0.5, 0.0]])
    planted = planted / np.linalg.norm(planted)
    assert abs(float(projection[0] @ planted[0])) > 0.9


def test_three_way_uses_one_chronological_split_and_returns_finite_scores():
    panel = rows(40)
    embeddings = np.random.default_rng(7).normal(size=(40, 6))
    report = three_way(panel, ("f0", "f1", "f2"), embeddings, fraction=0.7, components=3, steps=100)
    assert report["split"]["train_rows"] + report["split"]["test_rows"] == 40
    assert report["split"]["train_through"] < report["split"]["test_from"]
    for name in ("prevalence", "metadata_only", "text_only", "metadata_and_text"):
        assert report[name]["rows"] == report["split"]["test_rows"], name
        assert report[name]["log_loss"] > 0.0, name
        assert 0.0 <= report[name]["accuracy"] <= 1.0, name


def test_row_and_embedding_counts_must_match():
    try:
        three_way(rows(10), ("f0",), np.zeros((9, 4)), fraction=0.5, components=2, steps=10)
    except ValueError:
        pass
    else:
        raise AssertionError("a mismatch must be refused")


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} text A/B contract(s) held")
