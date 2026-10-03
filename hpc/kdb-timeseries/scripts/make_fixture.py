#!/usr/bin/env python3
"""Create a deterministic synthetic TSV fixture for the HPG q-runtime smoke test."""
from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

FIELDS = ("date", "sym", "source_id", "batch_sha256", "row_index", "open_px_e8usd",
          "high_px_e8usd", "low_px_e8usd", "close_px_e8usd", "volume", "row_sha256")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    batch = hashlib.sha256(b"gqh-kdb-synthetic-smoke-v1").hexdigest()
    rows = [
        ("2026-01-02", "PWR", 100_000_000, 102_000_000, 99_000_000, 101_000_000, 1200),
        ("2026-01-05", "PWR", 101_000_000, 104_000_000, 100_000_000, 103_000_000, 1500),
        ("2026-01-05", "SPY", 600_000_000, 602_000_000, 598_000_000, 601_000_000, 9000),
    ]
    with args.output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for i, (d, sym, op, hi, lo, cl, vol) in enumerate(rows):
            payload = f"{d}|{sym}|{op}|{hi}|{lo}|{cl}|{vol}".encode()
            writer.writerow({"date": d, "sym": sym, "source_id": "synthetic_smoke",
                             "batch_sha256": batch, "row_index": i, "open_px_e8usd": op,
                             "high_px_e8usd": hi, "low_px_e8usd": lo, "close_px_e8usd": cl,
                             "volume": vol, "row_sha256": hashlib.sha256(payload).hexdigest()})


if __name__ == "__main__":
    main()
