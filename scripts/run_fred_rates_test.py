#!/usr/bin/env python3
"""Do rates, credit and fuel prices inform the complex, condition its sleeve, or help at its events?

Three declared tests, the same discipline the load family got, and the constant-long floor applied.

  aggregate timing   the equal-weight complex basket against the same point-in-time rate features
  sleeve conditioning whether the disclosure sleeve's returns differ across rate regimes, and whether
                     a regime rule chosen on earlier data and applied later beats holding it flat
  event incremental  adding the rate block to the disclosure specialist's features at its own events

Features per series: the 250-day z-score, the 20-day change and the 60-day change, all read with the
panel's declared one-observation publication lag.

    python3 scripts/run_fred_rates_test.py
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import statistics
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.market_state import load_series  # noqa: E402
from filing_specialist.model import (apply_scaler, fit_scaler, fit_softmax, matrix_from_rows,  # noqa: E402
                                     predict_softmax)
from filing_specialist.portfolio_stats import month_blocked_interval, portfolio_metrics  # noqa: E402
from filing_specialist.rpo_model import FEATURES, prepare_rows  # noqa: E402
from run_sleeve_portfolio import COSTS  # noqa: E402
from run_system_optimizer import BASELINE, disclosure_daily, disclosure_scores  # noqa: E402
from run_walk_forward import ORIGINS, blocks  # noqa: E402

CACHE = ROOT / "results" / "bar-cache"
SERIES = ("DFII10", "T10Y2Y", "BAA10Y", "DHHNGSP", "VIXCLS")
HORIZON = 20
EVAL_YEARS = ("2022", "2023", "2024", "2025", "2026")


def load_panel(path: Path) -> dict[str, dict[str, float]]:
    panel = {}
    with gzip.open(path, "rt") as handle:
        for row in csv.DictReader(handle):
            panel[row["date"]] = {name: float(row[name]) for name in SERIES if row.get(name)}
    return panel


def feature_table(panel: dict[str, dict[str, float]]) -> dict[str, dict[str, dict[str, float]]]:
    """Per series, per day: level z-score over 250 days, 20-day and 60-day changes."""
    table: dict[str, dict[str, dict[str, float]]] = {name: {} for name in SERIES}
    for name in SERIES:
        series = {day: values[name] for day, values in panel.items() if name in values}
        days = sorted(series)
        for position, day in enumerate(days):
            if position < 60:
                continue
            window = [series[days[index]] for index in range(max(0, position - 250), position)]
            mean = statistics.mean(window) if window else None
            deviation = statistics.pstdev(window) if len(window) > 20 else None
            row = {"level_z": (series[day] - mean) / deviation if deviation else None,
                   "change_20": series[day] - series[days[position - 20]],
                   "change_60": series[day] - series[days[position - 60]]}
            if all(value is not None for value in row.values()):
                table[name][day] = row
    return table


def basket_returns(tickers: set[str]) -> dict[str, float]:
    series = {ticker: load_series(ticker, CACHE) for ticker in tickers}
    series = {ticker: prices for ticker, prices in series.items() if prices}
    calendar = sorted({day for prices in series.values() for day in prices})
    daily = {}
    for position in range(1, len(calendar)):
        previous, day = calendar[position - 1], calendar[position]
        returns = [prices[day] / prices[previous] - 1.0 for prices in series.values()
                   if day in prices and previous in prices]
        if returns:
            daily[day] = statistics.mean(returns)
    return daily


def forward_basket(daily: dict[str, float], day: str, horizon: int = HORIZON) -> float | None:
    days = sorted(key for key in daily if key >= day)
    if len(days) < 2:
        return None
    window = days[:horizon]
    return math.prod(1.0 + daily[key] for key in window) - 1.0


def spearman(left: list[float], right: list[float]) -> float | None:
    if len(left) < 8:
        return None

    def ranks(values):
        order = sorted(range(len(values)), key=lambda position: values[position])
        out = [0.0] * len(values)
        for rank, position in enumerate(order):
            out[position] = float(rank)
        return out

    x, y = ranks(left), ranks(right)
    mx, my = statistics.mean(x), statistics.mean(y)
    numerator = sum((a - mx) * (b - my) for a, b in zip(x, y))
    denominator = (sum((a - mx) ** 2 for a in x) ** 0.5) * (sum((b - my) ** 2 for b in y) ** 0.5)
    return numerator / denominator if denominator else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, default=ROOT / "results" / "fred-panel.csv.gz")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "fred-rates-test.json")
    args = parser.parse_args()

    panel = load_panel(args.panel)
    table = feature_table(panel)
    tickers = set()
    for name in ("revenue-vintages-pit.csv", "capex-vintages-pit.csv"):
        path = ROOT / "results" / name
        if path.exists():
            tickers |= {row["ticker"] for row in csv.DictReader(path.open())}
    available = {ticker for ticker in tickers if (CACHE / f"{ticker}.json").exists()}
    basket = basket_returns(available)

    # test one: aggregate timing
    information = {}
    for name in SERIES:
        for feature in ("level_z", "change_20", "change_60"):
            pairs = []
            for day in sorted(basket)[::5]:
                if day < "2019-01-01":
                    continue
                candidates = [key for key in table[name] if key < day]
                if not candidates:
                    continue
                value = table[name][candidates[-1]].get(feature)
                outcome = forward_basket(basket, day)
                if value is not None and outcome is not None:
                    pairs.append((value, outcome))
            information[f"{name}.{feature}"] = {
                "samples": len(pairs),
                "ic": spearman([pair[0] for pair in pairs], [pair[1] for pair in pairs])}
    ranked = sorted((abs(block["ic"]), name) for name, block in information.items()
                    if block["ic"] is not None)
    best_key = ranked[-1][1] if ranked else None

    def rule_series(multipliers: dict[str, float], key: str) -> list[dict]:
        name, feature = key.split(".")
        daily = []
        for day in sorted(basket):
            if day < "2019-01-01":
                continue
            candidates = [token for token in table[name] if token < day]
            if not candidates:
                continue
            value = table[name][candidates[-1]].get(feature)
            if value is None:
                continue
            regime = "high" if value > 1.0 else ("low" if value < -1.0 else "mid")
            daily.append({"date": day, "gross": basket[day] * multipliers[regime],
                          "net": basket[day] * multipliers[regime]})
        return daily

    timing = {}
    if best_key:
        options = [{"high": 0.5, "mid": 1.0, "low": 1.0}, {"high": 0.0, "mid": 1.0, "low": 1.0},
                   {"high": 0.5, "mid": 1.0, "low": 0.5}, {"high": 1.0, "mid": 1.0, "low": 1.0}]
        stitched = []
        for year in EVAL_YEARS:
            best, best_sharpe = None, None
            for multipliers in options:
                training = [row for row in rule_series(multipliers, best_key)
                            if row["date"] < f"{year}-01-01"]
                if len(training) < 200:
                    continue
                sharpe = portfolio_metrics(training)["sharpe"]
                if best_sharpe is None or sharpe > best_sharpe:
                    best, best_sharpe = multipliers, sharpe
            if best is None:
                continue
            chosen = rule_series(best, best_key)
            stitched.extend([row for row in chosen if f"{year}-01-01" <= row["date"] < f"{int(year) + 1}-01-01"])
        always = [{"date": day, "gross": basket[day], "net": basket[day]}
                  for day in sorted(basket) if day >= "2022-01-01"]
        timing = {"feature": best_key, "optimised": {"days": len(stitched),
                                                     "metrics": portfolio_metrics(stitched) if stitched else None},
                  "always_long": {"days": len(always), "metrics": portfolio_metrics(always)},
                  "interval": month_blocked_interval(stitched, always) if stitched else None}

    # test two: sleeve conditioning across regimes, and the constant-long floor
    events = disclosure_scores(CACHE)
    sleeve_daily_series = disclosure_daily(events, dict(BASELINE), CACHE)
    long_events = [{"ticker": event["ticker"], "decision": event["decision"], "weight": 1.0,
                    "period_end": event["period_end"]} for event in events]
    import run_sleeve_portfolio as sleeve_module
    long_daily_all, _ = sleeve_module.sleeve_daily(long_events, CACHE, COSTS["base"])
    conditioning = {"regimes": {}}
    if best_key:
        name = best_key.split(".")[0]
        feature = best_key.split(".")[1]
        buckets: dict[str, list[dict]] = {"high": [], "mid": [], "low": []}
        for row in sleeve_daily_series:
            candidates = [token for token in table[name] if token < row["date"]]
            if not candidates:
                continue
            value = table[name][candidates[-1]].get(feature)
            if value is None:
                continue
            regime = "high" if value > 1.0 else ("low" if value < -1.0 else "mid")
            buckets[regime].append(row)
        for regime, rows in buckets.items():
            if rows:
                conditioning["regimes"][regime] = {"days": len(rows),
                                                   "metrics": portfolio_metrics(rows)}
        conditioning["constant_long"] = {"metrics": portfolio_metrics(long_daily_all)}

    # test three: incremental at the disclosure events
    rows, _ = prepare_rows(list(csv.DictReader((ROOT / "results" / "revenue-vintages-pit.csv").open())))
    incremental = {}
    for name in SERIES:
        for feature in ("level_z", "change_60"):
            losses = {"baseline": [], "with_rates": []}
            for start, end in blocks(ORIGINS):
                train = [row for row in rows if str(row["label_available"])[:10] < start]
                test = [row for row in rows if start <= str(row["label_available"])[:10] < end]
                if len(train) < 40 or len(test) < 5:
                    continue
                base_train, train_labels = matrix_from_rows(train, tuple(FEATURES))
                base_test, _ = matrix_from_rows(test, tuple(FEATURES))
                classes = tuple(sorted({int(row["label_bin"]) for row in train}))
                stats = fit_scaler(base_train)
                parameters = fit_softmax(apply_scaler(base_train, stats), train_labels, classes)
                baseline = predict_softmax(parameters, apply_scaler(base_test, stats))

                def added(rows_subset):
                    values = []
                    for row in rows_subset:
                        day = str(row["label_available"])[:10]
                        candidates = [token for token in table[name] if token < day]
                        values.append(table[name][candidates[-1]].get(feature, 0.0)
                                      if candidates else 0.0)
                    return np.array(values)
                combined_train = np.column_stack([base_train, added(train)])
                combined_test = np.column_stack([base_test, added(test)])
                stats2 = fit_scaler(combined_train)
                parameters2 = fit_softmax(apply_scaler(combined_train, stats2), train_labels, classes)
                with_rates = predict_softmax(parameters2, apply_scaler(combined_test, stats2))
                labels = np.array([int(row["label_bin"]) for row in test])

                def loss(probabilities):
                    picked = np.clip(probabilities[np.arange(len(labels)), labels], 1e-12, 1.0)
                    return float(-np.log(picked).mean())
                losses["baseline"].append(loss(baseline))
                losses["with_rates"].append(loss(with_rates))
            if losses["baseline"]:
                incremental[f"{name}.{feature}"] = {
                    "folds": len(losses["baseline"]),
                    "log_loss_baseline": statistics.mean(losses["baseline"]),
                    "log_loss_with_rates": statistics.mean(losses["with_rates"]),
                    "improved_folds": sum(1 for a, b in zip(losses["baseline"], losses["with_rates"])
                                          if b < a)}

    report = {"schema": "fred-rates-test-v1", "scope": "development_only",
              "protocol": "docs/plan/open-work.md", "basket_tickers": len(available),
              "information": information, "best_feature": best_key, "timing": timing,
              "conditioning": conditioning, "incremental_at_events": incremental,
              "ready_for_performance_claim": False,
              "limitations": ["development only", "one-observation publication lag is an approximation "
                              "of the real vintage clock", "the credit spread series is short on the "
                              "free endpoint", "the timing rule uses three regimes and four options"]}
    args.output.write_text(json.dumps(report, indent=1) + "\n")

    print("aggregate information, top six by |IC|:")
    for magnitude, key in ranked[-6:]:
        block = information[key]
        print("  %-22s IC %+.4f  samples %d" % (key, block["ic"], block["samples"]))
    if timing:
        optimised = timing["optimised"]["metrics"]
        always = timing["always_long"]["metrics"]
        print("timing on %s: optimised net %+.2f%% sharpe %+.3f | always long net %+.2f%% sharpe %+.3f" % (
            timing["feature"], optimised["annual_return"] * 100, optimised["sharpe"],
            always["annual_return"] * 100, always["sharpe"]))
        interval = timing["interval"]
        print("  optimised minus always long: point %+.4f CI [%+.4f, %+.4f] share+ %.3f" % (
            interval["point"], interval["lower"], interval["upper"], interval["share_positive"]))
    print("sleeve by rate regime:")
    for regime, block in conditioning.get("regimes", {}).items():
        metrics = block["metrics"]
        print("  %-5s days %4d net %+7.2f%% sharpe %+6.3f dd %+6.1f%%" % (
            regime, block["days"], metrics["annual_return"] * 100, metrics["sharpe"],
            metrics["max_drawdown"] * 100))
    if "constant_long" in conditioning:
        metrics = conditioning["constant_long"]["metrics"]
        print("  constant long over the sleeve window: net %+.2f%% sharpe %+.3f dd %+.1f%%" % (
            metrics["annual_return"] * 100, metrics["sharpe"], metrics["max_drawdown"] * 100))
    print("incremental at disclosure events (best two series):")
    for key, block in sorted(incremental.items(), key=lambda item: item[1]["log_loss_with_rates"])[:2]:
        print("  %-22s baseline %.4f -> with rates %.4f | improved %d of %d folds" % (
            key, block["log_loss_baseline"], block["log_loss_with_rates"], block["improved_folds"],
            block["folds"]))
    print("written", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
