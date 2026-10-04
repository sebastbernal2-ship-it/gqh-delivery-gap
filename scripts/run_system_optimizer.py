#!/usr/bin/env python3
"""Optimise the whole expression as one unit instead of one arm at a time.

Every earlier result changed one arm and froze the rest. That is coordinate descent: it cannot see
interactions, and this system has obvious ones, because a better leg only matters at the portfolio
weight the blend gives it, and a stricter gate only matters at the horizon the engine holds for.

Declared parameter space, six dimensions, all small on purpose:

  horizon          holding period, 10, 20 or 30 sessions          (both sleeves move together)
  gate_threshold   confirmation strictness, none, 0.5 or 1.0      (expected-class distance from middle)
  w_intensity      portfolio weight on the charge sleeve, 0.40 to 0.85
  vol_target       none, 0.10 or 0.14                             (composite volatility target)
  sizing_gamma     conviction shaping, 0.5, 1.0 or 1.5            (|conviction| ** gamma)
  entry_threshold  minimum conviction to act, 0.0, 0.10 or 0.20

Protocol: expanding-window refits. For each evaluation year from 2022, the parameter set that maximises
net Sharpe on everything strictly before that year is chosen from a declared random sample of the grid
(fixed seed), then applied to that year only. The stitched series is one out-of-sample path, compared
against the frozen baseline configuration and against constant long exposure at every disclosure event.

    python3 scripts/run_system_optimizer.py
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.portfolio_stats import month_blocked_interval, portfolio_metrics  # noqa: E402
from filing_specialist.rpo_model import FEATURES  # noqa: E402
from run_intensity_gate_test import CORRECTED, gate_for  # noqa: E402
from run_intensity_strategy import BASE, load_adv, load_prices, load_signals, run  # noqa: E402
from run_sleeve_portfolio import COSTS  # noqa: E402
from run_three_sleeve_portfolio import align, apply_vol_target, weighted_daily  # noqa: E402
from run_walk_forward import ORIGINS, blocks  # noqa: E402

EVAL_YEARS = ("2022", "2023", "2024", "2025", "2026")
SAMPLE_SIZE = 120
SEED = 20261004
# the published configuration: the disclosure expectation confirms the charge legs, twenty-session
# holds, the two sleeves blended near inverse-vol weights, no volatility target, flat sizing
BASELINE = {"horizon": 20, "gate_threshold": 0.0, "w_intensity": 0.78, "vol_target": None,
            "sizing_gamma": 1.0, "entry_threshold": 0.0}


def disclosure_scores(cache: Path) -> list[dict]:
    """Out-of-sample expected classes for every disclosure event, once, so sizing is a cheap map."""
    import csv
    sys.path.insert(0, str(ROOT / "scripts"))
    from filing_specialist.model import apply_scaler, fit_scaler, fit_softmax, matrix_from_rows, predict_softmax
    from filing_specialist.rpo_model import prepare_rows
    rows, _ = prepare_rows(list(csv.DictReader((ROOT / "results" / "revenue-vintages-pit.csv").open())))
    events = []
    for start, end in blocks(ORIGINS):
        train = [row for row in rows if str(row["label_available"])[:10] < start]
        later = [row for row in rows if start <= str(row["label_available"])[:10] < end]
        if len(train) < 40 or not later:
            continue
        train_matrix, train_labels = matrix_from_rows(train, tuple(FEATURES))
        test_matrix, _ = matrix_from_rows(later, tuple(FEATURES))
        classes = tuple(sorted({int(row["label_bin"]) for row in train}))
        stats = fit_scaler(train_matrix)
        parameters = fit_softmax(apply_scaler(train_matrix, stats), train_labels, classes)
        probabilities = predict_softmax(parameters, apply_scaler(test_matrix, stats))
        for row, values in zip(later, probabilities):
            expected = sum(k * float(p) for k, p in zip(classes, values))
            events.append({"ticker": str(row["ticker"]), "decision": str(row["label_available"])[:10],
                           "expected": expected, "period_end": str(row["period_end"])})
    return events


def disclosure_daily(events: list[dict], params: dict, cache: Path) -> list[dict]:
    import run_sleeve_portfolio as sleeve
    original = sleeve.HORIZON
    sleeve.HORIZON = params["horizon"]
    try:
        prepared = []
        for event in events:
            conviction = (event["expected"] - 2.0) / 2.0
            shaped = math.copysign(abs(conviction) ** params["sizing_gamma"], conviction)
            if abs(shaped) < params["entry_threshold"]:
                continue
            prepared.append({"ticker": event["ticker"], "decision": event["decision"],
                             "weight": shaped, "period_end": event["period_end"]})
        daily, _ = sleeve.sleeve_daily(prepared, cache, COSTS["base"])
    finally:
        sleeve.HORIZON = original
    return daily


def intensity_daily(params: dict, signals, window, prices, adv, group_of,
                    events: list[dict]) -> list[dict]:
    extra = {**BASE, "horizon": params["horizon"], "target_vol": None}
    gate = None
    if params["gate_threshold"] is not None:
        # the confirmation comes from the disclosure model's expectation for the same issuer, resolved
        # to each signal's filing date exactly as the T44 gate test does
        by_ticker: dict[str, list[dict]] = {}
        for event in events:
            by_ticker.setdefault(event["ticker"], []).append(event)
        for ticker in by_ticker:
            by_ticker[ticker].sort(key=lambda event: event["decision"])
        scores = {}
        for signal in signals:
            known = [event for event in by_ticker.get(signal["ticker"], [])
                     if event["decision"] <= signal["filed"]]
            if known:
                scores[(signal["ticker"], signal["filed"])] = known[-1]["expected"]
        gate = gate_for(scores, signals, centre=2.0) if scores else None
        if gate is not None:
            threshold = params["gate_threshold"]
            gate = {key: value for key, value in gate.items() if abs(value) >= threshold} or None
    result = run(extra, signals, window, prices, adv, group_of, gate=gate)
    return result.get("daily", [])


def composite(daily_by_sleeve: list[list[dict]], params: dict) -> list[dict]:
    dates, values = align(daily_by_sleeve)
    weight = params["w_intensity"]
    weights = [[1.0 - weight] * len(dates), [weight] * len(dates)]
    combined = weighted_daily(dates, values, weights)
    if params["vol_target"]:
        combined = apply_vol_target(combined, params["vol_target"])
    return combined


def subset(daily: list[dict], start: str | None = None, end: str | None = None) -> list[dict]:
    return [row for row in daily if (start is None or row["date"] >= start)
            and (end is None or row["date"] < end)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / "results" / "bar-cache")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "system-optimizer.json")
    parser.add_argument("--sample", type=int, default=SAMPLE_SIZE,
                        help="declared random sample of the parameter grid")
    args = parser.parse_args()

    events = disclosure_scores(args.cache)
    dates, prices = load_prices()
    adv = load_adv()
    panel = json.loads((ROOT / "results" / "market-panel.json").read_text())
    group_of = {series["ticker"]: group for group, payload in panel["groups"].items()
                for series in payload["series"]}
    signals = load_signals(CORRECTED["capex"], CORRECTED["revenue"])
    window = [day for day in dates if day >= "2019-02-01"]   # the sleeves' own common start, not the
                                                             # narrower T44 gate-test window

    rng = np.random.default_rng(SEED)
    grid = []
    for _ in range(args.sample):
        grid.append({
            "horizon": int(rng.choice([10, 20, 30])),
            "gate_threshold": None if rng.random() < 0.25 else float(rng.choice([0.0, 0.5, 1.0])),
            "w_intensity": float(round(rng.uniform(0.40, 0.85), 3)),
            "vol_target": None if rng.random() < 0.4 else float(rng.choice([0.10, 0.14])),
            "sizing_gamma": float(rng.choice([0.5, 1.0, 1.5])),
            "entry_threshold": float(rng.choice([0.0, 0.10, 0.20])),
        })
    grid.append(dict(BASELINE))
    cache: dict[str, list[dict]] = {}

    def evaluate(params: dict) -> list[dict]:
        key = json.dumps(params, sort_keys=True)
        if key not in cache:
            disclosure = disclosure_daily(events, params, args.cache)
            intensity = intensity_daily(params, signals, window, prices, adv, group_of, events)
            cache[key] = composite([disclosure, intensity], params)
        return cache[key]

    stitched, choices = [], []
    for year in EVAL_YEARS:
        train_window = ("2019-01-01", f"{year}-01-01")
        best, best_score = None, None
        for params in grid:
            daily = evaluate(params)
            training = subset(daily, *train_window)
            if len(training) < 200:
                continue
            metrics = portfolio_metrics(training)
            score = (metrics["sharpe"], metrics["annual_return"])
            if best_score is None or score > best_score:
                best, best_score = params, score
        if best is None:
            continue
        chosen = dict(best)
        evaluation = subset(evaluate(chosen), f"{year}-01-01", f"{int(year) + 1}-01-01")
        stitched.extend(evaluation)
        choices.append({"year": year, "params": chosen, "train_sharpe": round(best_score[0], 3),
                        "train_days": len(subset(evaluate(chosen), *train_window))})

    baseline_daily = subset(evaluate(dict(BASELINE)), "2022-01-01", None)
    long_events = [{"ticker": event["ticker"], "decision": event["decision"], "weight": 1.0,
                    "period_end": event["period_end"]} for event in events]
    import run_sleeve_portfolio as sleeve
    sleeve.HORIZON = BASELINE["horizon"]
    long_daily_all, _ = sleeve.sleeve_daily(long_events, args.cache, COSTS["base"])
    long_daily = subset(long_daily_all, "2022-01-01", None)

    report = {"schema": "system-optimizer-v1", "scope": "development_only",
              "protocol": "docs/plan/open-work.md",
              "space": {"horizon": [10, 20, 30], "gate_threshold": [None, 0.0, 0.5, 1.0],
                        "w_intensity": "uniform 0.40 to 0.85", "vol_target": [None, 0.10, 0.14],
                        "sizing_gamma": [0.5, 1.0, 1.5], "entry_threshold": [0.0, 0.10, 0.20],
                        "sample": args.sample, "seed": SEED},
              "objective": "net Sharpe on all data strictly before the evaluation year, base costs",
              "choices": choices,
              "optimised": {"days": len(stitched), "metrics": portfolio_metrics(stitched) if stitched else None},
              "baseline": {"days": len(baseline_daily), "metrics": portfolio_metrics(baseline_daily)},
              "constant_long": {"days": len(long_daily), "metrics": portfolio_metrics(long_daily)},
              "interval_optimised_minus_baseline": month_blocked_interval(stitched, baseline_daily)
              if stitched else None,
              "interval_optimised_minus_long": month_blocked_interval(stitched, long_daily)
              if stitched else None,
              "ready_for_performance_claim": False,
              "limitations": ["development only; the parameter sample is declared and finite",
                              "the same evaluation years were used in earlier one-arm tests, so this is "
                              "still development evidence",
                              "costs are flat and base tier only in the search objective"]}
    args.output.write_text(json.dumps(report, indent=1) + "\n")

    print("chosen parameters by evaluation year:")
    for choice in choices:
        params = choice["params"]
        print("  %s horizon %2d gate %-4s w %.2f vol %-4s gamma %.1f entry %.2f | train sharpe %.3f" % (
            choice["year"], params["horizon"], str(params["gate_threshold"]),
            params["w_intensity"], str(params["vol_target"]), params["sizing_gamma"],
            params["entry_threshold"], choice["train_sharpe"]))
    for label in ("optimised", "baseline", "constant_long"):
        metrics = report[label]["metrics"]
        print("%-13s net %+7.2f%% vol %5.1f%% sharpe %+6.3f dd %+6.1f%%" % (
            label, metrics["annual_return"] * 100, metrics["annual_vol"] * 100, metrics["sharpe"],
            metrics["max_drawdown"] * 100))
    for label in ("interval_optimised_minus_baseline", "interval_optimised_minus_long"):
        interval = report[label]
        print("%s: point %+.4f CI [%+.4f, %+.4f] share+ %.3f" % (
            label, interval["point"], interval["lower"], interval["upper"], interval["share_positive"]))
    print("written", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
