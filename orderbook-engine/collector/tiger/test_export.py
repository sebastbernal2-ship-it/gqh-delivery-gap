#!/usr/bin/env python3
import json
import tempfile
import unittest
from pathlib import Path

import export_fixture


class ExportTest(unittest.TestCase):
    def test_saved_tiger_rows_match_ocaml_jsonl_shape(self):
        row = {
            "kind": "snapshot",
            "segment": 1,
            "symbol": "BTCUSDT",
            "received_time": "2024-01-01T00:00:00Z",
            "event_time_ms": 1704067200000,
            "source_path": "capture.gz",
            "source_sha256": "a" * 64,
            "applied": True,
            "last_update_id": 100,
            "first_update_id": None,
            "final_update_id": None,
            "previous_update_id": None,
            "bids": [["100.00", "1.0"]],
            "asks": [["101.00", "2.0"]],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rows.json"
            path.write_text(
                json.dumps(
                    {
                        "result_sets": [
                            {
                                "columns": [{"name": name} for name in row],
                                "rows": [[row[name] for name in row]],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            rows = export_fixture.query_json("tiger", None, "SELECT 1", path)
        normalized = export_fixture.row_to_normalized(rows[0])
        self.assertEqual(normalized["received_time"], "2024.01.01D00:00:00.000000000")
        self.assertEqual(normalized["last_update_id"], 100)
        self.assertEqual(normalized["bids"], [["100.00", "1.0"]])


class CanonicalExportTest(unittest.TestCase):
    def depth_row(self, **overrides):
        row = {
            "kind": "snapshot",
            "segment": 1,
            "symbol": "BTCUSDT",
            "received_time": "2024-01-01T00:00:00.150000+00:00",
            "event_time_ms": 1704067200100,
            "source_path": "captures/day-1.csv.gz",
            "source_sha256": "a" * 64,
            "applied": True,
            "last_update_id": 100,
            "first_update_id": None,
            "final_update_id": None,
            "previous_update_id": None,
            "bids": [["100000.0001", "1.000001"]],
            "asks": [["100000.0002", "2"]],
        }
        row.update(overrides)
        return row

    def test_canonical_depth_uses_integer_units(self):
        event = export_fixture.row_to_canonical_depth(self.depth_row(), "binance-futures")
        self.assertEqual(event["kind"], "depth_snapshot")
        self.assertEqual(event["bids"], [[1000000001, 1000001]])
        self.assertEqual(event["asks"], [[1000000002, 2000000]])
        self.assertEqual(event["event_time"], "2024-01-01T00:00:00.100000000Z")
        self.assertEqual(event["receive_time"], "2024-01-01T00:00:00.150000000Z")
        self.assertEqual(event["quality"], "healthy")
        self.assertEqual(event["source_sha256"], "a" * 64)

    def test_canonical_depth_marks_unapplied_rows_suspect(self):
        event = export_fixture.row_to_canonical_depth(
            self.depth_row(applied=False), "binance-futures"
        )
        self.assertEqual(event["quality"], "suspect")
        self.assertIn("quality_reason", event)

    def test_canonical_depth_update_uses_final_update_id(self):
        row = self.depth_row(
            kind="update",
            last_update_id=None,
            first_update_id=101,
            final_update_id=102,
            previous_update_id=100,
        )
        event = export_fixture.row_to_canonical_depth(row, "binance-futures")
        self.assertEqual(event["kind"], "depth_update")
        self.assertEqual(event["first_update_id"], 101)
        self.assertEqual(event["last_update_id"], 102)
        self.assertEqual(event["previous_update_id"], 100)
        with self.assertRaises(ValueError):
            export_fixture.row_to_canonical_depth(
                row | {"final_update_id": None}, "binance-futures"
            )

    def test_canonical_trade_and_observation(self):
        trade = {
            "symbol": "BTCUSDT",
            "received_time": "2024-01-01T00:00:01+00:00",
            "trade_time_ms": 1704067200000,
            "trade_id": "9001",
            "price": "100000.5",
            "quantity": "0.01",
            "buyer_is_maker": True,
            "source_path": "captures/trades.csv.gz",
            "source_sha256": "b" * 64,
        }
        event = export_fixture.row_to_canonical_trade(trade, "binance-futures")
        self.assertEqual(event["kind"], "trade")
        self.assertEqual(event["price_ticks"], 1000005000)
        self.assertEqual(event["quantity_units"], 10000)
        observation = {
            "observed_at": "2024-01-01 00:00:10+00",
            "data_type": "book-depth",
            "source": "file:/data/book-depth.csv",
            "symbol": "BTCUSDT",
            "payload": '{"percentage":-5,"depth":"11063.46100000","notional":"457379319.64167000"}',
            "source_sha256": "c" * 64,
        }
        event = export_fixture.row_to_canonical_observation(observation, "binance-futures")
        self.assertEqual(event["kind"], "observation")
        self.assertEqual(event["data_type"], "book-depth")
        self.assertIn('"percentage":-5', event["payload"])
        self.assertEqual(event["event_time"], "2024-01-01T00:00:10.000000000Z")
        with self.assertRaises(ValueError):
            export_fixture.row_to_canonical_observation(
                observation | {"symbol": None}, "binance-futures"
            )
        with self.assertRaises(ValueError):
            export_fixture.row_to_canonical_observation(
                observation | {"source_sha256": None}, "binance-futures"
            )

    def test_bool_field_accepts_sql_text_forms(self):
        self.assertIs(export_fixture.bool_field(True, "x"), True)
        self.assertIs(export_fixture.bool_field(False, "x"), False)
        self.assertIs(export_fixture.bool_field("t", "x"), True)
        self.assertIs(export_fixture.bool_field("f", "x"), False)
        self.assertIs(export_fixture.bool_field("true", "x"), True)
        self.assertIs(export_fixture.bool_field("false", "x"), False)
        with self.assertRaises(ValueError):
            export_fixture.bool_field("maybe", "x")

    def test_trade_rows_keep_both_aggressor_sides(self):
        base = {
            "symbol": "BTCUSDT",
            "received_time": "2026-10-03T23:42:24.110617+00:00",
            "trade_time_ms": 1791070942477,
            "trade_id": "8143911217",
            "price": "84744.20",
            "quantity": "0.002",
            "source_path": "captures/trades.jsonl.gz",
            "source_sha256": "b" * 64,
        }
        maker = export_fixture.row_to_canonical_trade(
            base | {"buyer_is_maker": "t"}, "binance-futures"
        )
        taker = export_fixture.row_to_canonical_trade(
            base | {"buyer_is_maker": "f"}, "binance-futures"
        )
        self.assertIs(maker["buyer_is_maker"], True)
        self.assertIs(taker["buyer_is_maker"], False)

    def test_depth_quality_reads_the_sql_text_form(self):
        row = self.depth_row(applied="f")
        event = export_fixture.row_to_canonical_depth(row, "binance-futures")
        self.assertEqual(event["quality"], "suspect")
        row = self.depth_row(applied="t")
        event = export_fixture.row_to_canonical_depth(row, "binance-futures")
        self.assertEqual(event["quality"], "healthy")

    def test_unit_conversion_rejects_extra_precision(self):
        self.assertEqual(export_fixture.price_ticks("1"), 10000)
        self.assertEqual(export_fixture.price_ticks("1.50000"), 15000)
        self.assertEqual(export_fixture.quantity_units("1.000001"), 1000001)
        with self.assertRaises(ValueError):
            export_fixture.price_ticks("1.00001")
        with self.assertRaises(ValueError):
            export_fixture.quantity_units("0.0000001")
        with self.assertRaises(ValueError):
            export_fixture.price_ticks("-1")
        with self.assertRaises(ValueError):
            export_fixture.price_ticks("abc")

    def test_manifest_records_provenance(self):
        class Args:
            kind = "observations"
            venue = "binance-futures"
            symbol = "BTCUSDT"
            start = "2024-01-01T00:00:00Z"
            end = "2024-01-01T00:10:00Z"

        events = [
            export_fixture.row_to_canonical_observation(
                {
                    "observed_at": "2024-01-01 00:00:10+00",
                    "data_type": "book-depth",
                    "source": "file:/data/book-depth.csv",
                    "symbol": "BTCUSDT",
                    "payload": {"percentage": -5, "depth": "1.0", "notional": "2.0"},
                    "source_sha256": "c" * 64,
                },
                "binance-futures",
            ),
            export_fixture.row_to_canonical_observation(
                {
                    "observed_at": "2024-01-01 00:00:13+00",
                    "data_type": "book-depth",
                    "source": "file:/data/book-depth.csv",
                    "symbol": "BTCUSDT",
                    "payload": {"percentage": -5, "depth": "3.0", "notional": "4.0"},
                    "source_sha256": "c" * 64,
                },
                "binance-futures",
            ),
        ]
        manifest = export_fixture.manifest_for("fixture.jsonl", events, Args(), "d" * 64)
        self.assertEqual(manifest["row_count"], 2)
        self.assertEqual(manifest["source_hashes"], ["c" * 64])
        self.assertEqual(
            manifest["event_time_range"],
            ["2024-01-01T00:00:10.000000000Z", "2024-01-01T00:00:13.000000000Z"],
        )
        self.assertEqual(manifest["fixture_sha256"], "d" * 64)
        self.assertEqual(manifest["query_version"], export_fixture.QUERY_VERSION)

    def test_query_for_kind_selects_table(self):
        depth = export_fixture.query_for("depth", "BTCUSDT", "2024-01-01", "2024-01-02")
        self.assertIn("FROM depth_events", depth)
        self.assertIn("received_time >=", depth)
        # Snapshots must come first inside their segment so a fixture replays
        # in file order.
        self.assertIn(
            "ORDER BY floor(extract(epoch from received_time) / 300), (kind = 'snapshot') DESC, received_time",
            depth,
        )
        trades = export_fixture.query_for("trades", None, None, None)
        self.assertIn("FROM trade_events", trades)
        self.assertNotIn("WHERE", trades)
        observations = export_fixture.query_for("observations", "BTCUSDT", None, None)
        self.assertIn("FROM observations", observations)
        self.assertIn("observed_at", observations)


if __name__ == "__main__":
    unittest.main()
