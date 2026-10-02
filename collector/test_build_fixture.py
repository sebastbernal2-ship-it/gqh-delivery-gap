"""Tests for the local normalized-to-canonical fixture builder."""

import json
import tempfile
import unittest
from pathlib import Path

import build_fixture


def row(kind, received, **extra):
    base = {
        "kind": kind,
        "segment": 1,
        "symbol": "BTCUSDT",
        "received_time": received,
        "event_time_ms": 1791070944257,
        "source_path": "capture.jsonl.gz",
        "source_sha256": "a" * 64,
        "applied": True,
        "bids": [["84744.0", "1.5"]],
        "asks": [["84744.1", "2.0"]],
        "last_update_id": None,
        "first_update_id": None,
        "final_update_id": None,
        "previous_update_id": None,
    }
    base.update(extra)
    return base


class ParseReceivedTest(unittest.TestCase):
    def test_nine_fraction_digits(self):
        seconds, nanoseconds = build_fixture.parse_received("2026.10.03D23:42:24.335665000")
        self.assertEqual(nanoseconds, 335665000)
        self.assertEqual(seconds % 60, 24)

    def test_rejects_bad_shape(self):
        with self.assertRaises(build_fixture.FixtureError):
            build_fixture.parse_received("2026-10-03T23:42:24Z")


class OrderingTest(unittest.TestCase):
    def test_snapshot_first_inside_its_bucket_even_when_later(self):
        update = row("update", "2026.10.04D00:00:01.000000000", first_update_id=2, final_update_id=2, previous_update_id=1, last_update_id=None)
        snapshot = row("snapshot", "2026.10.04D00:00:05.000000000", last_update_id=2)
        later_bucket = row("update", "2026.10.04D00:06:01.000000000", first_update_id=3, final_update_id=3, previous_update_id=2, last_update_id=None)
        rows = [update, snapshot, later_bucket]
        ordered = sorted(range(len(rows)), key=lambda index: build_fixture.fixture_key(rows[index], index))
        self.assertEqual([rows[index]["kind"] for index in ordered], ["snapshot", "update", "update"])

    def test_bucket_boundary_splits_windows(self):
        first = row("update", "2026.10.04D00:04:59.000000000", first_update_id=1, final_update_id=1, previous_update_id=0, last_update_id=None)
        second = row("update", "2026.10.04D00:05:01.000000000", first_update_id=2, final_update_id=2, previous_update_id=1, last_update_id=None)
        self.assertLess(build_fixture.bucket_of(first["received_time"]), build_fixture.bucket_of(second["received_time"]))


class AppliedFlagTest(unittest.TestCase):
    def test_unapplied_rows_are_kept_and_flagged(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "depth.jsonl"
            kept = row("update", "2026.10.04D00:00:01.000000000", applied=True, first_update_id=1, final_update_id=1, previous_update_id=0, last_update_id=None)
            flagged = row("update", "2026.10.04D00:00:02.000000000", applied=False, first_update_id=2, final_update_id=2, previous_update_id=1, last_update_id=None)
            path.write_text(json.dumps(kept) + "\n" + json.dumps(flagged) + "\n", encoding="utf-8")
            rows = build_fixture.load_rows([path], {"snapshot", "update"})
            self.assertEqual(len(rows), 2)
            event = build_fixture.convert(rows[1], "depth", "binance-futures")
            self.assertEqual(event["quality"], "suspect")
            self.assertEqual(event["quality_reason"], "capture row was not applied to the book")


class KindlessTradeRowTest(unittest.TestCase):
    def test_trade_rows_without_kind_are_selected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "trades.jsonl"
            path.write_text(
                json.dumps(
                    {
                        "symbol": "BTCUSDT",
                        "received_time": "2026.10.04D00:00:02.000000000",
                        "event_time_ms": 1791072002000,
                        "trade_time_ms": 1791072002000,
                        "source_path": "trades.jsonl.gz",
                        "source_sha256": "c" * 64,
                        "trade_id": 7,
                        "price": "84744.5",
                        "quantity": "0.5",
                        "buyer_is_maker": True,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            rows = build_fixture.load_rows([path], {"trade"})
            self.assertEqual(len(rows), 1)


class BuildTest(unittest.TestCase):
    def test_depth_rows_become_canonical_events(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "depth.jsonl"
            path.write_text(
                json.dumps(row("update", "2026.10.04D00:00:01.000000000", first_update_id=5, final_update_id=7, previous_update_id=4, last_update_id=None)) + "\n",
                encoding="utf-8",
            )
            rows = build_fixture.load_rows([path], {"snapshot", "update"})
            event = build_fixture.convert(rows[0], "depth", "binance-futures")
            self.assertEqual(event["kind"], "depth_update")
            self.assertEqual(event["previous_update_id"], 4)
            self.assertEqual(event["receive_time"], "2026-10-04T00:00:01.000000000Z")
            self.assertEqual(event["bids"], [[847440000, 1500000]])

    def test_trades_kind_reads_trade_rows(self):
        trade = {
            "kind": "trade",
            "symbol": "BTCUSDT",
            "received_time": "2026.10.04D00:00:02.000000000",
            "event_time_ms": 1791072002000,
            "source_path": "trades.jsonl.gz",
            "source_sha256": "b" * 64,
            "trade_id": "42",
            "price": "84744.5",
            "quantity": "0.25",
            "buyer_is_maker": False,
        }
        event = build_fixture.convert(trade, "trades", "binance-futures")
        self.assertEqual(event["kind"], "trade")
        self.assertEqual(event["trade_id"], 42)
        self.assertEqual(event["quantity_units"], 250000)
        self.assertFalse(event["buyer_is_maker"])


if __name__ == "__main__":
    unittest.main()
