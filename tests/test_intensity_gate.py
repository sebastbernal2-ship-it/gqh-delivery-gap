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
    """Omitting the gate and passing none must be the same run, and the published base must match
    whenever the machine caches every series the signals name."""
    dates, prices = load_prices()
    adv = load_adv()
    panel = json.loads((ROOT / "results" / "market-panel.json").read_text())
    group_of = {series["ticker"]: group
                for group, payload in panel["groups"].items()
                for series in payload["series"]}
    signals = load_signals(ROOT / "results" / "complex-capex-quarterly.csv",
                           ROOT / "results" / "complex-revenue-quarterly.csv")
    omitted = run({**BASE, "target_vol": None}, signals, dates, prices, adv, group_of)
    explicit = run({**BASE, "target_vol": None}, signals, dates, prices, adv, group_of, gate=None)
    assert omitted["metrics"] == explicit["metrics"]              # the identity contract, always
    published = json.loads((ROOT / "results" / "intensity-strategy.json").read_text())["base"]
    assert omitted["cohorts"] == published["cohorts"] == 267
    # The engine builds its daily calendar from every cached series, so its exact metric values depend
    # on the machine's cache depth even though the traded names are fixed. The exact pin therefore runs
    # only where the full local cache exists, and a fresh clone, which holds the committed 66-series
    # subset, checks the identity contract and the cohort structure instead.
    if len(prices) >= 700:
        assert abs(omitted["metrics"]["annual_return"] - published["metrics"]["annual_return"]) < 1e-12
        assert abs(omitted["metrics"]["sharpe"] - published["metrics"]["sharpe"]) < 1e-12
        assert abs(omitted["metrics"]["max_drawdown"] - published["metrics"]["max_drawdown"]) < 1e-12
    else:
        assert omitted["metrics"]["sharpe"] is not None and omitted["cohorts"] > 200
        print("note: %d cached series here, below the full-cache threshold, so the exact pin is "
              "skipped and the identity and cohort contracts stand" % len(prices))


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
