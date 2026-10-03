"""GARCH risk tests require requirements-garch.txt; use only artificial data."""
import copy
import unittest
from unittest.mock import patch
import numpy as np
from arch import arch_model
from .core import attribute
from .garch import fit_garch, compare_risk
from .run import fixture


class GarchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.panel = fixture()
        cls.cutoff = cls.panel.available_at[299]
        cls.risk = fit_garch(cls.panel, cls.cutoff, ("MKT",))

    def test_positive_semidefinite_reconciled_forecasts(self):
        for h in (1, 5, 20):
            model = self.risk.at_horizon(h)
            self.assertGreaterEqual(np.linalg.eigvalsh(model.joint_cov).min(), -1e-14)
            self.assertAlmostEqual(attribute(model, [.4,.3,.2,.1])["reconciliation_error"], 0, places=14)
        self.assertGreater(abs(self.risk.correlation[-1, -2]), .001)

    def test_matches_library_univariate_forecast(self):
        series = self.panel.factors[:300, 0]
        series = series - series.mean()
        scale = np.sqrt(np.mean(series ** 2))
        fit = arch_model(series / scale, mean="Zero", vol="GARCH", p=1, q=1,
                         dist="normal", rescale=False).fit(disp="off", show_warning=False)
        expected = fit.forecast(horizon=20, reindex=False).variance.values[-1] * scale ** 2
        np.testing.assert_allclose(self.risk.forecast(20)[:,0,0], expected, rtol=1e-9)

    def test_future_outcomes_do_not_change_forecasts(self):
        altered = copy.deepcopy(self.panel)
        altered.returns[300:] *= 100
        altered.factors[300:] *= 100
        other = fit_garch(altered, self.cutoff, ("MKT",))
        np.testing.assert_array_equal(self.risk.parameters, other.parameters)
        a, f1 = compare_risk(self.risk, self.panel, [.25]*4)
        b, f2 = compare_risk(other, altered, [.25]*4)
        for name in f1:
            np.testing.assert_array_equal(f1[name], f2[name])
        self.assertNotEqual(a["scores"], b["scores"])

    def test_publication_gap_rejected(self):
        p = copy.deepcopy(self.panel)
        p.available_at = (*p.available_at[:10], p.available_at[-1], *p.available_at[11:])
        with self.assertRaisesRegex(ValueError, "complete available"):
            fit_garch(p, self.cutoff, ("MKT",))

    def test_insufficient_history(self):
        with self.assertRaisesRegex(ValueError, "100 training"):
            fit_garch(self.panel, self.panel.available_at[60], ("MKT",))

    def test_stationarity_and_mean_reversion(self):
        p = self.risk.parameters
        self.assertTrue(np.all(p[:,1:].sum(axis=1) < 1))
        steady = p[:,0] / (1 - p[:,1:].sum(axis=1))
        far = np.diag(self.risk.forecast(10000)[-1])
        np.testing.assert_allclose(far, steady, rtol=1e-6)

    def test_reject_optimizer_failure(self):
        with patch("arch.arch_model") as mocked:
            result = mocked.return_value.fit.return_value
            result.params = {"omega": .01, "alpha[1]": .1, "beta[1]": .8}
            result.convergence_flag = 9
            with self.assertRaisesRegex(ValueError, "optimizer failed"):
                fit_garch(self.panel, self.cutoff, ("MKT",))

    def test_qlike_matches_direct_portfolio_calculation(self):
        report, f = compare_risk(self.risk, self.panel, [.25]*4)
        m = self.risk.model
        e = (self.panel.returns[300:] - m.intercept - m.factor_mean @ m.beta) @ np.full(4,.25)
        h = f["CCC_GARCH11"]
        self.assertAlmostEqual(report["scores"]["CCC_GARCH11"]["mean_qlike"], np.mean(np.log(h)+e*e/h))


if __name__ == "__main__":
    unittest.main()
