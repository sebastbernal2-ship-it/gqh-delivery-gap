"""A discrete time hazard, fitted with numpy and nothing else.

The object is whether a promise survives each month it is at risk. That is a logistic hazard: one row per
project month, an indicator for the month the promise first moved, and covariates known before that month.

Deliberately plain. A gradient descent logistic fit with an L2 penalty is enough for a panel of this size, it
can be read line by line, and it makes no promises about non linearity that the data cannot support. Standard
errors come from a bootstrap over rows, because a formula would assume independence that repeated project
months do not have.
"""
from __future__ import annotations

import random

import numpy as np


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -40, 40)))


def fit(x, y, l2: float = 1e-3, steps: int = 60, ridge: float = 1e-6):
    """Logistic regression by iteratively reweighted least squares.

    The first version of this used gradient descent with a step normalised by the largest gradient. It
    converged differently on a full sample and on a bootstrap resample, which produced confidence intervals
    that excluded their own point estimate. Newton steps converge in a handful of iterations and give the same
    answer for both, and a tiny ridge keeps the update well posed.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    weights = np.zeros(x.shape[1])
    for _ in range(steps):
        p = sigmoid(x @ weights)
        weight = np.clip(p * (1 - p), 1e-8, None)
        gradient = x.T @ (y - p) - l2 * weights * len(y)
        hessian = (x * weight[:, None]).T @ x + (l2 * len(y) + ridge) * np.eye(x.shape[1])
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError:
            break
        weights = weights + step
        if np.abs(step).max() < 1e-8:
            break
    p = np.clip(sigmoid(x @ weights), 1e-12, 1 - 1e-12)
    loss = float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
    return weights, loss


def predict(x, weights):
    return sigmoid(np.asarray(x, dtype=float) @ np.asarray(weights, dtype=float))


def log_likelihood(x, y, weights) -> float:
    p = np.clip(predict(x, weights), 1e-12, 1 - 1e-12)
    y = np.asarray(y, dtype=float)
    return float(np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))


def auc(x, y, weights) -> float:
    """Rank based discrimination, with average ranks for ties."""
    scores = predict(x, weights)
    y = np.asarray(y)
    positives, negatives = scores[y == 1], scores[y == 0]
    if len(positives) == 0 or len(negatives) == 0:
        return float("nan")
    combined = np.concatenate([positives, negatives])
    order = np.argsort(combined)
    ranks = np.empty(len(combined), dtype=float)
    ranks[order] = np.arange(1, len(combined) + 1)
    unique, inverse, counts = np.unique(combined, return_inverse=True, return_counts=True)
    if np.any(counts > 1):
        summed = np.zeros(len(unique))
        np.add.at(summed, inverse, ranks)
        ranks = (summed / counts)[inverse]
    rank_sum = ranks[:len(positives)].sum()
    n1, n0 = len(positives), len(negatives)
    return float((rank_sum - n1 * (n1 + 1) / 2) / (n1 * n0))


def bootstrap(x, y, trials: int = 40, seed: int = 7, l2: float = 1e-3, steps: int = 1500):
    """Coefficient spread from resampling rows, which does not assume independent rows."""
    rng = random.Random(seed)
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    out = []
    for _ in range(trials):
        index = np.array([rng.randrange(len(y)) for _ in range(len(y))])
        if y[index].sum() == 0:
            continue
        weights, _ = fit(x[index], y[index], l2=l2, steps=steps)
        out.append(weights)
    return np.array(out) if out else np.zeros((0, x.shape[1]))


def odds_ratios(coefficients, spread) -> list[dict]:
    out = []
    for index, value in enumerate(coefficients):
        low = float(np.percentile(spread[:, index], 5)) if len(spread) else float("nan")
        high = float(np.percentile(spread[:, index], 95)) if len(spread) else float("nan")
        out.append({"coefficient": float(value), "odds_ratio": float(np.exp(value)),
                    "odds_low": float(np.exp(low)), "odds_high": float(np.exp(high)),
                    "spans_one": bool(low <= 0 <= high)})
    return out
