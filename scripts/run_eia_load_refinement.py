#!/usr/bin/env python3
"""Do seasonal, peak and ramp measures of regional load carry more than raw load growth did?

The first grid-load test (T64) ranked regions by 30-day load growth and found no per-name information.
This refinement asks the questions that the physical series actually supports, all strictly
point-in-time and all measured against each authority's own prior-year seasonal window:

  level_surprise     mean demand against the same calendar window in prior years, 30-day mean
  peak_surprise      daily peak against the same window in prior years, 30-day mean
  ramp_surprise      mean hour-to-hour ramp against the same window in prior years, 30-day mean
  acceleration       30-day growth minus the same growth measured 30 days earlier

Three declared tests: the per-name information coefficient of each measure, a monthly cross-sectional
long-short on the best measure, and the incremental test at disclosure events, where the load block is
added to the surviving specialist's own features on the same folds.

    python3 scripts/run_eia_load_refinement.py
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.market_state import load_series  # noqa: E402
from filing_specialist.model import apply_scaler, fit_scaler, fit_softmax, matrix_from_rows, predict_softmax  # noqa: E402
from filing_specialist.portfolio_stats import month_blocked_interval, portfolio_metrics  # noqa: E402
from filing_specialist.rpo_model import FEATURES, prepare_rows  # noqa: E402
from run_eia_load_specialist import EXPOSURE, HORIZON, forward_return, spearman  # noqa: E402
from run_walk_forward import ORIGINS, blocks  # noqa: E402

CACHE = ROOT / "results" / "bar-cache"
FEATURE_NAMES = ("level_surprise", "peak_surprise", "ramp_surprise", "acceleration")
WINDOW = 30
COST_BPS = 20.0


def load_panel(path: Path) -> dict[str, dict[str, dict[str, float]]]:
    panel: dict[str, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    with gzip.open(path, "rt") as handle:
        for row in csv.DictReader(handle):
            month, day, year = row["date"].split("/")
            iso = f"{year}-{month}-{day}"
            for column, name in (("demand_mean", "mean"), ("demand_peak", "peak"),
                                 ("demand_ramp_mean", "ramp")):
                value = row.get(column)
                if value:
                    panel[row["authority"]][name][iso] = float(value)
    return panel


def rolling(values: dict[str, float], day: str, window: int = WINDOW) -> float | None:
    days = sorted(key for key in values if key < day)
    if len(days) < window:
        return None
    recent = days[-window:]
    return statistics.mean(values[key] for key in recent)


def growth(values: dict[str, float], day: str, window: int = WINDOW) -> float | None:
    days = sorted(key for key in values if key < day)
    if len(days) < 2 * window:
        return None
    recent = statistics.mean(values[key] for key in days[-window:])
    prior = statistics.mean(values[key] for key in days[-2 * window:-window])
    return (recent / prior - 1.0) if prior else None


def seasonal_surprise(series: dict[str, float], day: str) -> float | None:
    """The value's 30-day mean against the same calendar window in prior years, point in time."""
    days = sorted(key for key in series if key < day)
    if len(days) < 120:
        return None
    current_year = int(day[:4])
    month_day = day[5:]
    window = days[-WINDOW:]
    prior_points = []
    for key in series:
        year = int(key[:4])
        if year >= current_year:
            continue
        if abs(int(key[5:7]) - int(month_day[:2])) <= 1:
            prior_points.append(series[key])
    if len(prior_points) < 30:
        return None
    current_mean = statistics.mean(series[key] for key in window)
    norm = statistics.mean(prior_points)
    return (current_mean / norm - 1.0) if norm else None


