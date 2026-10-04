"""Smoke contracts for the filing text scorer on synthetic examples."""
from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from filing_scorer import run  # noqa: E402
from jevlike.data import validate  # noqa: E402

OPTIONS = ("down a lot", "down a little", "flat", "up a little", "up a lot")


def example(context: str, label: int):
    return validate({"context": context, "options": list(OPTIONS), "label": label})


def examples(count: int = 20) -> list:
    out = []
    for index in range(count):
        label = index % 3
        out.append(example(f"filing number {index} mentions item {label} and demand", label))
    return out


class FilingScorerTests(unittest.TestCase):
    def test_run_returns_finite_metrics_without_a_baseline(self):
        report = run(examples(20), None, fraction=0.5, epochs=3, seed=1)
        self.assertEqual(report["split"]["train"], 10)
        self.assertEqual(report["split"]["test"], 10)
        self.assertEqual(report["text"]["rows"], 10)
        self.assertTrue(report["text"]["log_loss"] > 0.0)
        self.assertTrue(0.0 <= report["text"]["accuracy"] <= 1.0)
        self.assertEqual(len(report["train_nll_trajectory"]), 3)
        self.assertNotIn("prevalence", report)

    def test_baseline_split_must_match_the_example_count(self):
        rows = [{"label_available": f"2024-01-{index + 1:02d}T00:00:00+00:00", "label_bin": index % 3}
                for index in range(5)]
        with self.assertRaises(ValueError):
            run(examples(20), (rows, rows), fraction=0.5, epochs=1, seed=1)

    def test_smallest_working_split_stays_finite(self):
        report = run(examples(6), None, fraction=0.5, epochs=2, seed=2)
        self.assertGreaterEqual(report["split"]["train"], 1)
        self.assertGreaterEqual(report["split"]["test"], 1)
        self.assertTrue(report["text"]["log_loss"] > 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
