"""Contracts for the council-as-combiner experiment: partitions, clocks, finite scores."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from council.distributions import assert_compatible  # noqa: E402
from filing_council import as_matrix, clock, evaluate_council, fit_block, four_way  # noqa: E402


def panel(count: int = 81) -> list[dict]:
    rows = []
    for index in range(count):
        rows.append({
            "label_available": f"20{20 + index // 36}-{index // 12 % 12 + 1:02d}-{index % 28 + 1:02d}T12:00:00+00:00",
            "label_bin": index % 5,
            "f0": float(index % 7),
            "f1": float((index * 3) % 11),
            "f2": float((index * 5) % 13),
        })
    return sorted(rows, key=lambda row: row["label_available"])


class FilingCouncilTests(unittest.TestCase):
    def test_four_way_blocks_are_nonempty_chronological_and_disjoint(self):
        rows = panel()
        blocks = four_way(rows)
        self.assertEqual(sum(len(block) for block in blocks), len(rows))
        joined = [row["label_available"] for block in blocks for row in block]
        self.assertEqual(joined, sorted(joined))
        sizes = [len(block) for block in blocks]
        self.assertEqual(sizes, [34, 8, 8, 8, 23], sizes)
        for left, right in zip(blocks, blocks[1:]):
            self.assertLess(max(row["label_available"] for row in left),
                            min(row["label_available"] for row in right))

    def test_a_shared_timestamp_never_splits_across_blocks(self):
        rows = panel()
        rows[33]["label_available"] = rows[34]["label_available"]
        rows[41]["label_available"] = rows[42]["label_available"]
        blocks = four_way(rows)
        for left, right in zip(blocks, blocks[1:]):
            self.assertLess(max(row["label_available"] for row in left),
                            min(row["label_available"] for row in right))
        self.assertGreaterEqual(len(blocks[0]), 35)
        self.assertGreaterEqual(len(blocks[1]), 8)

    def test_clock_ends_at_the_reveal(self):
        row = {"label_available": "2024-05-01T12:00:00+00:00"}
        cutoff, forecast_time, valid_until = clock(row, "2024-02-01T12:00:00+00:00")
        self.assertEqual(cutoff, "2024-02-01T12:00:00+00:00")
        self.assertLess(forecast_time, valid_until)
        self.assertLessEqual(cutoff, forecast_time)
        # a prior row sharing the timestamp cannot be the cutoff
        fallback, forecast_time, valid_until = clock(row, "2024-05-01T12:00:00+00:00")
        self.assertEqual(fallback, "2023-05-02T12:00:00+00:00")
        self.assertLessEqual(fallback, forecast_time)

    def test_block_specialist_forecast_holds_the_contract(self):
        rows = panel()
        matrix, labels = as_matrix([[row["f0"], row["f1"], row["f2"]] for row in rows[:34]]), \
            np.array([int(row["label_bin"]) for row in rows[:34]])
        specialist = fit_block(matrix, labels, "evidence:metadata", "m1", "d1", steps=100)
        cutoff, forecast_time, valid_until = clock(rows[40], rows[39]["label_available"])
        forecast = specialist.forecast([1.0, 2.0, 3.0], "ctx", cutoff, forecast_time, valid_until)
        self.assertEqual(len(forecast.probabilities), 5)
        self.assertAlmostEqual(sum(forecast.probabilities), 1.0, places=9)
        assert_compatible((forecast,))

    def test_council_runs_end_to_end_on_synthetic_blocks(self):
        rows = panel()
        blocks = four_way(rows)
        metadata = as_matrix([[row["f0"], row["f1"], row["f2"]] for row in rows])
        text = np.random.default_rng(11).normal(size=(len(rows), 4))
        report = evaluate_council(blocks, metadata, text, ("f0", "f1", "f2"), steps=100)
        self.assertEqual(report["blocks"], {"training": 34, "calibration": 8, "gate": 8,
                                            "pool": 8, "evaluation": 23})
        for name in ("prevalence", "metadata_only", "text_only", "concatenated", "council"):
            self.assertEqual(report[name]["rows"], 23, name)
            self.assertTrue(np.isfinite(report[name]["log_loss"]), name)
            self.assertTrue(0.0 <= report[name]["accuracy"] <= 1.0, name)
        self.assertEqual(len(report["specialists"]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
