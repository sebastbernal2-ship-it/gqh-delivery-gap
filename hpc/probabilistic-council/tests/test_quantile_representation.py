import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from council.distributions import (QuantileForecast, SpecialistForecast, assert_compatible,
                                   bin_labels, from_categorical, probabilities_to_quantiles,
                                   quantiles_to_probabilities, to_categorical)
from council.risk_adapter import QUANTILE_LEVELS, risk_forecasts

STAMP = {"context": "btc:2026-10-04", "forecast_time": "2026-10-04T09:00:00+00:00",
         "valid_until": "2026-10-04T10:00:00+00:00", "information_cutoff": "2026-10-04T08:59:00+00:00",
         "model_version": "risk-v1", "data_version": "capture-20261004"}


def normal_bins(edges):
    def phi(value):
        return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))
    boundaries = [0.0] + [phi(edge) for edge in edges] + [1.0]
    return [high - low for low, high in zip(boundaries, boundaries[1:])]


class QuantileRepresentationTests(unittest.TestCase):
    def test_conversion_against_a_hand_computed_case(self):
        levels, values, edges = (0.1, 0.5, 0.9), (-2.0, 0.0, 2.0), (-1.0, 1.0)
        probabilities = quantiles_to_probabilities(levels, values, edges)
        self.assertAlmostEqual(probabilities[0], 0.3, places=9)
        self.assertAlmostEqual(probabilities[1], 0.4, places=9)
        self.assertAlmostEqual(probabilities[2], 0.3, places=9)

    def test_round_trip_preserves_the_bulk(self):
        edges = (-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5)
        original = normal_bins(edges)
        levels = (0.1, 0.25, 0.5, 0.75, 0.9)
        restored = quantiles_to_probabilities(levels, probabilities_to_quantiles(original, edges, levels), edges)
        for index in (2, 3, 4, 5):
            self.assertLess(abs(original[index] - restored[index]), 0.02, f"bin {index}")

    def test_round_trip_tail_error_is_bounded_and_measured(self):
        """The linear tail extension is an assumption, not data. On a standard normal
        discretization the round trip measures 0.057 total variation, with at most 0.029 in the
        two bins that hold the tails. These bounds document the approximation."""
        edges = (-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5)
        original = normal_bins(edges)
        levels = (0.1, 0.25, 0.5, 0.75, 0.9)
        restored = quantiles_to_probabilities(levels, probabilities_to_quantiles(original, edges, levels), edges)
        distance = 0.5 * sum(abs(a - b) for a, b in zip(original, restored))
        self.assertLess(distance, 0.08, f"round trip total variation {distance}")
        outer = max(abs(original[index] - restored[index]) for index in (0, 1, 6, 7))
        self.assertLess(outer, 0.04, f"outer bin error {outer}")

    def test_quantiles_beyond_the_edges_fill_the_outer_bins(self):
        probabilities = quantiles_to_probabilities((0.1, 0.5, 0.9), (-10.0, 0.0, 10.0), (-1.0, 1.0))
        self.assertGreater(probabilities[0], 0.4)
        self.assertGreater(probabilities[2], 0.4)
        self.assertAlmostEqual(sum(probabilities), 1.0, places=9)

    def test_nonmonotone_values_are_rejected(self):
        with self.assertRaises(ValueError):
            quantiles_to_probabilities((0.1, 0.5, 0.9), (-2.0, 0.0, -1.0), (-1.0, 1.0))
        with self.assertRaises(ValueError):
            quantiles_to_probabilities((0.5, 0.5), (0.0, 1.0), (-1.0, 1.0))

    def test_labels_cover_every_bin(self):
        labels = bin_labels((-1.0, 1.0))
        self.assertEqual(len(labels), 3)
        self.assertEqual(labels, ("<-1", "[-1,1)", ">=1"))

    def test_quantile_forecast_carries_the_shared_clock_contract(self):
        forecast = QuantileForecast(specialist_id="risk:5s:buy:terminal_loss",
                                    levels=(0.1, 0.5, 0.9), values=(-2.0, 0.0, 2.0), unit="bps",
                                    **STAMP)
        self.assertEqual(forecast.unit, "bps")
        with self.assertRaises(ValueError):
            QuantileForecast(specialist_id="risk:5s:buy:terminal_loss", levels=(0.1, 0.5, 0.9),
                             values=(-2.0, 0.0, 2.0), unit="",
                             **{**STAMP, "forecast_time": "2026-10-04T09:00:00"})

    def test_from_categorical_keeps_the_median_inside_the_middle_bin(self):
        original = SpecialistForecast(specialist_id="specialist", outcome_space=bin_labels((-1.0, 1.0)),
                                      probabilities=(0.2, 0.6, 0.2), **STAMP)
        quantiles = from_categorical(original, (-1.0, 1.0), (0.1, 0.5, 0.9), "bps")
        self.assertLessEqual(quantiles.values[0], -1.0)
        self.assertGreaterEqual(quantiles.values[2], 1.0)
        self.assertAlmostEqual(quantiles.values[1], 0.0, places=6)


class RiskAdapterTests(unittest.TestCase):
    def prediction(self):
        cube = []
        for horizon in (5, 15, 60):
            sides = []
            for terminal in ((-2.0, 0.0, 2.0), (-1.5, 0.5, 2.5)):
                adverse = (0.25, 0.75, 1.75)
                sides.append([terminal, adverse])
            cube.append(sides)
        return cube

    def test_twelve_marginals_convert_and_stay_compatible(self):
        forecasts = risk_forecasts(self.prediction(), {"terminal_loss": (-1.0, 1.0),
                                                       "observed_adverse": (0.5, 1.0)},
                                   **STAMP)
        self.assertEqual(len(forecasts), 12)
        identifiers = {forecast.specialist_id for forecast in forecasts}
        self.assertEqual(len(identifiers), 12)
        self.assertIn("risk:5s:buy:terminal_loss", identifiers)
        for forecast in forecasts:
            self.assertAlmostEqual(sum(forecast.probabilities), 1.0, places=9)
            self.assertEqual(len(forecast.outcome_space), len(forecast.probabilities))
            self.assertEqual(forecast.model_version, "risk-v1")
        terminal = [forecast for forecast in forecasts
                    if forecast.specialist_id.endswith("terminal_loss")]
        assert_compatible(tuple(terminal))
        self.assertEqual(len(terminal[0].outcome_space), 3)

    def test_shape_and_finiteness_are_enforced(self):
        with self.assertRaises(ValueError):
            risk_forecasts([[[]]], {"terminal_loss": (-1.0, 1.0),
                                    "observed_adverse": (0.5, 1.0)}, **STAMP)
        broken = self.prediction()
        broken[0][0][0] = (0.0, float("nan"), 1.0)
        with self.assertRaises(ValueError):
            risk_forecasts(broken, {"terminal_loss": (-1.0, 1.0),
                                    "observed_adverse": (0.5, 1.0)}, **STAMP)
        with self.assertRaises(ValueError):
            risk_forecasts(self.prediction(), {"terminal_loss": (-1.0, 1.0)}, **STAMP)

    def test_quantile_levels_match_the_training_contract(self):
        self.assertEqual(QUANTILE_LEVELS, (0.1, 0.5, 0.9))


if __name__ == "__main__":
    unittest.main(verbosity=2)
