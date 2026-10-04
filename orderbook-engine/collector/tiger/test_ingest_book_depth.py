#!/usr/bin/env python3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import ingest_book_depth

HEADER = "timestamp,percentage,depth,notional"
ROW_A = "2024-01-01 00:00:10,-5,11063.46100000,457379319.64167000"
ROW_B = "2024-01-01 00:00:10,1,1445.08600000,61384880.02871000"
ROW_C = "2024-01-01 00:00:13,-1,2115.40400000,89042185.24933000"


class IngestTest(unittest.TestCase):
    def write_csv(self, directory: str, lines: list[str]) -> Path:
        path = Path(directory) / "book-depth.csv"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def test_reads_rows_with_exact_decimal_payloads(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_csv(directory, [HEADER, ROW_A, ROW_B])
            rows = ingest_book_depth.read_rows(path, "BTCUSDT")
        self.assertEqual(len(rows), 2)
        self.assertEqual(
            rows[0]["payload"],
            {
                "percentage": -5,
                "depth": "11063.46100000",
                "notional": "457379319.64167000",
            },
        )
        self.assertEqual(
            rows[0]["observed_at"],
            datetime(2024, 1, 1, 0, 0, 10, tzinfo=timezone.utc),
        )

    def test_rejects_bad_input(self):
        with tempfile.TemporaryDirectory() as directory:
            bad_header = self.write_csv(directory, ["time,pct,depth,notional", ROW_A])
            with self.assertRaises(ValueError):
                ingest_book_depth.read_rows(bad_header, "BTCUSDT")
            bad_decimal = self.write_csv(
                directory, [HEADER, "2024-01-01 00:00:10,-5,abc,1.0"]
            )
            with self.assertRaises(ValueError):
                ingest_book_depth.read_rows(bad_decimal, "BTCUSDT")
            negative = self.write_csv(directory, [HEADER, "2024-01-01 00:00:10,-5,-1.0,1.0"])
            with self.assertRaises(ValueError):
                ingest_book_depth.read_rows(negative, "BTCUSDT")

    def test_select_rows_filters_and_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_csv(directory, [HEADER, ROW_A, ROW_B, ROW_C])
            rows = ingest_book_depth.read_rows(path, "BTCUSDT")
        start = datetime(2024, 1, 1, 0, 0, 11, tzinfo=timezone.utc)
        selected = ingest_book_depth.select_rows(rows, start, None, None)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["payload"]["percentage"], -1)
        limited = ingest_book_depth.select_rows(rows, None, None, 2)
        self.assertEqual(len(limited), 2)

    def test_sql_is_idempotent_and_escaped(self):
        rows = [
            {
                "observed_at": datetime(2024, 1, 1, 0, 0, 10, tzinfo=timezone.utc),
                "symbol": "BTCUSDT",
                "payload": {"percentage": -5, "depth": "1.0", "notional": "2.0"},
            }
        ]
        sql = ingest_book_depth.build_sql(rows, "BTCUSDT", "file:'/tmp/a.csv", "a" * 64)
        self.assertTrue(sql.startswith("DELETE FROM observations WHERE source_sha256 = "))
        self.assertIn("'file:''/tmp/a.csv", sql)
        self.assertIn("INSERT INTO observations", sql)
        self.assertIn("INSERT INTO source_manifests", sql)
        self.assertEqual(sql.count("ON CONFLICT (source_id) DO UPDATE"), 1)
        self.assertIn("(observed_at, data_type, source, symbol, payload, source_sha256)", sql)

    def test_batches_split_and_manifest_is_deterministic(self):
        base = datetime(2024, 1, 1, tzinfo=timezone.utc)
        rows = [
            {
                "observed_at": base + timedelta(seconds=index),
                "symbol": "BTCUSDT",
                "payload": {"percentage": 1, "depth": "1.0", "notional": "2.0"},
            }
            for index in range(ingest_book_depth.BATCH_ROWS + 1)
        ]
        sql = ingest_book_depth.build_sql(rows, "BTCUSDT", "file:/a.csv", "b" * 64)
        self.assertEqual(sql.count("INSERT INTO observations"), 2)
        first = ingest_book_depth.manifest_id("file:/a.csv", "b" * 64)
        second = ingest_book_depth.manifest_id("file:/a.csv", "b" * 64)
        other = ingest_book_depth.manifest_id("file:/a.csv", "c" * 64)
        self.assertEqual(first, second)
        self.assertNotEqual(first, other)
        rollback = ingest_book_depth.rollback_sql("file:/a.csv", "b" * 64)
        self.assertIn(first, rollback)
        self.assertIn("DELETE FROM observations", rollback)

    def test_run_path_sends_one_document(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_csv(directory, [HEADER, ROW_A])
            with mock.patch.object(sys, "argv", ["ingest_book_depth.py", str(path), "--symbol", "BTCUSDT"]):
                with mock.patch.object(ingest_book_depth, "run_tiger") as runner:
                    status = ingest_book_depth.main()
        self.assertEqual(status, 0)
        self.assertEqual(runner.call_count, 1)
        document = runner.call_args.args[2]
        self.assertIn("DELETE FROM observations", document)
        self.assertIn("INSERT INTO source_manifests", document)


if __name__ == "__main__":
    unittest.main()