def build_features(panel: dict) -> dict[str, dict[str, dict[str, float]]]:
    features: dict[str, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    for authority, series in panel.items():
        for day in series["mean"]:
            level = seasonal_surprise(series["mean"], day)
            peak = seasonal_surprise(series["peak"], day)
            ramp = seasonal_surprise(series["ramp"], day)
            recent = growth(series["mean"], day)
            earlier = growth(series["mean"], day, window=WINDOW)
            row = features[authority][day]
            if level is not None:
                row["level_surprise"] = level
            if peak is not None:
                row["peak_surprise"] = peak
            if ramp is not None:
                row["ramp_surprise"] = ramp
            if recent is not None and earlier is not None:
                row["acceleration"] = recent - earlier
    return features


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, default=ROOT / "results" / "eia-load-daily.csv.gz")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "eia-load-refinement.json")
    args = parser.parse_args()

    panel = load_panel(args.panel)
    features = build_features(panel)
    prices = {ticker: load_series(ticker, CACHE) for ticker in EXPOSURE}
    prices = {ticker: series for ticker, series in prices.items() if series}

    # test one: per-name information for every measure
    information = {}
    for ticker, series in sorted(prices.items()):
        authority = EXPOSURE[ticker]
        table = features.get(authority, {})
        days = [day for day in sorted(series) if day >= "2019-07-01"][::5]
        per_feature = {}
        for name in FEATURE_NAMES:
            pairs = []
            for day in days:
                candidates = [key for key in table if key < day]
                if not candidates:
                    continue
                value = table[candidates[-1]].get(name)
                outcome = forward_return(series, day)
                if value is not None and outcome is not None:
                    pairs.append((value, outcome))
            per_feature[name] = {"samples": len(pairs),
                                 "ic": spearman([pair[0] for pair in pairs],
                                                [pair[1] for pair in pairs])}
        information[ticker] = {"authority": authority, "features": per_feature}
    summary = {}
    for name in FEATURE_NAMES:
        ics = [block["features"][name]["ic"] for block in information.values()
               if block["features"][name]["ic"] is not None]
        summary[name] = {"tickers": len(ics), "mean_ic": statistics.mean(ics) if ics else None,
                         "median_ic": statistics.median(ics) if ics else None,
                         "share_positive": (sum(1 for value in ics if value > 0) / len(ics))
                         if ics else None}
    best = max((name for name in FEATURE_NAMES if summary[name]["mean_ic"] is not None),
               key=lambda name: abs(summary[name]["mean_ic"])) if summary else None

    # test two: monthly cross-sectional long-short on the best measure
    daily = []
    rebalances = 0
    if best:
        calendar = sorted({day for series in prices.values() for day in series})
        calendar = [day for day in calendar if day >= "2019-07-01"]
        events, last_month = [], None
        for day in calendar:
            if day[:7] != last_month:
                events.append(day)
                last_month = day[:7]
        for day in events:
            ranked = []
            for ticker, series in prices.items():
                table = features.get(EXPOSURE[ticker], {})
                candidates = [key for key in table if key < day]
                if not candidates:
                    continue
                value = table[candidates[-1]].get(best)
                if value is not None:
                    ranked.append((value, ticker))
            if len(ranked) < 6:
                continue
            ranked.sort()
            half = max(1, len(ranked) // 2)
            longs = [ticker for _, ticker in ranked[-half:]]
            shorts = [ticker for _, ticker in ranked[:half]]
            days = sorted({candidate for ticker in longs + shorts
                           for candidate in prices[ticker]})
            after = [candidate for candidate in days if candidate > day]
            if len(after) < HORIZON + 2:
                continue
            window = after[:HORIZON + 1]
            rebalances += 1
            for position in range(1, len(window)):
                current, previous = window[position], window[position - 1]
                leg = []
                for ticker in longs:
                    series = prices[ticker]
                    if current in series and previous in series:
                        leg.append(series[current] / series[previous] - 1.0)
                long_return = statistics.mean(leg) if leg else 0.0
                leg = []
                for ticker in shorts:
                    series = prices[ticker]
                    if current in series and previous in series:
                        leg.append(series[current] / series[previous] - 1.0)
                short_return = statistics.mean(leg) if leg else 0.0
                charge = COST_BPS / 1e4 if position == 1 else 0.0
                daily.append({"date": current, "gross": long_return - short_return,
                              "net": long_return - short_return - charge, "open": float(len(longs) + len(shorts))})
    zero = [{"date": row["date"], "net": 0.0, "gross": 0.0} for row in daily]
    pricing = {"ranking_feature": best, "rebalances": rebalances, "days": len(daily),
               "metrics": portfolio_metrics(daily) if daily else None,
               "interval": month_blocked_interval(daily, zero) if daily else None}

    # test three: does the load block add to the disclosure specialist at its own events?
    rows, _ = prepare_rows(list(csv.DictReader((ROOT / "results" / "revenue-vintages-pit.csv").open())))
    mapped = [row for row in rows if str(row["ticker"]) in EXPOSURE]
    incremental, folds_report = {}, []
    if mapped:
        for name in FEATURE_NAMES:
            losses = {"baseline": [], "with_load": []}
            for start, end in blocks(ORIGINS):
                train = [row for row in mapped if str(row["label_available"])[:10] < start]
                test = [row for row in mapped
                        if start <= str(row["label_available"])[:10] < end]
                if len(train) < 40 or len(test) < 4:
                    continue
                base_matrix, train_labels = matrix_from_rows(train, tuple(FEATURES))
                test_matrix, _ = matrix_from_rows(test, tuple(FEATURES))
                classes = tuple(sorted({int(row["label_bin"]) for row in train}))
                stats = fit_scaler(base_matrix)
                parameters = fit_softmax(apply_scaler(base_matrix, stats), train_labels, classes)
                baseline = predict_softmax(parameters, apply_scaler(test_matrix, stats))
                load_train, load_test = [], []
                for row in train:
                    day = str(row["label_available"])[:10]
                    table = features.get(EXPOSURE[str(row["ticker"])], {})
                    candidates = [key for key in table if key < day]
                    load_train.append(table[candidates[-1]].get(name, 0.0) if candidates else 0.0)
                for row in test:
                    day = str(row["label_available"])[:10]
                    table = features.get(EXPOSURE[str(row["ticker"])], {})
                    candidates = [key for key in table if key < day]
                    load_test.append(table[candidates[-1]].get(name, 0.0) if candidates else 0.0)
                combined_train = np.column_stack([base_matrix, np.array(load_train)])
                combined_test = np.column_stack([test_matrix, np.array(load_test)])
                stats2 = fit_scaler(combined_train)
                parameters2 = fit_softmax(apply_scaler(combined_train, stats2), train_labels, classes)
                with_load = predict_softmax(parameters2, apply_scaler(combined_test, stats2))
                labels = np.array([int(row["label_bin"]) for row in test])

                def loss(probabilities):
                    picked = np.clip(probabilities[np.arange(len(labels)), labels], 1e-12, 1.0)
                    return float(-np.log(picked).mean())
                losses["baseline"].append(loss(baseline))
                losses["with_load"].append(loss(with_load))
            if losses["baseline"]:
                incremental[name] = {
                    "folds": len(losses["baseline"]),
                    "log_loss_baseline": statistics.mean(losses["baseline"]),
                    "log_loss_with_load": statistics.mean(losses["with_load"]),
                    "improved_folds": sum(1 for a, b in zip(losses["baseline"], losses["with_load"])
                                          if b < a)}
    report = {"schema": "eia-load-refinement-v1", "scope": "development_only",
              "protocol": "docs/plan/open-work.md", "events": len(mapped),
              "information": information, "information_summary": summary, "best_feature": best,
              "pricing": pricing, "incremental_at_events": incremental,
              "ready_for_performance_claim": False,
              "limitations": ["development only", "the exposure map is declared, not fitted",
                              "load is demand, not price", "the incremental test uses the mapped names only"]}
    args.output.write_text(json.dumps(report, indent=1) + "\n")

    print("information per measure (mean IC over mapped names):")
    for name in FEATURE_NAMES:
        block = summary[name]
        print("  %-16s mean %+.4f median %+.4f positive %s" % (
            name, block["mean_ic"] or 0.0, block["median_ic"] or 0.0,
            f"{100 * (block['share_positive'] or 0):.0f}%"))
    if pricing["metrics"]:
        metrics = pricing["metrics"]
        interval = pricing["interval"]
        print("pricing on %s: net %+.2f%% sharpe %+.3f dd %+.1f%% | mean %+.4f CI [%+.4f, %+.4f] share+ %.3f" % (
            best, metrics["annual_return"] * 100, metrics["sharpe"], metrics["max_drawdown"] * 100,
            interval["point"], interval["lower"], interval["upper"], interval["share_positive"]))
    print("incremental at %d mapped disclosure events:" % len(mapped))
    for name, block in incremental.items():
        print("  %-16s baseline %.4f -> with_load %.4f | folds improved %d of %d" % (
            name, block["log_loss_baseline"], block["log_loss_with_load"], block["improved_folds"],
            block["folds"]))
    print("written", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
