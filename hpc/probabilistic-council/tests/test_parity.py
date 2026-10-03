"""A parity gate must reject malformed vectors, not silently zip a matching prefix."""
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jevlike.verify_cpp_parity import probability_error


class ParityTests(unittest.TestCase):
    def test_complete_normalized_vectors_report_max_error(self):
        self.assertAlmostEqual(probability_error([0.2, 0.8], [0.3, 0.7]), 0.1)

    def test_rejects_truncated_and_extended_vectors(self):
        for vector in ([], [0.2], [0.2, 0.8, 0.0]):
            with self.subTest(vector=vector), self.assertRaises(ValueError):
                probability_error([0.2, 0.8], vector)

    def test_rejects_nonfinite_out_of_range_and_unnormalized_vectors(self):
        for vector in ([math.nan, 0.8], [math.inf, 0.8], [-0.1, 1.1], [0.1, 0.1]):
            with self.subTest(vector=vector), self.assertRaises(ValueError):
                probability_error([0.2, 0.8], vector)


if __name__ == "__main__":
    unittest.main()
