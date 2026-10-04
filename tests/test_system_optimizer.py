#!/usr/bin/env python3
"""Contracts for the system-level optimizer: the composition, the subsetting, the commitment map."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from run_system_optimizer import BASELINE, subset  # noqa: E402


def test_baseline_is_the_published_configuration():
    assert BASELINE["horizon"] == 20 and BASELINE["sizing_gamma"] == 1.0
    assert BASELINE["entry_threshold"] == 0.0 and BASELINE["vol_target"] is None
    assert BASELINE["gate_threshold"] == 0.0        # the gate is on; strictness is what varies
    assert 0.7 < BASELINE["w_intensity"] < 0.85


def test_subset_is_half_open_on_the_end():
    daily = [{"date": f"2024-0{month}-01", "net": 0.0} for month in range(1, 10)]
    window = subset(daily, "2024-03-01", "2024-07-01")
    assert [row["date"] for row in window] == ["2024-03-01", "2024-04-01", "2024-05-01", "2024-06-01"]
    assert len(subset(daily, "2024-03-01")) == 7
    assert len(subset(daily, None, "2024-02-01")) == 1


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} system-optimizer contract(s) held")
