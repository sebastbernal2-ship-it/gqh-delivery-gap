#!/usr/bin/env python3
"""The coupling layer: one joint law from calibrated marginals, under declared constraints.

The design's spine. Given one marginal distribution per dimension, a reference coupling and an
optional martingale constraint along a price dimension, this module finds a joint law that

1. matches every declared marginal, to a reported tolerance,
2. stays as close as possible to the reference coupling in KL divergence (iterative proportional
   fitting is the I-projection for that objective),
3. satisfies the martingale constraint on adjacent dimensions when a price grid is supplied,
   by an exponential tilt of each conditional slice, solved per slice by bisection.

Honest facts, stated rather than hidden:

- With only marginal constraints and a product reference, the KL-minimal coupling IS the product.
  Dependence enters only through a reference that carries it, through an extra constraint such as
  the martingale condition, or through data. A coupling layer that silently returns the product
  would be a no-op, so the reference and the constraints are explicit arguments.
- A martingale constraint and fixed marginals can be mutually inconsistent: the tower property
  requires the mean of adjacent price marginals to agree. When they do not, the solver does not
  converge and reports the residual instead of inventing a law.
- Every residual is returned. A converged flag is a measurement, never an assumption.

No world claim is made here. The first real target is the execution-risk cache, twelve marginal
heads over (3, 2, 2, 3) with the 5/15/60-second horizons, once its five whole-date roles exist.
"""
from __future__ import annotations

import numpy as np

DEFAULT_ITERATIONS = 400
DEFAULT_TOLERANCE = 1e-9


def normalize(tensor: np.ndarray) -> np.ndarray:
    total = float(tensor.sum())
    if total <= 0:
        raise ValueError("a coupling needs positive mass")
    return np.asarray(tensor, dtype=float) / total


def product_reference(marginals: list[np.ndarray]) -> np.ndarray:
    """The independence coupling of the given marginals, as a full tensor."""
    tensor = normalize(np.asarray(marginals[0], dtype=float))
    for marginal in marginals[1:]:
        tensor = np.multiply.outer(tensor, normalize(np.asarray(marginal, dtype=float)))
    return tensor


def marginal_of(tensor: np.ndarray, dimension: int) -> np.ndarray:
    axes = tuple(index for index in range(tensor.ndim) if index != dimension)
    return tensor.sum(axis=axes)


def marginal_residual(tensor: np.ndarray, marginals: list[np.ndarray]) -> float:
    return max(float(np.abs(marginal_of(tensor, index) - normalize(marginal)).max())
               for index, marginal in enumerate(marginals))


def ipf(reference: np.ndarray, marginals: list[np.ndarray],
        iterations: int = DEFAULT_ITERATIONS, tolerance: float = DEFAULT_TOLERANCE) -> dict:
    """Iterative proportional fitting: KL-minimal coupling that matches the marginals."""
    tensor = normalize(reference)
    shapes = [len(marginal) for marginal in marginals]
    if list(tensor.shape) != shapes:
        raise ValueError(f"reference shape {tensor.shape} does not match marginals {shapes}")
    for step in range(1, iterations + 1):
        for dimension, marginal in enumerate(marginals):
            target = normalize(marginal)
            current = marginal_of(tensor, dimension)
            factor = np.where(current > 0, target / np.where(current > 0, current, 1.0), 0.0)
            shape = [1] * tensor.ndim
            shape[dimension] = len(target)
            tensor = tensor * factor.reshape(shape)
        residual = marginal_residual(tensor, marginals)
        if residual <= tolerance:
            return {"tensor": normalize(tensor), "iterations": step, "marginal_residual": residual,
                    "converged": True}
    return {"tensor": normalize(tensor), "iterations": iterations,
            "marginal_residual": marginal_residual(tensor, marginals), "converged": False}


