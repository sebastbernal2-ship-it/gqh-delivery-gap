#!/usr/bin/env python3
"""Contracts for the shared-state transfer test: point-in-time state, real transfer, determinism."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from run_state_transfer_test import CLASSES, predict, state_at, train_arm  # noqa: E402


def test_state_reads_only_strictly_prior_observations():
    updates = {"revenue": [("2020-01-01", "T", 0.5, 0.1), ("2020-04-01", "T", -0.5, -0.1)],
               "assets": [], "operating_income": [], "capex": []}
    before_second = state_at(updates, "revenue", "T", "2020-04-01")
    after_second = state_at(updates, "revenue", "T", "2020-07-01")
    revenue_block = slice(0, 5)                       # last, mean3, last change, days, count
    assert before_second[revenue_block] == [0.5, 0.5, 0.1, 91.0, 1.0]
    assert after_second[revenue_block] == [-0.5, 0.0, -0.1, 91.0, 2.0]


def test_shared_training_transfers_when_one_head_has_more_labels():
    rng = np.random.default_rng(7)
    size = 900
    latent = rng.normal(size=size)
    edges = np.quantile(latent, [0.2, 0.4, 0.6, 0.8])
    labels = np.digitize(latent + rng.normal(size=size), edges)        # the same noisy rule for both
    features = np.column_stack([latent + rng.normal(scale=0.5, size=size), rng.normal(size=size)])
    test_latent = rng.normal(size=300)
    test_labels = np.digitize(test_latent + rng.normal(size=300), edges)
    test_features = np.column_stack([test_latent + rng.normal(scale=0.5, size=300),
                                     rng.normal(size=300)])
    scarce = 60
    single = train_arm(features[:scarce], {"revenue": (np.arange(scarce), labels[:scarce])},
                       hidden=True)
    stacked = features
    joint = train_arm(stacked, {"revenue": (np.arange(scarce), labels[:scarce]),
                                "other": (np.arange(scarce, size), labels[scarce:])}, hidden=True)
    def loss(model):
        probabilities = predict(model, test_features, "revenue")
        return float(-np.log(np.clip(probabilities[np.arange(len(test_labels)), test_labels],
                                     1e-12, 1.0)).mean())
    assert loss(joint) < loss(single)                  # the shared trunk carries the plentiful head


def test_training_is_deterministic():
    rng = np.random.default_rng(11)
    features = rng.normal(size=(200, 4))
    labels = rng.integers(0, len(CLASSES), size=200)
    rows = {"revenue": (np.arange(200), labels)}
    first = train_arm(features, rows, hidden=True)
    second = train_arm(features, rows, hidden=True)
    assert np.allclose(first["trunk_w"], second["trunk_w"])
    assert np.allclose(predict(first, features, "revenue"), predict(second, features, "revenue"))


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} transfer contract(s) held")
