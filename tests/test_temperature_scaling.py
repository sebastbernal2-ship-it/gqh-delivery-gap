#!/usr/bin/env python3
"""Contracts for the temperature fit: it shrinks overconfident logits and leaves honest ones alone."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.model import softmax  # noqa: E402
from run_gate_recalibration import fit_temperature, temperature_nll  # noqa: E402


def overconfident() -> tuple[np.ndarray, np.ndarray]:
    # the model screams class 0 and is right only half the time
    logits = np.tile(np.array([6.0, 0.0]), (100, 1))
    labels = np.array([0] * 50 + [1] * 50)
    return logits, labels


def honest() -> tuple[np.ndarray, np.ndarray]:
    # probabilities of 0.75 and the label is 0 three times in four
    logits = np.tile(np.array([np.log(3.0), 0.0]), (100, 1))
    labels = np.array([0] * 75 + [1] * 25)
    return logits, labels


def test_overconfidence_is_shrunk_by_a_temperature_above_one():
    logits, labels = overconfident()
    fit = fit_temperature(logits, labels)
    assert fit["temperature"] > 1.0
    assert fit["nll"] <= fit["nll_at_one"]               # the fit cannot be worse than no scaling


def test_an_honest_model_keeps_a_temperature_near_one():
    logits, labels = honest()
    fit = fit_temperature(logits, labels)
    assert 0.5 <= fit["temperature"] <= 2.0


def test_the_fit_is_deterministic_and_the_scores_are_ordered():
    logits, labels = overconfident()
    first, second = fit_temperature(logits, labels), fit_temperature(logits, labels)
    assert first == second
    assert temperature_nll(logits, labels, 1.0) > 0
    probabilities = softmax(logits / first["temperature"])
    assert np.allclose(probabilities.sum(axis=1), 1.0)


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} temperature contract(s) held")
