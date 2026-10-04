#!/usr/bin/env python3
"""Contracts for the coupling layer: exact marginals, honest infeasibility, measured entanglement."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hpc" / "probabilistic-council"))
from coupling import (_tilt_to_mean, couple, ipf, marginal_of, marginal_residual,  # noqa: E402
                      product_reference, tower_gap)

PRICES = np.array([100.0, 110.0])
UNIFORM = np.array([0.5, 0.5])


def test_a_product_reference_is_a_no_op():
    result = ipf(product_reference([UNIFORM, UNIFORM]), [UNIFORM, UNIFORM])
    assert result["converged"] and result["marginal_residual"] <= 1e-12
    assert np.allclose(result["tensor"], np.array([[0.25, 0.25], [0.25, 0.25]]))


def test_ipf_keeps_dependence_while_matching_marginals():
    dependent = np.array([[0.4, 0.1], [0.1, 0.4]])          # already has uniform marginals
    kept = ipf(dependent, [UNIFORM, UNIFORM])
    assert np.allclose(kept["tensor"], dependent / dependent.sum())
    skewed = np.array([[0.7, 0.1], [0.1, 0.1]])             # marginals do not match
    matched = ipf(skewed, [UNIFORM, UNIFORM])
    assert matched["marginal_residual"] <= 1e-9      # the declared tolerance
    assert matched["tensor"][0, 0] > 0.25                    # the diagonal tilt survives the fit


def test_tilt_hits_the_target_mean_exactly():
    tilted, residual = _tilt_to_mean(np.array([0.5, 0.5]), PRICES, 102.5)
    assert residual <= 1e-9                           # price units, after a z-scale solve
    assert abs(float((tilted * PRICES).sum()) - 102.5) < 1e-9
    assert abs(tilted[0] - 0.75) < 1e-9


def test_a_martingale_coupling_exists_when_the_tower_property_holds():
    result = couple([UNIFORM, UNIFORM], market_values=[PRICES, PRICES], martingale=True, rounds=200)
    assert result["converged"], result
    assert result["marginal_residual"] <= 1e-9
    assert result["martingale_residual"] <= 1e-6
    # the constraint forces dependence, so the joint is far from the product of its marginals
    assert abs(result["entanglement_kl_from_product"] - math.log(2)) < 1e-3
    assert result["tensor"][0, 0] > 0.49 and result["tensor"][1, 1] > 0.49


def test_inconsistent_marginals_are_proved_infeasible_never_papered_over():
    shifted = [UNIFORM, np.array([0.9, 0.1])]
    assert abs(tower_gap(shifted, [PRICES, PRICES]) - 4.0) < 1e-12
    result = couple(shifted, market_values=[PRICES, PRICES], martingale=True, rounds=20)
    assert result["feasible"] is False and result["converged"] is False
    assert result["tensor"] is None and "disagree" in result["reason"]


def test_three_dimensions_are_supported():
    result = couple([UNIFORM, UNIFORM, UNIFORM], market_values=[PRICES] * 3,
                    martingale=True, rounds=200)
    assert result["converged"], result
    assert result["martingale_residual"] <= 1e-6
    assert result["entanglement_tv_from_product"] > 0.5
    for dimension in range(3):
        assert marginal_residual(result["tensor"], [UNIFORM] * 3) <= 1e-9
        assert np.allclose(marginal_of(result["tensor"], dimension), UNIFORM, atol=1e-9)


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} coupling contract(s) held")
