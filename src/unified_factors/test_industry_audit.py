"""Tests for the quarantined nested industry-control sensitivity audit."""
import csv
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from .industry_audit import audit


class IndustryAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        rng = np.random.default_rng(42)
        n = 120
        market = rng.normal(0, 0.01, n)
        style = rng.normal(0, 0.01, n)
        industry = rng.normal(0, 0.01, n)
        noise = rng.normal(0, 0.001, (n, 2))
        start = datetime(2020, 1, 1, 21, tzinfo=timezone.utc)
        dates = [(start + timedelta(days=i)).isoformat() for i in range(n)]
        assets = ["A", "B"]
        values = np.column_stack((market, style, industry))
        returns = np.column_stack((2 * market + 0.4 * industry, -market + style - 0.7 * industry)) + noise
        factors = ["MKT", "SMB", "IND"]
        self.panel_path = self.root / "panel.json"
        self.controls_path = self.root / "controls.csv"
        self.panel_path.write_text(json.dumps({
            "study_role": "retrospective_only", "assets": assets,
            "factor_specs": [{"id": key} for key in factors],
            "rows": [{"period_end": dates[i], "available_at": dates[i],
                      "excess_returns": dict(zip(assets, returns[i].tolist())),
                      "factors": dict(zip(factors, values[i].tolist()))}
                     for i in range(n)],
        }))
        with self.controls_path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["session", "period_end", "available_at", "Industry"])
            writer.writeheader()
            for i in range(n):
                writer.writerow({"session": dates[i][:10], "period_end": dates[i],
                                 "available_at": dates[i], "Industry": industry[i]})

    def tearDown(self):
        self.temp.cleanup()

    def test_nested_control_reduces_residual_and_preserves_interpretation_limit(self):
        result = audit(self.panel_path, self.controls_path, ("MKT", "SMB"))
        delta = result["incremental"]["r_squared_change"]
        partial = result["incremental"]["partial_r_squared"]
        self.assertGreater(delta["A"], 0.05)
        self.assertGreater(delta["B"], 0.05)
        self.assertGreater(partial["A"], 0.9)
        self.assertGreater(partial["B"], 0.9)
        self.assertFalse(result["industry_controls_are_asset_matched"])
        self.assertIn("not forecast", result["label"])

    def test_control_clock_must_match_exact_session(self):
        with self.controls_path.open(newline="") as stream:
            content = list(csv.DictReader(stream))
        content[10]["session"] = "2019-12-31"
        with self.controls_path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=content[0].keys())
            writer.writeheader()
            writer.writerows(content)
        with self.assertRaisesRegex(ValueError, "date mismatch"):
            audit(self.panel_path, self.controls_path, ("MKT", "SMB"))

    def test_non_quarantined_panel_is_refused(self):
        panel = json.loads(self.panel_path.read_text())
        panel["study_role"] = "development"
        self.panel_path.write_text(json.dumps(panel))
        with self.assertRaisesRegex(ValueError, "requires the quarantined"):
            audit(self.panel_path, self.controls_path, ("MKT", "SMB"))

    def test_holdout_boundary_is_refused_even_if_role_is_mislabeled(self):
        panel = json.loads(self.panel_path.read_text())
        with self.controls_path.open(newline="") as stream:
            control_rows = list(csv.DictReader(stream))
        panel["rows"][-1]["period_end"] = "2024-10-03T20:00:00+00:00"
        panel["rows"][-1]["available_at"] = "2026-10-03T21:00:00+00:00"
        control_rows[-1]["session"] = "2024-10-03"
        control_rows[-1]["period_end"] = "2024-10-03T20:00:00+00:00"
        control_rows[-1]["available_at"] = "2026-10-03T21:00:00+00:00"
        self.panel_path.write_text(json.dumps(panel))
        with self.controls_path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=control_rows[0].keys())
            writer.writeheader()
            writer.writerows(control_rows)
        with self.assertRaisesRegex(ValueError, "sealed holdout boundary"):
            audit(self.panel_path, self.controls_path, ("MKT", "SMB"))


if __name__ == "__main__":
    unittest.main()
