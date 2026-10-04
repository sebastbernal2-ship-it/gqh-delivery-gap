#!/usr/bin/env python3
"""Accounting contracts for the capex intensity strategy harness.

These tests pin the repairs declared in
docs/inbox/aidan-2026-10-03/campaign/README.md:

1. the revenue join uses a 20 day window, not 20 months;
2. the signal is public only when all four facts are filed;
3. entry waits for the first session strictly after the filing date;
4. costs and capacity use the prior month's dollar volume;
5. overlapping cohorts share one unit of gross capital.
"""
from __future__ import annotations

import csv
import importlib.util
import pathlib
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "run_intensity_strategy", ROOT / "scripts" / "run_intensity_strategy.py")
ris = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ris)

FIELDS = ["ticker", "concept", "period_start", "period_end", "value_usd", "form", "filed", "fy", "fp"]


def write_rows(path: pathlib.Path, rows: list[dict]) -> None:
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({**{field: "" for field in FIELDS}, **row})


def test_day_gap_counts_calendar_days():
    assert ris.day_gap("2024-03-31", "2024-03-01") == 30
    assert ris.day_gap("2024-03-01", "2024-03-31") == 30
    assert ris.day_gap("2024-04-01", "2024-03-31") == 1


def test_revenue_join_uses_days_not_months():
    with tempfile.TemporaryDirectory() as tmp:
        capex = pathlib.Path(tmp) / "capex.csv"
        revenue = pathlib.Path(tmp) / "revenue.csv"
        write_rows(capex, [
            {"ticker": "T1", "period_end": "2023-03-31", "value_usd": "100", "filed": "2023-05-01"},
            {"ticker": "T1", "period_end": "2024-03-31", "value_usd": "120", "filed": "2024-05-01"},
            {"ticker": "T2", "period_end": "2023-03-31", "value_usd": "100", "filed": "2023-05-01"},
            {"ticker": "T2", "period_end": "2024-03-31", "value_usd": "120", "filed": "2024-05-01"},
        ])
        write_rows(revenue, [
            {"ticker": "T1", "concept": ris.PREFERRED, "period_end": "2023-04-05", "value_usd": "1000", "filed": "2023-05-01"},
            {"ticker": "T1", "concept": ris.PREFERRED, "period_end": "2024-04-05", "value_usd": "1100", "filed": "2024-05-01"},
            {"ticker": "T2", "concept": ris.PREFERRED, "period_end": "2023-04-05", "value_usd": "1000", "filed": "2023-05-01"},
            {"ticker": "T2", "concept": ris.PREFERRED, "period_end": "2024-07-10", "value_usd": "1100", "filed": "2024-05-01"},
        ])
        signals = ris.load_signals(capex_path=capex, revenue_path=revenue)
        tickers = {signal["ticker"] for signal in signals}
        assert tickers == {"T1"}, tickers


def test_signal_waits_for_every_filed_fact():
    with tempfile.TemporaryDirectory() as tmp:
        capex = pathlib.Path(tmp) / "capex.csv"
        revenue = pathlib.Path(tmp) / "revenue.csv"
        write_rows(capex, [
            {"ticker": "T1", "period_end": "2023-03-31", "value_usd": "100", "filed": "2024-06-15"},
            {"ticker": "T1", "period_end": "2024-03-31", "value_usd": "120", "filed": "2024-05-01"},
        ])
        write_rows(revenue, [
            {"ticker": "T1", "concept": ris.PREFERRED, "period_end": "2023-03-31", "value_usd": "1000", "filed": "2024-06-15"},
            {"ticker": "T1", "concept": ris.PREFERRED, "period_end": "2024-03-31", "value_usd": "1100", "filed": "2024-05-01"},
        ])
        signals = ris.load_signals(capex_path=capex, revenue_path=revenue)
        assert len(signals) == 1
        assert signals[0]["filed"] == "2024-06-15"


def test_entry_is_the_first_session_after_the_filing():
    dates = ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
    assert ris.first_session_after(dates, "2024-01-03") == "2024-01-04"
    assert ris.first_session_after(dates, "2024-01-05") is None


def test_costs_use_the_prior_month_volume():
    adv = {"2024-01": 1_000_000.0, "2024-02": 2_000_000.0, "2024-03": 3_000_000.0}
    assert ris.lagged_adv(adv, "2024-03-15") == 2_000_000.0
    assert ris.lagged_adv(adv, "2024-01-05") is None


def test_overlapping_cohorts_share_one_unit_of_capital():
    dates = ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"]
    prices = {
        "A": {"2024-01-04": 100.0, "2024-01-05": 100.0, "2024-01-08": 102.0},
        "B": {"2024-01-04": 100.0, "2024-01-05": 100.0, "2024-01-08": 98.0},
        "C": {"2024-01-04": 100.0, "2024-01-05": 100.0, "2024-01-08": 104.0},
        "D": {"2024-01-04": 100.0, "2024-01-05": 100.0, "2024-01-08": 96.0},
    }
    first = {"start": 2, "horizon": 4, "entry_cost": 0.0, "weights": {"A": 0.5, "B": -0.5}}
    second = {"start": 3, "horizon": 4, "entry_cost": 0.0, "weights": {"C": 0.5, "D": -0.5}}
    open_cohorts = [first, second]
    gross, _ = ris.daily_cohort_pnl(open_cohorts, 4, dates, prices, {}, 1.0)
    assert abs(gross - 0.03) < 1e-9, gross


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} accounting contract(s) held")
