import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import pull_massive_daily_bars as massive


class MassiveIngestTests(unittest.TestCase):
    def test_api_key_is_added_only_to_allowed_host(self):
        url = massive._with_api_key("https://api.massive.com/v2/aggs?cursor=x", "secret")
        self.assertIn("apiKey=secret", url)
        with self.assertRaises(massive.MassiveError):
            massive._with_api_key("https://evil.example/v2/aggs", "secret")

    def test_bars_are_normalized_to_utc_and_validated(self):
        payload = {"status": "OK", "results": [
            {"t": 1790899200000, "o": 10, "h": 12, "l": 9, "c": 11, "v": 100},
        ]}
        with patch.object(massive, "_request_json", return_value=payload):
            rows = massive.get_bars("PWR", "2026-10-01", "2026-10-02", "unused")
        self.assertEqual(rows[0]["ticker"], "PWR")
        self.assertTrue(rows[0]["bar_time_utc"].endswith("+00:00"))

    def test_duplicate_timestamps_fail_closed(self):
        row = {"t": 1790899200000, "o": 10, "h": 12, "l": 9, "c": 11, "v": 100}
        with patch.object(massive, "_request_json", return_value={"status": "OK", "results": [row, row]}):
            with self.assertRaises(massive.MassiveError):
                massive.get_bars("PWR", "2026-10-01", "2026-10-02", "unused")

    def test_disclosures_keep_accession_and_supporting_text(self):
        event = {
            "tickers": ["PWR"], "cik": "1050915", "accession_number": "0000000000-26-000001",
            "filing_date": "2026-09-15", "primary_category": "operations",
            "secondary_category": "capacity", "tertiary_category": "project_delay",
            "supporting_text": "A verifiable excerpt.", "filing_url": "https://www.sec.gov/example",
        }
        with patch.object(massive, "_request_json", return_value={"status": "OK", "results": [event]}):
            rows = massive.get_disclosures("PWR", "2026-01-01", "2026-10-01", "unused")
        self.assertEqual(rows[0]["accession_number"], event["accession_number"])
        self.assertEqual(rows[0]["supporting_text"], event["supporting_text"])


if __name__ == "__main__":
    unittest.main()
