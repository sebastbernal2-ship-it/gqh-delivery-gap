import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

QUANTUM = Path(__file__).resolve().parents[1] / "quantum"
sys.path.insert(0, str(QUANTUM))
import qcbm_joint  # noqa: E402


class QcbmJointTests(unittest.TestCase):
    def test_probabilities_are_normalized(self):
        parameters = qcbm_joint.initial_parameters(3, 3, 7)
        probabilities = qcbm_joint.circuit_probabilities(parameters, 3, 3)
        self.assertEqual(len(probabilities), 8)
        self.assertAlmostEqual(sum(probabilities), 1.0, places=9)
        self.assertTrue(all(value >= 0.0 for value in probabilities))

    def test_training_improves_on_the_initial_parameters(self):
        target = list(qcbm_joint.DEFAULT_TARGET)
        fitted = qcbm_joint.fit_spsa(target, 3, 3, steps=200, seed=20261004)
        self.assertLess(fitted["best_loss"], fitted["initial_loss"])
        self.assertEqual(len(fitted["parameters"]), 9)
        self.assertGreater(fitted["evaluations"], 200)

    def test_correlated_target_differs_from_its_product_baseline(self):
        target = list(qcbm_joint.DEFAULT_TARGET)
        product = qcbm_joint.product_distribution(target, 3)
        self.assertAlmostEqual(sum(product), 1.0, places=9)
        self.assertGreater(qcbm_joint.total_variation(product, target), 0.0)
        marginals = [sum(target[i] for i in range(8) if i & (1 << q)) for q in range(3)]
        self.assertTrue(all(0.0 < value < 1.0 for value in marginals))

    def test_loader_rejects_a_distribution_that_does_not_sum_to_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "target.json"
            path.write_text(json.dumps({"states": [qcbm_joint.state_label(i, 3) for i in range(8)],
                                        "probabilities": [0.5] * 8}))
            with self.assertRaises(ValueError):
                qcbm_joint.load_target(path, 3)

    def test_receipt_is_written_without_a_performance_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "run-001"
            result = subprocess.run(
                [sys.executable, str(QUANTUM / "qcbm_joint.py"), "--backend", "numpy",
                 "--steps", "60", "--output", str(output)],
                capture_output=True, text=True, check=True)
            receipt = json.loads((output / "receipt.json").read_text())
            self.assertIs(receipt["ready_for_performance_claim"], False)
            self.assertEqual(receipt["schema"], "qcbm-joint-v1")
            self.assertIn("tv_product_target", receipt["metrics"])
            self.assertIn("tv_model_target", receipt["metrics"])
            self.assertEqual(len(receipt["model"]), 8)
            self.assertAlmostEqual(sum(receipt["model"].values()), 1.0, places=9)
            self.assertEqual(receipt["backend_metadata"]["requested"], "numpy")
            self.assertGreater(float(result.stdout.strip().split('"tv_model_target": ')[1].split(",")[0]), -1.0)

    def test_simulator_is_not_claimed_as_hardware(self):
        document = (QUANTUM / "README.md").read_text().lower()
        self.assertIn("equal-budget classical comparator", document)
        self.assertIn("entanglement alone is not evidence", document)


if __name__ == "__main__":
    unittest.main(verbosity=2)
