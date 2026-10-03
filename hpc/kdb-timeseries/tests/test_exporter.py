from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import export_tiger_bars as exporter


class ExporterTests(unittest.TestCase):
    def _record(self, **overrides):
        record = {
            "source_id": "massive_bars",
            "batch_sha256": hashlib.sha256(b"batch").hexdigest(),
            "row_index": 3,
            "row_sha256": hashlib.sha256(b"row").hexdigest(),
            "payload_json": {"ticker": "PWR", "bar_time_utc": "2026-01-02T00:00:00Z",
                             "open": 101.25, "high": 104, "low": 99.5,
                             "close": 103.5, "volume": 1200},
        }
        record.update(overrides)
        return record

    def test_normalizes_prices_to_exact_scaled_integers(self):
        out = exporter.normalize_record(self._record())
        self.assertEqual(out["date"], "2026-01-02")
        self.assertEqual(out["open_px_e8usd"], 10_125_000_000)
        self.assertEqual(out["volume"], 1200)

    def test_rejects_timezone_naive_timestamp(self):
        with self.assertRaisesRegex(ValueError, "timezone"):
            exporter.session_date(datetime(2026, 1, 2))

    def test_utc_date_rollover(self):
        self.assertEqual(exporter.session_date("2026-01-02T00:30:00+01:00").isoformat(), "2026-01-01")

    def test_rejects_float_that_cannot_be_represented_at_scale(self):
        with self.assertRaisesRegex(ValueError, "represented exactly"):
            exporter.to_scaled_e8usd("0.000000001", "price")

    def test_rejects_bad_ohlc(self):
        rec = self._record(payload_json={"ticker": "PWR", "bar_time_utc": "2026-01-02T00:00:00Z",
                                         "open": 101, "high": 100, "low": 99,
                                         "close": 100, "volume": 1})
        with self.assertRaisesRegex(ValueError, "OHLC"):
            exporter.normalize_record(rec)

    def test_output_is_not_overwritten_unless_explicit(self):
        row = exporter.normalize_record(self._record())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bars.tsv"
            exporter.write_export([row], path)
            with self.assertRaises(FileExistsError):
                exporter.write_export([row], path)
            manifest = exporter.write_export([row], path, force=True)
            self.assertEqual(manifest["rows"], 1)


if __name__ == "__main__":
    unittest.main()
