#!/usr/bin/env python3
"""Contracts for the forward window: append-only snapshots and refused immature outcomes."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from evaluate_forward_window import realized  # noqa: E402
from run_forward_snapshot import new_snapshot_path  # noqa: E402

SERIES = {f"2026-01-{day:02d}": 100.0 + day for day in range(1, 29)}


def test_an_outcome_that_cannot_exist_yet_is_refused():
    assert realized(SERIES, "2026-01-27") is None            # fewer than 21 sessions remain
    assert realized(SERIES, "2026-01-01") is not None


def test_the_return_uses_entry_after_the_decision_and_the_declared_horizon():
    value, exit_session = realized(SERIES, "2026-01-01", horizon=5)
    days = sorted(SERIES)
    after = [day for day in days if day > "2026-01-01"]
    assert exit_session == after[5]
    assert abs(value - (SERIES[after[5]] / SERIES[after[0]] - 1.0)) < 1e-12


def test_a_snapshot_is_never_overwritten():
    with tempfile.TemporaryDirectory() as tmpdir:
        directory = Path(tmpdir)
        stamp = "20261004T000000Z"
        path = new_snapshot_path(directory, stamp)
        path.write_text(json.dumps({"run_utc": stamp}))
        try:
            new_snapshot_path(directory, stamp)
        except FileExistsError:
            pass
        else:
            raise AssertionError("an existing snapshot must be refused")
        assert json.loads(path.read_text())["run_utc"] == stamp


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} forward-window contract(s) held")
