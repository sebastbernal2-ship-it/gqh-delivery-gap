"""Point-in-time and experiment integration regressions for the synthetic specialist lab."""
from dataclasses import replace
from datetime import timedelta
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from specialist_lab import FEATURES, PARTITIONS, Standardizer, VIEWS, choice, run, split_rows, synthetic_rows


class SpecialistLabTests(unittest.TestCase):
    def setUp(self):
        self.rows = synthetic_rows(100, 7)

    def test_split_has_disjoint_chronological_roles(self):
        parts = split_rows(self.rows)
        self.assertEqual([len(parts[p]) for p in PARTITIONS], [50, 15, 15, 10, 10])
        self.assertEqual(sum(len({r.case_id for r in block}) for block in parts.values()), 100)

    def test_rejects_unavailable_feature(self):
        self.rows[0] = replace(self.rows[0], available_at=self.rows[0].decision_at + timedelta(seconds=1))
        with self.assertRaisesRegex(ValueError, "availability"):
            split_rows(self.rows)

    def test_rejects_labels_that_cross_next_fit_boundary(self):
        self.rows[49] = replace(self.rows[49], label_available_at=self.rows[50].decision_at)
        with self.assertRaisesRegex(ValueError, "mature"):
            split_rows(self.rows)

    def test_rejects_episode_crossing_partitions(self):
        self.rows[50] = replace(self.rows[50], episode_id=self.rows[49].episode_id)
        with self.assertRaisesRegex(ValueError, "episode"):
            split_rows(self.rows)

    def test_rejects_duplicates_unsorted_and_mixed_horizons(self):
        cases = [self.rows[:99] + [self.rows[0]],
                 [self.rows[1], self.rows[0]] + self.rows[2:],
                 [replace(self.rows[0], label_end=self.rows[0].label_end - timedelta(seconds=1))] + self.rows[1:]]
        for rows in cases:
            with self.subTest(rows=rows[0].case_id), self.assertRaises(ValueError):
                split_rows(rows)

    def test_future_label_and_identity_never_enter_feature_text(self):
        scaler = Standardizer.fit(self.rows[:50])
        row = self.rows[0]
        changed = replace(row, return_bps=12345, case_id="LEAK_MARKER", episode_id="FUTURE")
        for view in VIEWS.values():
            self.assertEqual(choice(row, view, scaler).context, choice(changed, view, scaler).context)
            for i, name in enumerate(FEATURES):
                self.assertEqual(name in choice(row, view, scaler).context, i in view)

    def test_scaler_uses_only_training_and_labels_do_not_affect_it(self):
        parts = split_rows(self.rows)
        scaler = Standardizer.fit(parts["training"])
        changed_labels = [replace(r, return_bps=100) for r in parts["training"]]
        self.assertEqual(scaler, Standardizer.fit(changed_labels))
        extreme = replace(self.rows[-1], features=(1e8,) * len(FEATURES))
        self.assertEqual(scaler, Standardizer.fit(split_rows(self.rows[:-1] + [extreme])["training"]))
        self.assertNotEqual(scaler, Standardizer.fit(self.rows[:-1] + [extreme]))

    def test_rejects_nonfinite_and_mixed_target(self):
        for row in (replace(self.rows[0], features=(math.nan,) * 6),
                    replace(self.rows[0], target_id="different"),
                    replace(self.rows[0], return_bps=math.inf)):
            with self.subTest(target=row.target_id), self.assertRaises(ValueError):
                row.validate()

    def test_target_bin_boundaries_are_fixed(self):
        for value, label in ((-5.01, 0), (-5, 1), (5, 1), (5.01, 2)):
            self.assertEqual(replace(self.rows[0], return_bps=value).label, label)

    def test_end_to_end_generates_models_and_rejects_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "run"
            report = run(output, count=100, epochs=1, seed=7)
            self.assertEqual(report["status"], "synthetic_engineering_only")
            self.assertEqual(set(report["evaluation_metrics"]),
                             {"numeric", "single", "flow", "liquidity", "context", "council", "equal_pool", "prevalence"})
            self.assertEqual(set(report["gate_weights"]), set(VIEWS))
            self.assertEqual(len(list(output.glob("*.pt"))), 5)
            for line in (output / "evaluation.jsonl").read_text().splitlines():
                for probabilities in json.loads(line)["predictions"].values():
                    self.assertEqual(len(probabilities), 3)
                    self.assertAlmostEqual(sum(probabilities), 1)
            before = (output / "report.json").read_bytes()
            with self.assertRaises(FileExistsError):
                run(output, count=100, epochs=1, seed=7)
            self.assertEqual(before, (output / "report.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
