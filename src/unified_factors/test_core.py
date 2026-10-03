"""Numerical and information-boundary regression tests; no network or production data."""
import copy
import unittest
from dataclasses import replace
import numpy as np
from .core import fit, attribute, covariance, overlap, hedge_projection, evaluate, BASELINES
from .run import fixture


class ExposureTests(unittest.TestCase):
    def setUp(self):
        self.panel = fixture()
        self.cutoff = self.panel.available_at[299]
        self.ids = BASELINES["FF5_MOM"]

    def test_covariance_reconstructs_assets(self):
        m = fit(self.panel, self.cutoff, self.ids)
        w = np.array([.8, -.3, .2, .1])
        result = attribute(m, w)
        expected = w @ np.cov(self.panel.returns[:300], rowvar=False) @ w
        self.assertAlmostEqual(result["variance"], expected, places=14)
        self.assertAlmostEqual(result["reconciliation_error"], 0, places=14)

    def test_ewma_cross_terms_retained(self):
        m = fit(self.panel, self.cutoff, self.ids, covariance_method="ewma")
        w = np.array([.4,.3,.2,.1])
        r = attribute(m, w)
        expected = w @ covariance(self.panel.returns[:300], "ewma") @ w
        self.assertAlmostEqual(r["variance"], expected, places=14)
        self.assertGreater(abs(r["factor_residual_cross_variance"]), 1e-12)

    def test_future_changes_do_not_change_fit(self):
        altered = copy.deepcopy(self.panel)
        altered.returns[300:] *= 10000
        altered.factors[300:] *= -9000
        a, b = fit(self.panel, self.cutoff, self.ids), fit(altered, self.cutoff, self.ids)
        np.testing.assert_array_equal(a.beta, b.beta)
        np.testing.assert_array_equal(a.joint_cov, b.joint_cov)

    def test_delayed_publication_excluded(self):
        p = copy.deepcopy(self.panel)
        dates = list(p.available_at)
        dates[10] = p.available_at[-1]
        p.available_at = tuple(dates)
        self.assertEqual(fit(p, self.cutoff, self.ids).diagnostics["training_rows"], 299)

    def test_alias_rejected(self):
        p = copy.deepcopy(self.panel)
        p.specs = (*p.specs[:-1], replace(p.specs[-1], canonical_id="MKT"))
        with self.assertRaisesRegex(ValueError, "aliases"):
            fit(p, self.cutoff, self.ids)

    def test_collinear_attribution_rejected(self):
        p = copy.deepcopy(self.panel)
        p.factors[:, 1] = p.factors[:, 0] * 2
        with self.assertRaisesRegex(ValueError, "rank-deficient"):
            fit(p, self.cutoff, self.ids)

    def test_correlated_not_independent_residuals(self):
        m = fit(self.panel, self.cutoff, self.ids)
        r = attribute(m, [.4,.3,.2,.1])
        self.assertGreater(r["residual_off_diagonal_effect"], 0)
        self.assertGreater(r["residual_leading_eigenvalue_share"], .5)

    def test_negative_contribution_is_valid(self):
        m = fit(self.panel, self.cutoff, self.ids)
        k = len(m.specs)
        m.beta[:] = 0
        m.joint_cov[:] = 0
        m.joint_cov[k:, k:] = np.array([[1,.8,0,0],[.8,1,0,0],[0,0,1,0],[0,0,0,1]])
        r = attribute(m, [1,-.2,0,0])
        self.assertAlmostEqual(r["variance"], .72)
        self.assertAlmostEqual(r["asset_residual_variance_contributions"][m.assets[1]], -.12)
        self.assertAlmostEqual(r["reconciliation_error"], 0)

    def test_schema_and_time_boundary(self):
        m = fit(self.panel, self.cutoff, self.ids)
        with self.assertRaises(ValueError):
            evaluate(m, self.panel)
        later = self.panel.subset(np.arange(420) >= 300)
        later.currency = "EUR"
        with self.assertRaises(ValueError):
            evaluate(m, later)

    def test_sealed_refused(self):
        self.panel.study_role = "sealed"
        with self.assertRaises(ValueError):
            fit(self.panel, self.cutoff, self.ids)

    def test_missing_and_bad_clock_refused(self):
        p = copy.deepcopy(self.panel)
        p.factors[1, 0] = np.nan
        with self.assertRaises(ValueError):
            p.validate()
        p = copy.deepcopy(self.panel)
        p.times = ("2020-01-01", *p.times[1:])
        with self.assertRaises(ValueError):
            p.validate()

    def test_hedgeable_not_same_as_systematic(self):
        r = hedge_projection([1,2], [[1], [0]])
        np.testing.assert_allclose(r["unspanned_exposure"], [0,2])
        self.assertFalse(r["executable"])

    def test_factor_permutation_preserves_portfolio_risk(self):
        a = fit(self.panel, self.cutoff, self.ids)
        b = fit(self.panel, self.cutoff, tuple(reversed(self.ids)))
        self.assertAlmostEqual(attribute(a, [.25]*4)["variance"], attribute(b, [.25]*4)["variance"], places=14)

    def test_numerical_overlap_diagnostics(self):
        x = self.panel.factors.copy()
        x[:, 1] = x[:, 0] + .01 * x[:, 1]
        r = overlap(x, self.panel.specs)
        self.assertGreater(r["vif"]["MKT"], 100)
        self.assertTrue(r["correlated_pairs"])


if __name__ == "__main__":
    unittest.main()
