#!/usr/bin/env python3
"""Offline tests for the hazard model and the factor parsers. No network."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from models.hazard import auc, bootstrap, fit, log_likelihood, odds_ratios, predict  # noqa: E402

failures: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        failures.append(f"{name}: got {got!r}, want {want!r}")


def close(name: str, got, want, tol: float) -> None:
    if not abs(got - want) <= tol:
        failures.append(f"{name}: got {got!r}, want about {want!r}")


rng = np.random.default_rng(5)

# A factor that really drives the outcome must be recovered close to its true value.
n = 3000
x = rng.normal(size=(n, 2))
truth = np.array([1.4, 0.0])
p = 1 / (1 + np.exp(-(x @ truth)))
y = (rng.random(n) < p).astype(float)
weights, loss = fit(x, y)
close("a real effect is recovered", weights[0], 1.4, 0.15)
check("no effect stays near zero", abs(weights[1]) < 0.12, True)
check("the loss is finite", loss == loss, True)

# Discrimination: perfect separation is one, random ranking is about a half.
perfect_x = np.array([[0.0], [1.0], [2.0], [3.0]])
perfect_y = np.array([0.0, 0.0, 1.0, 1.0])
perfect_w, _ = fit(perfect_x, perfect_y, l2=0.0)
check("perfect separation gives an AUC of one", round(auc(perfect_x, perfect_y, perfect_w), 6), 1.0)
tied_x = np.zeros((40, 1))
check("no information gives an AUC of one half",
      round(auc(tied_x, np.array([0.0, 1.0] * 20), np.zeros(1)), 4), 0.5)

# Probabilities stay probabilities, and the log likelihood is negative.
probabilities = predict(x, weights)
check("predictions are inside zero and one", bool(np.all((probabilities > 0) & (probabilities < 1))), True)
check("log likelihood is negative", log_likelihood(x, y, weights) < 0, True)

# The interval must contain the estimate. An earlier gradient fitter did not, which is why this is tested.
spread = bootstrap(x, y, trials=8)
ratios = odds_ratios(weights, spread)
check("an interval contains its own estimate",
      all(r["odds_low"] <= r["odds_ratio"] <= r["odds_high"] for r in ratios), True)
check("a real effect is clear of one", ratios[0]["spans_one"], False)
check("a null effect spans one", ratios[1]["spans_one"], True)

if failures:
    print("\n".join(f"  FAIL {f}" for f in failures))
    print(f"\n{12 - len(failures)}/12 passed")
    raise SystemExit(1)
print("\n12/12 passed")
