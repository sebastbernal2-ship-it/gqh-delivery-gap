#!/usr/bin/env python3
"""Contracts for the RPO surprise specialist: no future input, bins, drops, comparison."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.model import compare  # noqa: E402
from filing_specialist.rpo_model import (BIN_LABELS, FEATURES, prepare_rows,  # noqa: E402
                                         surprise_bin)


def vintage(ticker: str, period_end: str, relative: str, availability: str,
            status: str = "measured", change: str = "10", previous: str = "100",
            history_count: str = "2", group: str = "datacenter") -> dict:
    return {"ticker": ticker, "period_end": period_end, "relative_surprise_pit": relative,
            "surprise_pit": relative, "expectation_status": status, "availability": availability,
            "change": change, "previous_value": previous, "history_count": history_count,
            "history_span_days": "365", "group": group, "in_sealed_window": "False"}


def test_bins_are_left_closed_around_the_declared_edges():
    assert surprise_bin(-0.20) == 0
    assert surprise_bin(-0.10) == 1
    assert surprise_bin(-0.02) == 2
    assert surprise_bin(0.02) == 3
    assert surprise_bin(0.10) == 4
    assert len(BIN_LABELS) == 5


def test_future_rows_cannot_change_earlier_features():
    rows = [vintage("T", "2022-03-31", "0.05", "2022-05-01T00:00:00+00:00"),
            vintage("T", "2023-03-31", "-0.05", "2023-05-01T00:00:00+00:00")]
    before, _ = prepare_rows(rows)
    later = rows + [vintage("T", "2024-03-31", "0.90", "2024-05-01T00:00:00+00:00")]
    after, _ = prepare_rows(later)
    keys = ("label_available", "last_relative_surprise", "mean_relative_surprise_3", "prior_count")
    assert [{k: row[k] for k in keys} for row in before] == \
           [{k: row[k] for k in keys} for row in after[:2]]
    assert after[2]["last_relative_surprise"] == -0.05
    assert after[2]["prior_count"] == 2.0


def test_first_disclosure_has_null_prior_features_and_a_flag():
    rows, _ = prepare_rows([vintage("T", "2022-03-31", "0.05", "2022-05-01T00:00:00+00:00")])
    row = rows[0]
    assert row["missing_prior"] == 1.0
    assert row["last_relative_surprise"] is None
    assert row["days_since_prior"] is None
    assert row["prior_count"] == 0.0


def test_rows_without_a_measured_vintage_are_dropped_with_reasons():
    rows, drops = prepare_rows([
        vintage("T", "2022-03-31", "0.05", "2022-05-01T00:00:00+00:00", status="missing"),
        vintage("T", "2022-06-30", "", "2022-08-01T00:00:00+00:00"),
        vintage("", "2022-09-30", "0.05", "2022-11-01T00:00:00+00:00"),
    ])
    assert rows == []
    assert drops == {"not_measured": 1, "no_relative_surprise": 1, "no_ticker": 1}


def test_comparison_runs_on_synthetic_rows_and_returns_finite_scores():
    rows = []
    for index in range(60):
        relative = ((index % 7) - 3) / 20.0
        rows.append(vintage("T", f"20{20 + index // 4}-{(index % 4) * 3 + 3:02d}-30",
                            f"{relative:.4f}", f"20{21 + index // 4}-01-{index % 27 + 1:02d}T00:00:00+00:00"))
    prepared, _ = prepare_rows(rows)
    report = compare(prepared, FEATURES, fraction=0.7)
    assert report["split"]["train_rows"] + report["split"]["test_rows"] == len(prepared)
    for name in ("prevalence", "softmax"):
        assert report[name]["log_loss"] > 0.0
        assert 0.0 <= report[name]["accuracy"] <= 1.0
    assert report["split"]["train_through"] < report["split"]["test_from"]


def test_prepare_rows_reads_a_file_wide_edge_declaration_and_the_standardized_column():
    base = {"ticker": "T", "expectation_status": "measured", "availability": "2020-01-01T23:59:59+00:00",
            "period_end": "2019-12-31", "previous_value": "100", "change": "5", "group": "g"}
    rows = []
    for index, value in enumerate(("1.0", "-1.0", "2.0", "0.0")):
        row = dict(base, relative_surprise_pit="0.01", relative_surprise_z=value,
                   change_relative_z="0.1", label_edges="-1.5,-0.5,0.5,1.5",
                   availability=f"2020-01-0{index+1}T23:59:59+00:00", period_end=f"2019-0{index+1}-01")
        rows.append(row)
    prepared, _ = prepare_rows(rows, surprise_column="relative_surprise_z",
                               change_column="change_relative_z")
    labels = [row["label_bin"] for row in prepared]
    assert labels == [3, 1, 4, 2]                        # the z edges apply, not the default ones
    default_prepared, _ = prepare_rows(rows[1:2])
    assert default_prepared[0]["label_bin"] == 2         # default edges unchanged: 0.01 sits in the middle


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} rpo specialist contract(s) held")