def _tilt_to_mean(probabilities: np.ndarray, values: np.ndarray, target: float,
                  bounds: tuple[float, float] = (-50.0, 50.0),
                  tolerance: float = 1e-12) -> tuple[np.ndarray, float]:
    """Exponential tilt of one distribution so its mean hits the target; returns the residual.

    The exponent is parameterised on standardised values, so the same bounds work for any unit:
    dollars, basis points or seconds. The tilt family is unchanged by that rescaling.
    """
    if probabilities.sum() <= 0:
        return probabilities, abs(target)
    base = probabilities / probabilities.sum()
    scale = float(np.std(values))
    if scale <= 0:
        return base, abs(float((base * values).sum()) - target)
    centre = float(np.mean(values))
    zed = (np.asarray(values, dtype=float) - centre) / scale
    target_z = (target - centre) / scale
    low, high = bounds
    for _ in range(200):
        middle = 0.5 * (low + high)
        weights = np.exp(np.clip(middle * zed, -700.0, 700.0))
        tilted = base * weights
        mass = tilted.sum()
        if mass <= 0 or not np.isfinite(mass):
            high = middle
            continue
        mean_z = float((tilted * zed).sum() / mass)
        if abs(mean_z - target_z) <= tolerance:
            tilted = tilted / mass
            return tilted, abs(float((tilted * values).sum()) - target)
        if mean_z < target_z:
            low = middle
        else:
            high = middle
        if high - low < 1e-14:
            break
    weights = np.exp(np.clip(0.5 * (low + high) * zed, -700.0, 700.0))
    tilted = base * weights
    mass = tilted.sum()
    if mass <= 0 or not np.isfinite(mass):
        return base, abs(float((base * values).sum()) - target)
    tilted = tilted / mass
    return tilted, abs(float((tilted * values).sum()) - target)


def martingale_residual(tensor: np.ndarray, market_values, horizons: tuple[int, int] | None = None) -> float:
    """Largest conditional-mean violation along adjacent dimensions, in price units."""
    if tensor.ndim < 2:
        return 0.0
    residual = 0.0
    pairs = [(horizons[0], horizons[1])] if horizons else list(zip(range(tensor.ndim - 1),
                                                                   range(1, tensor.ndim)))
    for earlier, later in pairs:
        values = np.asarray(market_values[earlier], dtype=float)
        later_values = np.asarray(market_values[later], dtype=float)
        axes = tuple(index for index in range(tensor.ndim) if index not in (earlier, later))
        pair = tensor.sum(axis=axes) if axes else tensor
        if earlier > later:
            pair = pair.T
        conditional_mass = pair.sum(axis=1)
        for index, mass in enumerate(conditional_mass):
            if mass <= 0:
                continue
            mean = float((pair[index] * later_values).sum() / mass)
            residual = max(residual, abs(mean - values[index]))
    return residual


def martingale_project(tensor: np.ndarray, market_values, horizons: tuple[int, int] | None = None,
                       damping: float = 1.0) -> np.ndarray:
    """One pass of conditional exponential tilts making adjacent conditional means martingales.

    `damping` below one aims partway at the target mean, which keeps the alternation with
    marginal matching stable when the target sits near the edge of the support.
    """
    if tensor.ndim < 2:
        return tensor
    tensor = tensor.copy()
    pairs = [(horizons[0], horizons[1])] if horizons else list(zip(range(tensor.ndim - 1),
                                                                   range(1, tensor.ndim)))
    for earlier, later in pairs:
        values = np.asarray(market_values[earlier], dtype=float)
        later_values = np.asarray(market_values[later], dtype=float)
        other_axes = [index for index in range(tensor.ndim) if index not in (earlier, later)]
        other_shape = [tensor.shape[index] for index in other_axes]
        for other_index in np.ndindex(*other_shape) if other_shape else [()]:
            slicer = [slice(None)] * tensor.ndim
            for axis, value in zip(other_axes, other_index):
                slicer[axis] = value
            block = tensor[tuple(slicer)]
            if earlier > later:
                block = block.T
            for row in range(block.shape[0]):
                mass = block[row].sum()
                if mass <= 0:
                    continue
                current = float((block[row] * later_values).sum() / mass)
                target = current + damping * (values[row] - current)
                tilted, _ = _tilt_to_mean(block[row], later_values, target)
                block[row] = tilted * mass
            tensor[tuple(slicer)] = block.T if earlier > later else block
    return normalize(tensor)


