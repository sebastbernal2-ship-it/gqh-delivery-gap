#!/usr/bin/env python3
"""The seasonal surprise must use only prior years, and the panel must carry the ramp columns."""
from __future__ import annotations

import csv
import gzip
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from run_eia_load_refinement import seasonal_surprise  # noqa: E402


def series(level: float) -> dict[str, float]:
    import datetime
    out = {}
    day = datetime.date(2019, 1, 1)
    while day < datetime.date(2023, 1, 1):
        out[day.isoformat()] = level
        day += datetime.timedelta(days=1)
    return out


def test_seasonal_surprise_compares_against_prior_years_only():
    flat = series(100.0)
    assert seasonal_surprise(flat, "2022-06-15") is not None
    value = seasonal_surprise(flat, "2022-06-15")
    assert abs(value) < 1e-9                     # the same level every year is no surprise
    raised = dict(flat)
    for month in (6, 7):
        for day in range(1, 29):
            raised[f"2022-{month:02d}-{day:02d}"] = 110.0
    value = seasonal_surprise(raised, "2022-06-29")
    assert value is not None and 0.05 < value < 0.15
    early = seasonal_surprise(flat, "2019-02-01")
    assert early is None                          # no prior-year window exists yet


def test_panel_carries_the_peak_and_ramp_columns():
    path = ROOT / "results" / "eia-load-daily.csv.gz"
    if not path.exists():
        return
    with gzip.open(path, "rt") as handle:
        header = next(csv.reader(handle))
    for column in ("demand_mean", "demand_peak", "demand_min", "demand_ramp_mean"):
        assert column in header, column


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} load-refinement contract(s) held")
