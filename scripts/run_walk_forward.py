#!/usr/bin/env python3
"""Rolling-origin evaluation of the three sleeves, so no result depends on one split.

Every origin refits the surprise models on rows available before it and scores only the following
block. The intensity sleeve refits its gate model the same way and reruns the engine on the block.
Blocks are then stitched into one continuous daily series per sleeve, and the composite is formed
from those series. Per-year event contributions are reported beside the stitched metrics.

Declared falsifiers: the stitched composite nets zero or less, or its Sharpe is 0.3 or below, or every
block is negative.

    python3 scripts/run_walk_forward.py
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import statistics
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.model import (apply_scaler, fit_scaler, fit_softmax,  # noqa: E402
                                     matrix_from_rows, predict_softmax)
from filing_specialist.portfolio_stats import (month_blocked_interval,  # noqa: E402
                                               portfolio_metrics)
from filing_specialist.rpo_model import FEATURES, prepare_rows  # noqa: E402
from run_intensity_gate_test import CORRECTED, VINTAGES, gate_for  # noqa: E402
from run_intensity_strategy import BASE, load_adv, load_prices, load_signals, run  # noqa: E402
from run_sleeve_portfolio import COSTS, apply_vol_target, sleeve_daily  # noqa: E402
from run_three_sleeve_portfolio import align, inverse_vol_weights, weighted_daily  # noqa: E402

ORIGINS = ("2019-01-01", "2020-01-01", "2021-01-01", "2022-01-01", "2023-01-01",
           "2024-01-01", "2025-01-01", "2026-01-01")
COMPLEX = ROOT / "results" / "market-panel.json"


def blocks(origins: tuple[str, ...] = ORIGINS) -> list[tuple[str, str]]:
    """(start, end) pairs; the last block runs to the data edge."""
    return [(origins[index], origins[index + 1] if index + 1 < len(origins) else "2030-01-01")
            for index in range(len(origins))]


def fit_at(rows: list[dict], origin: str, tickers: set[str] | None = None) -> dict:
    """Fit the declared recipe on rows available before the origin; predict the rest."""
    if tickers is not None:
        rows = [row for row in rows if str(row["ticker"]) in tickers]
    train = [row for row in rows if str(row["label_available"])[:10] < origin]
    later = [row for row in rows if str(row["label_available"])[:10] >= origin]
    if len(train) < 50 or not later:
        return {"train": train, "later": later, "classes": None, "probabilities": None}
    train_matrix, train_labels = matrix_from_rows(train, tuple(FEATURES))
    later_matrix, _ = matrix_from_rows(later, tuple(FEATURES))
    classes = tuple(sorted({int(row["label_bin"]) for row in train}))
    stats = fit_scaler(train_matrix)
    parameters = fit_softmax(apply_scaler(train_matrix, stats), train_labels, classes)
    return {"train": train, "later": later, "classes": classes,
            "probabilities": predict_softmax(parameters, apply_scaler(later_matrix, stats))}




def scaled_conviction(conviction: float, z: float | None, reference: float = 2.0) -> float:
    """The declared T58 decoupling: the raw model selects and signs the trade, the standardized
    surprise caps its size. Without a z the conviction is unchanged, so the default path is identical.
    """
    if z is None:
        return conviction
    return conviction * min(1.0, abs(z) / reference)


def load_size_lookup(panel: Path) -> dict:
    """Standardized surprises keyed by (ticker, decision date) for the decoupled sizing variant."""
    lookup = {}
    for row in csv.DictReader(panel.open()):
        raw = row.get("relative_surprise_z")
        if raw in (None, ""):
            continue
        ticker = (row.get("ticker") or "").strip()
        available = str(row.get("availability") or "")[:10]
        if ticker and available:
            lookup[(ticker, available)] = float(raw)
    return lookup


def sleeve_walk_forward(panel: Path, direction: float, tickers: set[str] | None = None,
                        origins: tuple[str, ...] = ORIGINS, size_lookup: dict | None = None
                        ) -> tuple[list[dict], list[dict], dict]:
    """One continuous event list and a per-block contribution table for one sleeve."""
    rows, _ = prepare_rows(list(csv.DictReader(panel.open())))
    events, contributions, digests = [], [], {}
    for start, end in blocks(origins):
        fitted = fit_at(rows, start, tickers)
        if fitted["probabilities"] is None:
            continue
        digests[start] = len(fitted["train"])
        for row, values in zip(fitted["later"], fitted["probabilities"]):
            decision = str(row["label_available"])[:10]
            if not (start <= decision < end):
                continue
            expected = sum(k * float(p) for k, p in zip(fitted["classes"], values))
            conviction = direction * (expected - 2.0) / 2.0
            if size_lookup is not None:
                conviction = scaled_conviction(conviction,
                                               size_lookup.get((str(row["ticker"]), decision)))
            if abs(conviction) < 1e-9:
                continue
            events.append({"ticker": str(row["ticker"]), "decision": decision,
                           "weight": conviction, "period_end": str(row["period_end"]),
                           "block": start})
        contributions.append({"block": start, "events": len(fitted["later"])})
    return events, contributions, digests


def contributions_by_year(events: list[dict], cache: Path, cost_bps: float) -> list[dict]:
    """Mean per-event net contribution by calendar year, on the frozen weights."""
    daily_by_block, _ = sleeve_daily(events, cache, cost_bps)
    return daily_by_block


def intensity_walk_forward(cost_mult: float, tickers: set[str] | None = None,
                           origins: tuple[str, ...] = ORIGINS) -> tuple[list[dict], dict]:
    """Rerun the gated engine block by block with the gate model refit at each origin."""
    dates, prices = load_prices()
    adv = load_adv()
    panel = json.loads(COMPLEX.read_text())
    group_of = {series["ticker"]: group for group, payload in panel["groups"].items()
                for series in payload["series"]}
    signals = load_signals(CORRECTED["capex"], CORRECTED["revenue"])
    if tickers is not None:
        signals = [signal for signal in signals if signal["ticker"] in tickers]
    revenue_rows, _ = prepare_rows(list(csv.DictReader(VINTAGES["revenue"].open())))
    stitched, info = [], {}
    for start, end in blocks(origins):
        fitted = fit_at(revenue_rows, start, tickers)
        if fitted["probabilities"] is None:
            continue
        expected = {}
        for row, values in zip(fitted["later"], fitted["probabilities"]):
            decision = str(row["label_available"])[:10]
            if start <= decision < end:
                score = sum(k * float(p) for k, p in zip(fitted["classes"], values))
                expected[(str(row["ticker"]), decision)] = score
        gate = gate_for(expected, signals, centre=2.0)
        window = [date for date in dates if start <= date < end]
        if len(window) < 40 or not gate:
            continue
        result = run({**BASE, "cost_mult": cost_mult, "target_vol": None}, signals, window,
                     prices, adv, group_of, gate=gate)
        stitched.extend(result["daily"])
        info[start] = {"signals_with_a_gate": len(gate), "cohorts": result["cohorts"]}
    return stitched, info


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revenue", type=Path, default=ROOT / "results" / "revenue-vintages-pit.csv")
    parser.add_argument("--capex", type=Path, default=ROOT / "results" / "capex-vintages-pit.csv")
    parser.add_argument("--cache", type=Path, default=ROOT / "results" / "bar-cache")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "walk-forward.json")
    parser.add_argument("--size-panel", type=Path, default=None,
                        help="standardized surprises for the decoupled sizing variant (declared in T58)")
    args = parser.parse_args()

    report = {"schema": "walk-forward-v1", "scope": "development_only",
              "protocol": "docs/plan/open-work.md", "origins": list(ORIGINS), "sleeves": {},
              "falsifiers": ["stitched composite nets zero or less",
                             "stitched composite Sharpe 0.3 or below",
                             "every block negative"],
              "ready_for_performance_claim": False,
              "limitations": [
                  "development only; both sealed windows are spent",
                  "complex names only; block boundaries leave up to twenty sessions of overlap",
                  "flat costs on the driver sleeves, volume buckets on the intensity sleeve",
              ]}
    series = {}
    size_lookup = load_size_lookup(args.size_panel) if args.size_panel else None
    report["size_panel"] = str(args.size_panel) if args.size_panel else None
    for name, panel, direction in (("revenue", args.revenue, 1.0), ("capex", args.capex, -1.0)):
        events, contributions, digests = sleeve_walk_forward(
            panel, direction, size_lookup=size_lookup if name == "revenue" else None)
        daily, info = sleeve_daily(events, args.cache, COSTS["base"])
        series[name] = daily
        report["sleeves"][name] = {
            "events": len(events), "sessions": info.get("sessions"), "blocks": contributions,
            "training_rows_by_origin": digests, "metrics": portfolio_metrics(daily)}
    intensity, intensity_info = intensity_walk_forward(1.0)
    series["intensity_gated"] = [{"date": row["date"], "net": row["net"], "gross": row["gross"]}
                                 for row in intensity]
    report["sleeves"]["intensity_gated"] = {"blocks": intensity_info,
                                            "metrics": portfolio_metrics(series["intensity_gated"])}

    names = ["revenue", "capex", "intensity_gated"]
    dates, values = align([series[name] for name in names])
    report["common_window"] = {"from": dates[0], "to": dates[-1], "sessions": len(dates)}
    equal = [[1 / 3] * len(dates) for _ in names]
    inverse = inverse_vol_weights(values)
    for label, weights in (("equal_gross", equal), ("inverse_vol", inverse)):
        combined = weighted_daily(dates, values, weights)
        report.setdefault("portfolio_daily", {})[label] = combined
        report.setdefault("portfolios", {})[label] = {
            "metrics": portfolio_metrics(combined),
            "metrics_vol_target": portfolio_metrics(apply_vol_target(combined, 0.10)),
            "weights_mean": [round(statistics.mean(w), 3) for w in weights]}
        if label == "inverse_vol":
            report["intervals"] = {
                "composite_minus_revenue": month_blocked_interval(combined, series["revenue"]),
                "composite_minus_capex": month_blocked_interval(combined, series["capex"]),
                "composite_minus_intensity": month_blocked_interval(combined, series["intensity_gated"]),
            }
    # the capex decision, in the same harness: does dropping the losing sleeve help?
    two_names = ["revenue", "intensity_gated"]
    two_values = [values[names.index(name)] for name in two_names]
    two_inverse = inverse_vol_weights(two_values)
    two_combined = weighted_daily(dates, two_values, two_inverse)
    report.setdefault("portfolio_daily", {})["without_capex_inverse_vol"] = two_combined
    report["without_capex"] = {
        "inverse_vol": {"metrics": portfolio_metrics(two_combined),
                        "metrics_vol_target": portfolio_metrics(apply_vol_target(two_combined, 0.10)),
                        "weights_mean": [round(statistics.mean(w), 3) for w in two_inverse]},
        "equal_gross": {"metrics": portfolio_metrics(
            weighted_daily(dates, two_values, [[0.5] * len(dates), [0.5] * len(dates)]))},
    }
    report["yearly_contributions"] = {}
    for name in ("revenue", "capex"):
        rows, _ = prepare_rows(list(csv.DictReader((args.revenue if name == "revenue" else args.capex).open())))
        events, _, _ = sleeve_walk_forward(
            args.revenue if name == "revenue" else args.capex,
            1.0 if name == "revenue" else -1.0,
            size_lookup=size_lookup if name == "revenue" else None)
        daily, _ = sleeve_daily(events, args.cache, COSTS["base"])
        by_year: dict[str, list[float]] = {}
        for row in daily:
            by_year.setdefault(row["date"][:4], []).append(row["net"])
        report["yearly_contributions"][name] = {
            year: round(statistics.mean(values) * 252, 4) for year, values in sorted(by_year.items())}
    args.output.write_text(json.dumps(report, indent=1) + "\n")

    print("sleeve metrics, stitched walk-forward")
    for name in names:
        m = report["sleeves"][name]["metrics"]
        print("  %-16s days %4d net %+7.2f%% vol %6.1f%% sharpe %+6.3f maxDD %+7.1f%%" % (
            name, m["days"], m["annual_return"] * 100, m["annual_vol"] * 100,
            m["sharpe"] or float("nan"), m["max_drawdown"] * 100))
    print("common window", report["common_window"])
    for label in ("equal_gross", "inverse_vol"):
        m = report["portfolios"][label]["metrics"]
        v = report["portfolios"][label]["metrics_vol_target"]
        print("  %-12s net %+7.2f%% vol %6.1f%% sharpe %+6.3f maxDD %+7.1f%% | vol-targeted %+7.2f%% %6.1f%% %+6.3f %+7.1f%%" % (
            label, m["annual_return"] * 100, m["annual_vol"] * 100, m["sharpe"] or float("nan"),
            m["max_drawdown"] * 100, v["annual_return"] * 100, v["annual_vol"] * 100,
            v["sharpe"] or float("nan"), v["max_drawdown"] * 100))
    two = report["without_capex"]["inverse_vol"]
    m = two["metrics"]
    v = two["metrics_vol_target"]
    print("  without capex (inverse-vol, mean weights %s): net %+7.2f%% vol %6.1f%% sharpe %+6.3f maxDD %+7.1f%% | vol-targeted %+7.2f%% sharpe %+6.3f maxDD %+7.1f%%" % (
        two["weights_mean"], m["annual_return"] * 100, m["annual_vol"] * 100,
        m["sharpe"] or float("nan"), m["max_drawdown"] * 100,
        v["annual_return"] * 100, v["sharpe"] or float("nan"), v["max_drawdown"] * 100))
    equal_two = report["without_capex"]["equal_gross"]["metrics"]
    print("  without capex (equal gross): net %+7.2f%% sharpe %+6.3f maxDD %+7.1f%%" % (
        equal_two["annual_return"] * 100, equal_two["sharpe"] or float("nan"),
        equal_two["max_drawdown"] * 100))
    for name, yearly in report["yearly_contributions"].items():
        print("  yearly net, " + name + ":", json.dumps(yearly))
    print("written", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