def divergence(tensor: np.ndarray, reference: np.ndarray) -> float:
    """KL divergence from the reference, guarding zeros."""
    left = np.asarray(tensor, dtype=float)
    right = np.asarray(reference, dtype=float)
    mask = left > 0
    if not mask.any():
        return 0.0
    return float((left[mask] * np.log(left[mask] / np.where(right[mask] > 0, right[mask], 1e-300))).sum())


def couple(marginals: list[np.ndarray], reference: np.ndarray | None = None,
           market_values=None, horizons: tuple[int, int] | None = None,
           martingale: bool = False, rounds: int = 40, iterations: int = DEFAULT_ITERATIONS,
           tolerance: float = DEFAULT_TOLERANCE) -> dict:
    """Alternate marginal matching and the martingale projection until both residuals are small."""
    if len(marginals) < 2:
        raise ValueError("a coupling needs at least two marginals")
    base = normalize(np.asarray(reference, dtype=float)) if reference is not None \
        else product_reference(marginals)
    result = ipf(base, marginals, iterations=iterations, tolerance=tolerance)
    tensor = result["tensor"]
    if not martingale:
        return {**result, "martingale_residual": None,
                "divergence_from_reference": divergence(tensor, base),
                "entanglement_kl_from_product": divergence(tensor, product_reference(marginals)),
                "entanglement_tv_from_product": 0.5 * float(np.abs(
                    tensor - product_reference(marginals)).sum()),
                "rounds": 0, "reference": "supplied" if reference is not None else "product"}
    if market_values is None:
        raise ValueError("a martingale constraint needs one price grid per dimension")
    gap = tower_gap(marginals, market_values)
    if gap > 1e-9:
        return {"tensor": None, "iterations": 0, "marginal_residual": None,
                "martingale_residual": None, "rounds": 0, "converged": False,
                "feasible": False, "tower_gap": gap,
                "reason": "adjacent price marginals disagree; no martingale coupling can match both",
                "reference": "supplied" if reference is not None else "product"}
    best = None
    for round_number in range(1, rounds + 1):
        projected = martingale_project(tensor, market_values, horizons, damping=0.5)
        result = ipf(projected, marginals, iterations=iterations, tolerance=tolerance)
        tensor = result["tensor"]
        residual = martingale_residual(tensor, market_values, horizons)
        score = max(result["marginal_residual"] / max(tolerance, 1e-12), residual / 1e-6)
        if best is None or score < best[0]:
            best = (score, tensor.copy(), round_number, result["marginal_residual"], residual)
        if residual <= 1e-6 and result["marginal_residual"] <= tolerance:
            best = (score, tensor.copy(), round_number, result["marginal_residual"], residual)
            break
    _, tensor, round_number, marginal_error, residual = best
    return {"tensor": tensor, "iterations": result["iterations"],
            "marginal_residual": marginal_error, "martingale_residual": residual,
            "rounds": round_number, "feasible": True,
            "converged": bool(residual <= 1e-6 and marginal_error <= tolerance),
            "divergence_from_reference": divergence(tensor, base),
            "entanglement_kl_from_product": divergence(tensor, product_reference(marginals)),
            "entanglement_tv_from_product": 0.5 * float(np.abs(
                tensor - product_reference(marginals)).sum()),
            "reference": "supplied" if reference is not None else "product"}

def tower_gap(marginals: list[np.ndarray], market_values) -> float:
    """The largest adjacent mean gap, in price units.

    A martingale coupling with these marginals can exist only when E[x_k] equals E[x_k+1] for
    every adjacent pair. A positive gap is a proof of infeasibility, not a solver failure.
    """
    gap = 0.0
    for index in range(len(marginals) - 1):
        earlier = float((normalize(np.asarray(marginals[index], dtype=float))
                         * np.asarray(market_values[index], dtype=float)).sum())
        later = float((normalize(np.asarray(marginals[index + 1], dtype=float))
                       * np.asarray(market_values[index + 1], dtype=float)).sum())
        gap = max(gap, abs(later - earlier))
    return gap
