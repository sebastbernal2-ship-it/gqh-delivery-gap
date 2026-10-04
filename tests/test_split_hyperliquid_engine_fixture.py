import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import split_hyperliquid_engine_fixture as adapter  # noqa: E402


SOURCE_HASH = "a" * 64


def event(kind, receive_time, symbol="BTC"):
    common = {
        "venue": "hyperliquid",
        "symbol": symbol,
        "source_id": "capture",
        "source_path": "raw.jsonl",
        "source_sha256": SOURCE_HASH,
        "quality": "healthy",
        "event_time": receive_time,
        "receive_time": receive_time,
        "sequence": None,
    }
    if kind == "depth_snapshot":
        return {**common, "kind": kind, "last_update_id": None, "bids": [[100, 200]], "asks": [[101, 300]]}
    return {**common, "kind": "trade", "trade_id": 1, "price_ticks": 101, "quantity_units": 25, "buyer_is_maker": False}


class SplitHyperliquidFixtureTest(unittest.TestCase):
    def test_splits_one_symbol_and_records_combined_and_component_hashes(self):
        rows = [
            event("trade", "2026-10-04T00:00:00.000000002Z"),
            event("depth_snapshot", "2026-10-04T00:00:00.000000001Z"),
            event("trade", "2026-10-04T00:00:00.000000003Z", "ETH"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.jsonl"
            source.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows))
            out = root / "out"
            manifest = adapter.split_fixture(source, out, "BTC", created_at="2026-10-04T00:01:00Z")
            combined = (out / "combined.jsonl").read_bytes()
            depth = (out / "depth.jsonl").read_bytes()
            trades = (out / "trades.jsonl").read_bytes()
            self.assertEqual(manifest["row_count"], 2)
            self.assertEqual(manifest["depth_rows"], 1)
            self.assertEqual(manifest["trade_rows"], 1)
            self.assertEqual(manifest["fixture_sha256"], hashlib.sha256(combined).hexdigest())
            self.assertEqual(manifest["component_sha256"]["depth"], hashlib.sha256(depth).hexdigest())
            self.assertEqual(manifest["component_sha256"]["trades"], hashlib.sha256(trades).hexdigest())
            ordered = [json.loads(line) for line in combined.splitlines()]
            self.assertEqual([row["kind"] for row in ordered], ["trade", "depth_snapshot"])
            self.assertEqual(ordered[1]["bids"], [[100, 200]])

    def test_refuses_non_integer_market_values_and_mixed_source_hashes(self):
        rows = [event("depth_snapshot", "2026-10-04T00:00:00.000000001Z"),
                event("trade", "2026-10-04T00:00:00.000000002Z")]
        rows[0]["bids"] = [[100.5, 200]]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "bad.jsonl"
            source.write_text("".join(json.dumps(row) + "\n" for row in rows))
            with self.assertRaisesRegex(ValueError, "integer \\[price, quantity\\]"):
                adapter.split_fixture(source, root / "bad-out", "BTC", created_at="2026-10-04T00:01:00Z")

    def test_refuses_existing_output_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.jsonl"
            source.write_text("\n".join(json.dumps(row) for row in [
                event("depth_snapshot", "2026-10-04T00:00:00.000000001Z"),
                event("trade", "2026-10-04T00:00:00.000000002Z"),
            ]))
            out = root / "out"
            out.mkdir()
            with self.assertRaises(FileExistsError):
                adapter.split_fixture(source, out, "BTC")


if __name__ == "__main__":
    unittest.main()
