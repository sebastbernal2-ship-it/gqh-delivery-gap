#!/usr/bin/env python3
"""Contracts for the intensity gate: confirmation semantics and an unchanged default path."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from seed_price_cache import seed  # noqa: E402

seed(quiet=True)          # a fresh clone has no price cache; the committed subset is enough
from run_intensity_strategy import BASE, gate_allows, load_adv, load_prices, load_signals, run  # noqa: E402


def test_confirmation_semantics():
    gate = {("AAA", "2020-01-02"): 1.5, ("BBB", "2020-01-02"): -1.0, ("CCC", "2020-01-02"): 0.0}
    filed = {"AAA": "2020-01-02", "BBB": "2020-01-02", "CCC": "2020-01-02", "DDD": "2020-01-02"}
    assert gate_allows(None, "AAA", filed, 1.0)                       # no gate, no change
    assert gate_allows(gate, "AAA", filed, 1.0)
    assert not gate_allows(gate, "AAA", filed, -1.0)
    assert gate_allows(gate, "BBB", filed, -1.0)
    assert not gate_allows(gate, "BBB", filed, 1.0)
    assert gate_allows(gate, "CCC", filed, 1.0) and gate_allows(gate, "CCC", filed, -1.0)
    assert not gate_allows(gate, "DDD", filed, 1.0)                   # missing data never confirms


def test_the_default_path_is_unchanged():
    """The published base run must reproduce exactly with no gate."""
    dates, prices = load_prices()
    adv = load_adv()
    panel = json.loads((ROOT / "results" / "market-panel.json").read_text())
    group_of = {series["ticker"]: group
                for group, payload in panel["groups"].items()
                for series in payload["series"]}
    signals = load_signals(ROOT / "results" / "complex-capex-quarterly.csv",
                           ROOT / "results" / "complex-revenue-quarterly.csv")
    result = run({**BASE, "target_vol": None}, signals, dates, prices, adv, group_of)
    published = json.loads((ROOT / "results" / "intensity-strategy.json").read_text())["base"]
    assert result["cohorts"] == published["cohorts"] == 267
    assert abs(result["metrics"]["annual_return"] - published["metrics"]["annual_return"]) < 1e-12
    assert abs(result["metrics"]["sharpe"] - published["metrics"]["sharpe"]) < 1e-12
    assert abs(result["metrics"]["max_drawdown"] - published["metrics"]["max_drawdown"]) < 1e-12


def test_a_gate_rejects_the_opposing_leg():
    dates, prices = load_prices()
    adv = load_adv()
    panel = json.loads((ROOT / "results" / "market-panel.json").read_text())
    group_of = {series["ticker"]: group
                for group, payload in panel["groups"].items()
                for series in payload["series"]}
    signals = load_signals(ROOT / "results" / "complex-capex-quarterly.csv",
                           ROOT / "results" / "complex-revenue-quarterly.csv")
    every_signal = {(row["ticker"], row["filed"]): -1.0 for row in signals}
    baseline = run({**BASE, "target_vol": None}, signals, dates, prices, adv, group_of)
    result = run({**BASE, "target_vol": None}, signals, dates, prices, adv, group_of,
                 gate=every_signal)
    assert result["sample_cohort"]["longs"] == 0        # every long leg was rejected
    assert result["sample_cohort"]["shorts"] > 0        # the short legs survive
    assert result["sample_cohort"]["names"] < baseline["sample_cohort"]["names"]
    assert result["metrics"]["annual_return"] != baseline["metrics"]["annual_return"]


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} intensity-gate contract(s) held")
