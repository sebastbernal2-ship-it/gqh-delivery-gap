#!/usr/bin/env python3
"""Fail when capture output is stale or the data disk is nearly full."""

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


def main():
    data_dir = Path(os.environ.get("DATA_DIR", "/data/binance"))
    max_age = int(os.environ.get("MAX_CAPTURE_AGE_SECONDS", "900"))
    max_disk_percent = int(os.environ.get("MAX_DISK_PERCENT", "90"))
    manifest = data_dir / "manifest.jsonl"
    if not manifest.exists():
        print("healthcheck failed: manifest is missing", file=sys.stderr)
        return 1
    rows = [line for line in manifest.read_text(encoding="utf-8").splitlines() if line]
    if not rows:
        print("healthcheck failed: manifest is empty", file=sys.stderr)
        return 1
    try:
        record = json.loads(rows[-1])
        manifest_path = Path(record["path"])
        segment_paths = [
            path
            for path in data_dir.glob("*.jsonl.gz")
            if not path.name.startswith("rejected-")
        ]
        if not segment_paths:
            print("healthcheck failed: no capture segments exist", file=sys.stderr)
            return 1
        path = max(segment_paths, key=lambda candidate: candidate.stat().st_mtime)
        if not path.exists():
            print(f"healthcheck failed: latest segment is missing: {path}", file=sys.stderr)
            return 1
        manifest_ended = datetime.fromisoformat(record["ended"]).timestamp()
        file_is_closed = path.stat().st_mtime <= manifest_ended + 5
        if path == manifest_path and file_is_closed:
            subprocess.run(["gzip", "-t", str(path)], check=True, capture_output=True)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"healthcheck failed: latest segment is invalid: {error}", file=sys.stderr)
        return 1
    age = time.time() - path.stat().st_mtime
    if age > max_age:
        print(f"healthcheck failed: latest segment is {age:.0f}s old", file=sys.stderr)
        return 1
    total, used, _ = shutil.disk_usage(data_dir)
    disk_percent = used * 100 / total
    if disk_percent >= max_disk_percent:
        print(f"healthcheck failed: disk usage is {disk_percent:.1f}%", file=sys.stderr)
        return 1
    print(f"healthy: segment_age={age:.0f}s disk_usage={disk_percent:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
