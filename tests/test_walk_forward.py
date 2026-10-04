#!/usr/bin/env python3
"""Contracts for the rolling-origin harness: disjoint blocks and a strict training cutoff."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from run_walk_forward import ORIGINS, blocks, fit_at  # noqa: E402


def test_origins_are_strictly_increasing_and_blocks_are_disjoint():
    assert ORIGINS == tuple(sorted(ORIGINS)) and len(set(ORIGINS)) == len(ORIGINS)
    spans = blocks()
    assert len(spans) == len(ORIGINS)
    for (start, end), next_start in zip(spans, list(ORIGINS[1:]) + [None]):
        assert start < end
        if next_start is not None:
            assert end == next_start                      # a block ends where the next begins


def row(day: str, label: int = 0) -> dict:
    return {"ticker": "T", "label_available": f"{day}T23:59:59+00:00", "label_bin": label,
            "period_end": "2020-03-31", "group_name": ""}


def test_fit_at_never_trains_on_rows_at_or_after_the_origin():
    rows = [row(f"20{year}-06-30", year % 5) for year in range(19, 25)]
    fitted = fit_at(rows, "2022-01-01")
    assert fitted["train"], "there must be training rows before the origin"
    assert all(str(item["label_available"])[:10] < "2022-01-01" for item in fitted["train"])
    assert all(str(item["label_available"])[:10] >= "2022-01-01" for item in fitted["later"])


def test_an_origin_with_too_little_history_yields_no_predictions():
    rows = [row("2021-06-30"), row("2022-06-30")]
    fitted = fit_at(rows, "2022-01-01")
    assert fitted["probabilities"] is None and fitted["classes"] is None


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} walk-forward contract(s) held")
