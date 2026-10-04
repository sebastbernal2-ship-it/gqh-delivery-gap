#!/usr/bin/env python3
"""Contracts for the grid-load specialist: growth arithmetic, rank correlation, declared exposure."""
from __future__ import annotations

import gzip
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from run_eia_load_specialist import EXPOSURE, growth, spearman  # noqa: E402


def test_growth_is_the_recent_window_against_the_prior_window():
    import datetime

    def series(levels):
        out, day = {}, datetime.date(2020, 1, 1)
        for level in levels:
            out[day.isoformat()] = level
            day += datetime.timedelta(days=1)
        return out, day.isoformat()

    short, day = series([100.0] * 40)
    assert growth(short, day, window=30) is None            # two full windows are required
    flat, day = series([100.0] * 60)
    assert growth(flat, day, window=30) == 0.0
    jumped, day = series([100.0] * 60 + [121.0] * 30)
    value = growth(jumped, day, window=30)
    assert value is not None and abs(value - 0.21) < 1e-9   # recent window against the prior window


def test_spearman_is_monotone_and_rejects_tiny_samples():
    assert spearman([1, 2, 3, 4, 5, 6, 7, 8], [1, 2, 3, 4, 5, 6, 7, 8]) == 1.0
    assert spearman([1, 2, 3, 4, 5, 6, 7, 8], [8, 7, 6, 5, 4, 3, 2, 1]) == -1.0
    assert spearman([1, 2, 3], [1, 2, 3]) is None


def test_every_mapped_authority_exists_in_the_published_panel():
    panel_path = ROOT / "results" / "eia-load-daily.csv.gz"
    if not panel_path.exists():
        return
    with gzip.open(panel_path, "rt") as handle:
        import csv
        authorities = {row["authority"] for row in csv.DictReader(handle)}
    missing = {authority for authority in EXPOSURE.values() if authority not in authorities}
    assert not missing, missing


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} grid-load contract(s) held")
