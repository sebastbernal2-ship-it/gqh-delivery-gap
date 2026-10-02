#!/usr/bin/env python3
import gzip
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import binance_depth_collector as collector


def test_restart_does_not_reuse_segment_path():
    with tempfile.TemporaryDirectory() as directory:
        original_data_dir = collector.DATA_DIR
        original_interval = collector.CAPTURE_INTERVAL_SECONDS
        collector.DATA_DIR = Path(directory)
        collector.CAPTURE_INTERVAL_SECONDS = 300
        captured_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        try:
            for _ in range(2):
                writer = collector.CaptureWriter("BTCUSDT", "depth")
                writer.write(
                    "btcusdt@depthSnapshot",
                    {"lastUpdateId": 1, "bids": [], "asks": []},
                    {},
                    captured_at,
                )
                writer.close()

            manifests = [
                json.loads(line)
                for line in (Path(directory) / "manifest.jsonl").read_text().splitlines()
            ]
            paths = [Path(row["path"]) for row in manifests]
            assert len(paths) == 2
            assert paths[0] != paths[1]
            assert all(path.exists() for path in paths)
            for path in paths:
                with gzip.open(path, "rt", encoding="utf-8") as handle:
                    assert handle.readline()
        finally:
            collector.DATA_DIR = original_data_dir
            collector.CAPTURE_INTERVAL_SECONDS = original_interval


if __name__ == "__main__":
    test_restart_does_not_reuse_segment_path()
    print("capture writer checks passed")
