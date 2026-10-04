#!/usr/bin/env python3
"""Contracts for the tape-block gate: distinct dates counted, unrelated entries ignored."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from tape_block_due import recorded_dates  # noqa: E402


def test_only_block_directories_count_and_dates_are_distinct():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "btc-20261004T0812Z").mkdir()
        (root / "btc-20261004T2000Z").mkdir()          # same UTC date, still one date
        (root / "btc-20261005T0812Z").mkdir()
        (root / "btc-20261005T0812Z.launch.log").write_text("log")   # not a directory
        (root / "tape-20261003T213543Z.jsonl").write_text("{}")      # older format
        assert recorded_dates(root) == ["2026-10-04", "2026-10-05"]


def test_a_missing_root_is_an_empty_history():
    with tempfile.TemporaryDirectory() as tmp:
        assert recorded_dates(Path(tmp) / "nope") == []


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} tape-gate contract(s) held")
