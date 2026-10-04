#!/usr/bin/env python3
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import ingest_normalized


def trade_row(index: int) -> dict:
    return {
        "received_time": f"2026.10.03D21:55:{index % 60:02d}.000000000",
        "event_time_ms": 1791064500000 + index,
        "trade_time_ms": 1791064500000 + index,
        "source_path": "btcusdt-trades-slice.jsonl.gz",
        "source_sha256": "a" * 64,
        "symbol": "BTCUSDT",
        "trade_id": str(8143852765 + index),
        "price": "84661.50",
        "quantity": "0.003",
        "buyer_is_maker": index % 2 == 0,
    }


class IngestNormalizedTest(unittest.TestCase):
    def test_parse_time_accepts_tardis_and_iso_formats(self):
        tardis = ingest_normalized.parse_time("2026.10.03D21:55:00.631603000")
        self.assertEqual(
            tardis, datetime(2026, 10, 3, 21, 55, 0, 631603, tzinfo=timezone.utc)
        )
        iso = ingest_normalized.parse_time("2026-10-03T21:55:00.631603+00:00")
        self.assertEqual(iso, tardis)
        with self.assertRaises(ValueError):
            ingest_normalized.parse_time("garbage")

    def test_event_key_is_deterministic(self):
        row = trade_row(1)
        self.assertEqual(ingest_normalized.event_key(row, "trades"), "trade:8143852766")
        depth = {"kind": "update", "segment": 1, "final_update_id": 10}
        self.assertEqual(ingest_normalized.event_key(depth, "depth"), "update:1:10")

    def test_every_row_appears_exactly_once_across_batches(self):
        rows = [trade_row(index) for index in range(ingest_normalized.BATCH_ROWS + 1)]
        sql = ingest_normalized.build_sql(rows, "trades", "x")
        self.assertEqual(sql.count("('trade:"), len(rows))
        self.assertEqual(sql.count("INSERT INTO trade_events"), 2)
        self.assertTrue(sql.startswith("DELETE FROM trade_events WHERE source_sha256 = "))
        first = ingest_normalized.event_key(rows[0], "trades")
        self.assertIn(first, sql)
        self.assertIn("INSERT INTO source_manifests", sql)

    def test_read_rows_rejects_missing_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rows.jsonl"
            path.write_text(
                json.dumps({"received_time": "2026.10.03D21:55:00.000000000"}) + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                ingest_normalized.read_rows(path, "trades")
            path.write_text(
                json.dumps(trade_row(0)) + "\n" + json.dumps(trade_row(1)) + "\n",
                encoding="utf-8",
            )
            rows = ingest_normalized.read_rows(path, "trades")
        self.assertEqual(len(rows), 2)

    def test_rollback_covers_rows_and_manifest(self):
        rows = [trade_row(0)]
        rollback = ingest_normalized.rollback_sql(rows, "trades")
        self.assertIn("DELETE FROM trade_events", rollback)
        self.assertIn("DELETE FROM source_manifests", rollback)
        self.assertIn("a" * 64, rollback)


if __name__ == "__main__":
    unittest.main()
