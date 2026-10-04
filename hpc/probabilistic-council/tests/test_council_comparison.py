import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from council_comparison import (EDGES, bin_index, evaluate, load_cache, load_specialists,
                                marginal_cases, predict_all, prevalence_table)

CHECKPOINTS = Path(__file__).resolve().parents[1] / "checkpoints" / "hpg-44665003"


def make_cache(root: Path, cases: int = 12) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20261004)
    features = rng.normal(size=(cases, 16, 24)).astype(np.float32)
    targets = np.empty((cases, 3, 2, 2), dtype=np.float32)
    targets[:, :, :, 0] = rng.normal(scale=1.5, size=(cases, 3, 2))
    targets[:, :, :, 1] = np.abs(rng.normal(scale=1.0, size=(cases, 3, 2)))
    roles = np.array([0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 4, 4], dtype=np.int64)
    clocks = np.stack([np.arange(cases) * 65_000_000_000,
                       np.arange(cases) * 65_000_000_000 + 64_000_000_000], axis=1).astype(np.int64)
    for name, array in {"features": features, "targets": targets,
                        "roles": roles, "clocks": clocks}.items():
        np.save(root / f"{name}.npy", array)
    (root / "manifest.json").write_text(json.dumps({"schema_version": "test-cache"}))
    return root


def make_predictions(cases: int = 12) -> dict:
    rng = np.random.default_rng(7)
    cube = np.sort(rng.normal(scale=1.2, size=(cases, 3, 2, 2, 3)), axis=-1)
    return {"fakeA": cube,
            "fakeB": np.sort(cube + rng.normal(scale=0.4, size=cube.shape), axis=-1)}


class CouncilComparisonTests(unittest.TestCase):
    def test_load_cache_validates_shapes_and_roles(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = load_cache(make_cache(Path(tmp)))
            self.assertEqual(cache["features"].shape, (12, 16, 24))
            self.assertEqual(cache["targets"].shape, (12, 3, 2, 2))
            broken = Path(tmp) / "broken"
            make_cache(broken)
            np.save(broken / "roles.npy", np.full(12, 5, dtype=np.int64))
            with self.assertRaises(ValueError):
                load_cache(broken)

    def test_bin_index_matches_the_dataset_convention(self):
        # execution_risk_dataset.py uses bisect_right, so a value equal to an edge falls in the next bin.
        self.assertEqual(bin_index(-3.0, EDGES["terminal_loss"]), 0)
        self.assertEqual(bin_index(-2.0, EDGES["terminal_loss"]), 1)
        self.assertEqual(bin_index(-0.5, EDGES["terminal_loss"]), 2)
        self.assertEqual(bin_index(0.5, EDGES["terminal_loss"]), 3)
        self.assertEqual(bin_index(2.0, EDGES["terminal_loss"]), 4)
        self.assertEqual(bin_index(0.25, EDGES["observed_adverse"]), 0)
        self.assertEqual(bin_index(0.5, EDGES["observed_adverse"]), 1)

    def test_marginal_cases_carry_one_forecast_per_specialist(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = load_cache(make_cache(Path(tmp)))
            cases = marginal_cases(make_predictions(), cache, "terminal_loss", 1)
            self.assertEqual(len(cases), 2 * 3 * 2)
            for case in cases:
                self.assertEqual({forecast.specialist_id for forecast in case.forecasts},
                                 {"fakeA", "fakeB"})
                for forecast in case.forecasts:
                    self.assertEqual(len(forecast.outcome_space), 5)
                    self.assertAlmostEqual(sum(forecast.probabilities), 1.0, places=9)

    def test_prevalence_table_normalizes_per_marginal(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = load_cache(make_cache(Path(tmp)))
            table = prevalence_table(cache)
            self.assertEqual(len(table), 12)
            for key, distribution in table.items():
                self.assertAlmostEqual(float(distribution.sum()), 1.0, places=9)
                self.assertEqual(len(distribution), 5, key)

    def test_evaluate_reports_every_comparison_finitely(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = load_cache(make_cache(Path(tmp)))
            predictions = make_predictions()
            manifest = {"checkpoints": {"fakeA.pt": {"evaluation_pinball_bps": 1.5},
                                        "fakeB.pt": {"evaluation_pinball_bps": 1.5}}}
            report = evaluate(cache, predictions, manifest)
            for task in ("terminal_loss", "observed_adverse"):
                rows = report["per_task"][task]
                self.assertEqual(set(rows), {"council", "prevalence", "fakeA", "fakeB"})
                for values in rows.values():
                    self.assertTrue(np.isfinite(values["pinball"]))
                    self.assertTrue(np.isfinite(values["log_loss"]))
            self.assertEqual(set(report["recomputation"]), {"fakeA", "fakeB"})
            self.assertGreaterEqual(report["recomputation"]["fakeA"]["absolute_difference"], 0.0)

    def test_real_checkpoints_load_and_produce_a_case(self):
        manifest = json.loads((CHECKPOINTS / "manifest.json").read_text())
        specialists = load_specialists(CHECKPOINTS, manifest)
        self.assertEqual(len(specialists), 9)
        with tempfile.TemporaryDirectory() as tmp:
            cache = load_cache(make_cache(Path(tmp)))
            predictions = predict_all(cache, specialists, limit=1)
            for name, cube in predictions.items():
                self.assertEqual(cube.shape, (1, 3, 2, 2, 3), name)
                self.assertTrue(np.isfinite(cube).all(), name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
