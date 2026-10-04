#!/usr/bin/env python3
"""Contracts for soft-target training: it learns the teacher, and it differs from label training."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.model import softmax  # noqa: E402
from run_distillation_test import fit_soft_targets  # noqa: E402


def test_soft_target_fit_reproduces_a_learnable_teacher():
    rng = np.random.default_rng(3)
    features = rng.normal(size=(300, 4))
    truth = rng.normal(size=(5, 3))
    teacher = softmax(np.column_stack([features, np.ones(300)]) @ truth)
    student = fit_soft_targets(features, teacher)
    fitted = softmax(np.column_stack([features, np.ones(300)]) @ student)
    assert float(np.abs(fitted - teacher).mean()) < 0.02      # the soft target is learnable


def test_soft_targets_differ_from_one_hot_targets():
    rng = np.random.default_rng(5)
    features = rng.normal(size=(200, 3))
    teacher = np.tile(np.array([0.6, 0.3, 0.1]), (200, 1))    # deliberately soft and smooth
    soft = fit_soft_targets(features, teacher)
    labels = np.array([0] * 200)                              # the hard reading of the same data
    from filing_specialist.model import fit_softmax
    hard = fit_softmax(features, labels, (0, 1, 2))
    soft_probabilities = softmax(np.column_stack([features, np.ones(200)]) @ soft)
    hard_probabilities = softmax(np.column_stack([features, np.ones(200)]) @ hard)
    assert float(soft_probabilities.std()) < float(soft_probabilities.mean())    # smooth, not peaked
    assert float(hard_probabilities.max(axis=1).mean()) > float(soft_probabilities.max(axis=1).mean())


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} distillation contract(s) held")
