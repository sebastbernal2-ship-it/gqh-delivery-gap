#!/usr/bin/env python3
"""Does regional grid load growth say anything about the names exposed to that region?

The dataset is the open EIA-930 hourly panel aggregated to daily regional load by
`scripts/build_eia930_load_panel.py`. The exposure map below is declared, not fitted: each ticker is
tied to the balancing authority its own facilities or fleet sit in, and nothing else is used.

Two declared tests:
  information   the rank correlation between a region's 30-day load growth and the forward 20-session
                return of its mapped names, sampled weekly
  pricing       each month the mapped names are ranked by their region's load growth, the top half is
                bought and the bottom half sold for twenty sessions, equal weight, flat costs

    python3 scripts/run_eia_load_specialist.py
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import statistics
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.market_state import load_series  # noqa: E402
from filing_specialist.portfolio_stats import month_blocked_interval, portfolio_metrics  # noqa: E402

CACHE = ROOT / "results" / "bar-cache"
HORIZON = 20
COST_BPS = 20.0
GROWTH_WINDOW = 30

# declared exposure: each ticker to the authority its own load, fleet or facilities sit in
EXPOSURE = {
    "CEG": "PJM", "AEP": "PJM", "D": "PJM", "EXC": "PJM", "FE": "PJM", "PPL": "PJM",
    "EQIX": "PJM", "DLR": "PJM", "AMZN": "PJM", "GOOGL": "PJM", "MSFT": "PJM", "META": "PJM",
    "VST": "ERCO", "NRG": "ERCO", "APLD": "ERCO", "CIFR": "ERCO",
    "SO": "SOCO", "NEE": "FPL", "DUK": "DUK", "ED": "NYIS", "ETR": "MISO", "DTE": "MISO",
    "WEC": "MISO", "AEE": "MISO",
}


def load_panel(path: Path) -> dict[str, dict[str, float]]:
    """Authority to ISO date to mean demand in MW."""
    panel: dict[str, dict[str, float]] = {}
    with gzip.open(path, "rt") as handle:
        for row in csv.DictReader(handle):
            value = row["demand_mean"]
            if not value:
                continue
            month, day, year = row["date"].split("/")
            panel.setdefault(row["authority"], {})[f"{year}-{month}-{day}"] = float(value)
    return panel


def growth(series: dict[str, float], day: str, window: int = GROWTH_WINDOW) -> float | None:
    """Mean demand over the window before the day against the window before that."""
    days = sorted(day_key for day_key in series if day_key < day)
    if len(days) < 2 * window:
        return None
    recent, prior = days[-window:], days[-2 * window:-window]
    recent_mean = statistics.mean(series[key] for key in recent)
    prior_mean = statistics.mean(series[key] for key in prior)
    return (recent_mean / prior_mean - 1.0) if prior_mean else None


def trading_days(prices: dict[str, float]) -> list[str]:
    return sorted(prices)


def forward_return(prices: dict[str, float], day: str, horizon: int = HORIZON) -> float | None:
    days = sorted(price_day for price_day in prices if price_day >= day)
    if len(days) < horizon + 1:
        return None
    entry, exit_day = days[0], days[horizon]
    return prices[exit_day] / prices[entry] - 1.0


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
    mean_x, mean_y = statistics.mean(x), statistics.mean(y)
    numerator = sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y))
    denominator = (sum((a - mean_x) ** 2 for a in x) ** 0.5) * (sum((b - mean_y) ** 2 for b in y) ** 0.5)
    return numerator / denominator if denominator else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, default=ROOT / "results" / "eia-load-daily.csv.gz")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "eia-load-specialist.json")
    args = parser.parse_args()

    panel = load_panel(args.panel)
    prices = {ticker: load_series(ticker, CACHE) for ticker in EXPOSURE}
    available = {ticker: series for ticker, series in prices.items() if series}
    print("mapped tickers with prices: %d of %d" % (len(available), len(EXPOSURE)))

    # information test: weekly samples of growth against forward return
    information = {}
    for ticker, series in sorted(available.items()):
        authority = EXPOSURE[ticker]
        authority_series = panel.get(authority, {})
        days = [day for day in trading_days(series) if day >= "2019-07-01"]
        samples = days[::5]
        pairs = []
        for day in samples:
            value = growth(authority_series, day)
            outcome = forward_return(series, day)
            if value is not None and outcome is not None:
                pairs.append((value, outcome))
        ic = spearman([pair[0] for pair in pairs], [pair[1] for pair in pairs])
        information[ticker] = {"authority": authority, "samples": len(pairs),
                               "information_coefficient": ic}
    ics = [block["information_coefficient"] for block in information.values()
           if block["information_coefficient"] is not None]
    information_summary = {"tickers": len(ics), "mean_ic": statistics.mean(ics) if ics else None,
                           "median_ic": statistics.median(ics) if ics else None,
                           "share_positive": (sum(1 for value in ics if value > 0) / len(ics))
                           if ics else None}

    # pricing test: monthly cross-sectional long-short by regional load growth
    calendar = sorted({day for series in available.values() for day in series})
    calendar = [day for day in calendar if day >= "2019-07-01"]
    rebalance_days = []
    last_month = None
    for day in calendar:
        month = day[:7]
        if month != last_month:
            rebalance_days.append(day)
            last_month = month
    events = []
    for day in rebalance_days:
        ranked = []
        for ticker, series in available.items():
            value = growth(panel.get(EXPOSURE[ticker], {}), day)
            if value is not None:
                ranked.append((value, ticker))
        if len(ranked) < 6:
            continue
        ranked.sort()
        half = max(1, len(ranked) // 2)
        shorts = [ticker for _, ticker in ranked[:half]]
        longs = [ticker for _, ticker in ranked[-half:]]
        events.append({"day": day, "longs": longs, "shorts": shorts})

    daily = []
    for event in events:
        series = {ticker: available[ticker] for ticker in event["longs"] + event["shorts"]}
        days = sorted({day for ticker_series in series.values() for day in ticker_series})
        after = [day for day in days if day > event["day"]]
        if len(after) < HORIZON + 2:
            continue
        window = after[:HORIZON + 1]
        costs = COST_BPS / 1e4
        for position in range(1, len(window)):
            day, previous = window[position], window[position - 1]
            returns = []
            for ticker in event["longs"]:
                ticker_series = series[ticker]
                if day in ticker_series and previous in ticker_series:
                    returns.append(ticker_series[day] / ticker_series[previous] - 1.0)
            long_return = statistics.mean(returns) if returns else 0.0
            returns = []
            for ticker in event["shorts"]:
                ticker_series = series[ticker]
                if day in ticker_series and previous in ticker_series:
                    returns.append(ticker_series[day] / ticker_series[previous] - 1.0)
            short_return = statistics.mean(returns) if returns else 0.0
            gross = long_return - short_return
            charge = costs if position == 1 else 0.0
            daily.append({"date": day, "gross": gross, "net": gross - charge,
                          "open": float(len(event["longs"]) + len(event["shorts"]))})

    zero = [{"date": row["date"], "net": 0.0, "gross": 0.0} for row in daily]
    report = {"schema": "eia-load-specialist-v1", "scope": "development_only",
              "protocol": "docs/plan/open-work.md",
              "panel": {"authorities": len(panel), "days": max(len(series) for series in panel.values())},
              "exposure": EXPOSURE, "information": information,
              "information_summary": information_summary,
              "pricing": {"rebalances": len(events), "days": len(daily),
                          "metrics": portfolio_metrics(daily) if daily else None,
                          "interval": month_blocked_interval(daily, zero) if daily else None},
              "ready_for_performance_claim": False,
              "limitations": ["development only", "the exposure map is declared, not fitted",
                              "load is demand, not price: no congestion or energy-price data here",
                              "the long and short legs are equal weighted and hold twenty sessions"]}
    args.output.write_text(json.dumps(report, indent=1) + "\n")

    print("information test: mean IC %.4f | median %.4f | positive in %.1f%% of %d names" % (
        information_summary["mean_ic"] or 0.0, information_summary["median_ic"] or 0.0,
        100 * (information_summary["share_positive"] or 0.0), information_summary["tickers"]))
    if daily:
        metrics = report["pricing"]["metrics"]
        interval = report["pricing"]["interval"]
        print("pricing test: rebalances %d days %d | net %+.2f%% vol %.1f%% sharpe %+.3f dd %+.1f%%" % (
            len(events), len(daily), metrics["annual_return"] * 100, metrics["annual_vol"] * 100,
            metrics["sharpe"], metrics["max_drawdown"] * 100))
        print("  long-short mean %.4f%% per day | CI [%.4f%%, %.4f%%] share+ %.3f" % (
            interval["point"] * 100, interval["lower"] * 100, interval["upper"] * 100,
            interval["share_positive"]))
    print("written", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
