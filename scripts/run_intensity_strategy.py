#!/usr/bin/env python3
"""Run the capex intensity strategy and report it honestly.

Protocol: docs/theses/t-intensity-charge.md, chain log docs/chains/t-intensity-charge.jsonl.
Development only, both sealed windows spent: the split is early against late, not a sealed test.

Signal: year over year change in capex intensity (capex over revenue), known at the later filing date,
valid for a declared window. Portfolio: dollar neutral long the low intensity names, short the high
intensity names, ranks within the complex after group demeaning. Cohorts open on a fixed cadence and hold
for the horizon, so overlapping cohorts accumulate.

Accounting: the signal waits for all four facts to be filed, entry is the first session strictly after
that date, costs and capacity use the prior month's dollar volume, and overlapping cohorts share one
unit of gross capital.

    python3 scripts/run_intensity_strategy.py                     # base specification
    python3 scripts/run_intensity_strategy.py --grid              # the declared variant grid
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAPEX = ROOT / "results" / "complex-capex-quarterly.csv"
REVENUE = ROOT / "results" / "complex-revenue-quarterly.csv"
ADV = ROOT / "results" / "universe-adv-monthly.csv"
PANEL = ROOT / "results" / "market-panel.json"
CACHE = ROOT / "results" / "bar-cache"
OUT = ROOT / "results" / "intensity-strategy.json"
PREFERRED = "RevenueFromContractWithCustomerExcludingAssessedTax"
SIGNAL_VALID_DAYS = 180
CADENCE = 5
COST_BUCKETS = [(50_000_000, 5.0), (10_000_000, 10.0), (2_000_000, 20.0), (0, 40.0)]
BASE = {"horizon": 20, "quantile": "third", "weight": "equal", "neutral": "group", "cost_mult": 1.0}
GRID = {"horizon": [5, 20, 60], "quantile": ["third", "half"], "weight": ["equal", "rank"],
        "neutral": ["group", "complex", "none"], "cost_mult": [1.0, 2.0]}


def day_gap(a: str, b: str) -> int:
    """Calendar day distance between two ISO dates; a parse failure reads as far apart."""
    try:
        return abs((datetime.date.fromisoformat(a) - datetime.date.fromisoformat(b)).days)
    except ValueError:
        return 99999


def first_session_after(dates: list[str], filed: str) -> str | None:
    """The first trading date strictly after a filing date."""
    return next((date for date in dates if date > filed), None)


def lagged_adv(adv_by_month: dict[str, float], date: str) -> float | None:
    """The prior month's dollar volume, the last one fully known at the decision date."""
    year, month = int(date[:4]), int(date[5:7])
    month -= 1
    if month == 0:
        year, month = year - 1, 12
    return adv_by_month.get(f"{year:04d}-{month:02d}")


def daily_cohort_pnl(open_cohorts: list[dict], rebalance: int, dates: list[str],
                     prices: dict[str, dict[str, float]], adv: dict[str, dict[str, float]],
                     cost_mult: float) -> tuple[float, float]:
    """One unit of gross capital per day, split equally across open cohorts.

    A cohort can never carry the whole book, because overlapping cohorts share the unit. Entry cost
    is charged on the cohort's first day, exit cost on its last, both at the same divisor. Expired
    cohorts are removed from the list.
    """
    scale = 1.0 / max(1, len(open_cohorts))
    gross = 0.0
    cost = 0.0
    previous, date = dates[rebalance - 1], dates[rebalance]
    for cohort in list(open_cohorts):
        elapsed = rebalance - cohort["start"]
        if elapsed == 0:
            cost += cohort["entry_cost"] * scale
            continue
        if 0 < elapsed <= cohort["horizon"]:
            for ticker, weight in cohort["weights"].items():
                series = prices.get(ticker)
                if not series or previous not in series or date not in series:
                    continue
                gross += weight * (series[date] / series[previous] - 1) * scale
        if elapsed == cohort["horizon"]:
            exit_costs = sum(abs(weight) * cost_bps(lagged_adv(adv.get(ticker, {}), date), cost_mult)
                             / 1e4 for ticker, weight in cohort["weights"].items())
            cost += exit_costs * scale
            open_cohorts.remove(cohort)
    return gross, cost


def load_signals(capex_path: Path = CAPEX, revenue_path: Path = REVENUE) -> list[dict]:
    capex: dict[str, dict[str, dict]] = collections.defaultdict(dict)
    for row in csv.DictReader(capex_path.open()):
        capex[row["ticker"]][row["period_end"]] = row
    revenue: dict[tuple[str, str], dict] = {}
    for row in csv.DictReader(revenue_path.open()):
        key = (row["ticker"], row["period_end"])
        current = revenue.get(key)
        if current is None or (row["concept"] == PREFERRED and current["concept"] != PREFERRED):
            revenue[key] = row
    revenue_by_ticker: dict[str, dict[str, dict]] = collections.defaultdict(dict)
    for (ticker, period_end), row in revenue.items():
        revenue_by_ticker[ticker][period_end] = row
    signals = []
    for ticker, quarters in sorted(capex.items()):
        for period_end, cap_row in sorted(quarters.items()):
            rev_row = next((candidate for rev_end, candidate in revenue_by_ticker[ticker].items()
                            if day_gap(rev_end, period_end) <= 20), None)
            if not rev_row or float(rev_row["value_usd"]) <= 0 or float(cap_row["value_usd"]) <= 0:
                continue
            year_ago = f"{int(period_end[:4]) - 1}{period_end[4:]}"
            year_cap = next((candidate for cand_end, candidate in quarters.items()
                             if day_gap(cand_end, year_ago) <= 10), None)
            year_rev = next((candidate for cand_end, candidate in revenue_by_ticker[ticker].items()
                             if day_gap(cand_end, year_ago) <= 10), None)
            if not year_cap or not year_rev:
                continue
            if float(year_cap["value_usd"]) <= 0 or float(year_rev["value_usd"]) <= 0:
                continue
            intensity = float(cap_row["value_usd"]) / float(rev_row["value_usd"])
            prior = float(year_cap["value_usd"]) / float(year_rev["value_usd"])
            filed = max(cap_row.get("filed", ""), rev_row.get("filed", ""),
                        year_cap.get("filed", ""), year_rev.get("filed", ""))
            if intensity <= 0 or prior <= 0 or not filed:
                continue
            signals.append({"ticker": ticker, "filed": filed, "period_end": period_end,
                            "intensity_change": math.log(intensity / prior)})
    signals.sort(key=lambda row: row["filed"])
    return signals


def load_prices() -> tuple[list[str], dict[str, dict[str, float]]]:
    prices = {}
    dates = set()
    for path in sorted(CACHE.glob("*.json")):
        series = json.loads(path.read_text())
        if not isinstance(series, dict):
            continue
        prices[path.stem] = series
        dates.update(series)
    return sorted(dates), prices


def load_adv() -> dict[str, dict[str, float]]:
    adv: dict[str, dict[str, float]] = collections.defaultdict(dict)
    for row in csv.DictReader(ADV.open()):
        adv[row["ticker"]][row["month"]] = float(row["adv_usd"])
    return adv


def cost_bps(adv_value: float | None, multiplier: float) -> float:
    if not adv_value:
        return 40.0 * multiplier
    for threshold, bps in COST_BUCKETS:
        if adv_value >= threshold:
            return bps * multiplier
    return 40.0 * multiplier


def run(config: dict, signals: list[dict], dates: list[str], prices: dict[str, dict[str, float]],
        adv: dict[str, dict[str, float]], group_of: dict[str, str], min_adv: float = 0.0) -> dict:
    date_index = {date: index for index, date in enumerate(dates)}
    daily = []
    cohort_log = []
    by_filed = collections.defaultdict(list)
    for signal in signals:
        by_filed[signal["filed"]].append(signal)
    filed_dates = sorted(by_filed)

    def active_signals(date: str) -> list[dict]:
        usable = []
        for signal in signals:
            if signal["filed"] >= date:
                break
            if day_gap(date, signal["filed"]) > SIGNAL_VALID_DAYS:
                continue
            if signal["ticker"] not in prices or date not in prices[signal["ticker"]]:
                continue
            if min_adv:
                adv_value = lagged_adv(adv.get(signal["ticker"], {}), date)
                if not adv_value or adv_value < min_adv:
                    continue
            usable.append(signal)
        latest = {}
        for signal in usable:
            latest[signal["ticker"]] = signal
        return list(latest.values())

    # The signal clock is the filing clock: a cohort opens when a new signal has been filed, not on a
    # fixed weekly cadence. Rebalancing weekly on a quarterly signal pays cost for a portfolio that has
    # not changed.
    schedule_dates = set()
    for signal in signals:
        if signal["filed"] < "2017-01-01":
            continue
        session = first_session_after(dates, signal["filed"])
        if session:
            schedule_dates.add(session)
    open_cohorts: list[dict] = []
    active_from = None
    active_to = None
    for rebalance, date in enumerate(dates):
        if rebalance == 0:
            continue
        live = active_signals(date) if date in schedule_dates else []
        if live and active_from is None:
            active_from = date
        if live and len(live) >= 6:
            values = {row["ticker"]: row["intensity_change"] for row in live}
            quantile = 1 / 3 if config["quantile"] == "third" else 0.5
            weights: dict[str, float] = {}
            if config["neutral"] == "group":
                # Group neutral: each group selects its own terciles and carries equal gross, so a
                # large group cannot outvote a small one.
                buckets: dict[str, dict[str, float]] = collections.defaultdict(dict)
                for ticker, value in values.items():
                    buckets[group_of.get(ticker, "unlisted")][ticker] = value
                leg_gross = 0.5 / max(1, len(buckets))
                for key in sorted(buckets):
                    ranked = sorted(buckets[key].items(), key=lambda item: item[1])
                    count = max(1, int(len(ranked) * quantile))
                    for leg, sign in ((ranked[:count], 1.0), (ranked[-count:], -1.0)):
                        if config["weight"] == "equal":
                            shares = [leg_gross / len(leg)] * len(leg)
                        else:
                            total = sum(range(1, len(leg) + 1))
                            shares = [leg_gross * position / total for position in range(1, len(leg) + 1)]
                        for (ticker, _), share in zip(leg, shares):
                            weights[ticker] = weights.get(ticker, 0.0) + sign * share
            else:
                if config["neutral"] == "complex":
                    mean = statistics.mean(values.values())
                    values = {ticker: value - mean for ticker, value in values.items()}
                ranked = sorted(values.items(), key=lambda item: item[1])
                count = max(1, int(len(ranked) * quantile))
                for leg, sign in ((ranked[:count], 1.0), (ranked[-count:], -1.0)):
                    if config["weight"] == "equal":
                        weight = 0.5 / len(leg)
                        for ticker, _ in leg:
                            weights[ticker] = weights.get(ticker, 0.0) + sign * weight
                    else:
                        total = sum(range(1, len(leg) + 1))
                        for position, (ticker, _) in enumerate(leg, start=1):
                            weights[ticker] = weights.get(ticker, 0.0) + sign * 0.5 * position / total
            entry_costs = 0.0
            capacity_terms = []
            for ticker, weight in weights.items():
                adv_value = lagged_adv(adv.get(ticker, {}), date)
                entry_costs += abs(weight) * cost_bps(adv_value, config["cost_mult"]) / 1e4
                if adv_value and weight:
                    capacity_terms.append(adv_value / abs(weight))
            if config.get("target_vol") and len(daily) > 60:
                trailing = [row["net"] for row in daily[-60:]]
                realised = statistics.pstdev(trailing) * math.sqrt(252) if len(trailing) > 5 else 0.0
                if realised > 0:
                    scale = min(2.0, config["target_vol"] / realised)
                    weights = {ticker: weight * scale for ticker, weight in weights.items()}
            open_cohorts.append({"start": rebalance, "horizon": config["horizon"], "weights": weights,
                                 "entry_cost": entry_costs,
                                 "capacity_1pct": 0.01 * min(capacity_terms) if capacity_terms else None,
                                 "capacity_5pct": 0.05 * min(capacity_terms) if capacity_terms else None,
                                 "names": len(weights)})
            cohort_log.append({"date": date, "names": len(weights),
                               "longs": sum(1 for weight in weights.values() if weight > 0),
                               "shorts": sum(1 for weight in weights.values() if weight < 0),
                               "entry_cost_bps": round(entry_costs * 1e4, 2),
                               "capacity_1pct": open_cohorts[-1]["capacity_1pct"],
                               "capacity_5pct": open_cohorts[-1]["capacity_5pct"]})
        # daily P&L from cohorts open on this date, one unit of gross capital split equally
        if open_cohorts:
            active_to = date
        gross_return, cost_today = daily_cohort_pnl(open_cohorts, rebalance, dates, prices, adv,
                                                    config["cost_mult"])
        net_return = gross_return - cost_today
        daily.append({"date": date, "gross": gross_return, "net": net_return, "open": len(open_cohorts)})

    def metrics(rows: list[dict]) -> dict:
        if not rows:
            return {"days": 0}
        nets = [row["net"] for row in rows]
        grosses = [row["gross"] for row in rows]
        mean = statistics.mean(nets)
        sd = statistics.pstdev(nets) if len(nets) > 1 else 0.0
        cumulative = 1.0
        peak = 1.0
        drawdown = 0.0
        for value in nets:
            cumulative *= 1 + value
            peak = max(peak, cumulative)
            drawdown = min(drawdown, cumulative / peak - 1)
        positives = [value for value in nets if value > 0]
        negatives = [value for value in nets if value < 0]
        return {"days": len(nets), "total_return": round(cumulative - 1, 4),
                "annual_return": round(mean * 252, 4), "annual_vol": round(sd * math.sqrt(252), 4),
                "sharpe": round(mean / sd * math.sqrt(252), 3) if sd else None,
                "gross_annual_return": round(statistics.mean(grosses) * 252, 4),
                "hit_rate": round(len(positives) / len(nets), 3),
                "profit_factor": round(sum(positives) / abs(sum(negatives)), 3) if negatives else None,
                "max_drawdown": round(drawdown, 4)}

    active_rows = [row for row in daily
                   if active_from and active_to and active_from <= row["date"] <= active_to]
    early_rows = [row for row in active_rows if row["date"] <= "2024-12-31"]
    late_rows = [row for row in active_rows if row["date"] >= "2025-01-01"]
    capacities = [entry["capacity_1pct"] for entry in cohort_log if entry["capacity_1pct"]]
    turnover_proxy = statistics.mean([entry["entry_cost_bps"] for entry in cohort_log]) if cohort_log else None
    return {"config": config, "cohorts": len(cohort_log), "names_median": statistics.median(
        [entry["names"] for entry in cohort_log]) if cohort_log else None,
        "metrics": metrics(active_rows), "early": metrics(early_rows), "late": metrics(late_rows),
        "window": {"from": active_from, "to": active_to},
        "capacity_1pct_median": round(statistics.median(capacities), 0) if capacities else None,
        "capacity_5pct_median": round(statistics.median([entry["capacity_5pct"] for entry in cohort_log
                                                         if entry["capacity_5pct"]]), 0) if cohort_log else None,
        "capacity_1pct_p10": round(sorted(capacities)[max(0, len(capacities) // 10 - 1)], 0) if capacities else None,
        "entry_cost_bps_median": round(statistics.median([entry["entry_cost_bps"] for entry in cohort_log]), 2)
        if cohort_log else None,
        "sample_cohort": cohort_log[0] if cohort_log else None}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", action="store_true")
    parser.add_argument("--horizon", type=int, default=BASE["horizon"])
    parser.add_argument("--quantile", default=BASE["quantile"])
    parser.add_argument("--weight", default=BASE["weight"])
    parser.add_argument("--neutral", default=BASE["neutral"])
    parser.add_argument("--cost-mult", type=float, default=BASE["cost_mult"])
    parser.add_argument("--output", type=Path, default=OUT,
                        help="where the run report lands; never overwrite another variant's file")
    parser.add_argument("--min-adv", type=float, default=0.0, help="minimum monthly dollar volume")
    parser.add_argument("--target-vol", type=float, default=0.0, help="optional annualised volatility target")
    args = parser.parse_args()

    signals = load_signals()
    dates, prices = load_prices()
    adv = load_adv()
    groups = json.loads(PANEL.read_text())["groups"]
    group_of = {}
    for group, payload in groups.items():
        for series in payload["series"]:
            group_of.setdefault(series["ticker"], group)
    print(f"signals {len(signals)} across {len({row['ticker'] for row in signals})} names, "
          f"prices {len(prices)} names on {len(dates)} dates, adv {len(adv)} names")

    if args.grid:
        runs = []
        for horizon in GRID["horizon"]:
            for quantile in GRID["quantile"]:
                for weight in GRID["weight"]:
                    for neutral in GRID["neutral"]:
                        for cost_mult in GRID["cost_mult"]:
                            config = {"horizon": horizon, "quantile": quantile, "weight": weight,
                                      "neutral": neutral, "cost_mult": cost_mult}
                            result = run(config, signals, dates, prices, adv, group_of)
                            runs.append({"config": config, "annual_return": result["metrics"].get("annual_return"),
                                         "sharpe": result["metrics"].get("sharpe"),
                                         "early_sharpe": result["early"].get("sharpe"),
                                         "late_sharpe": result["late"].get("sharpe"),
                                         "max_drawdown": result["metrics"].get("max_drawdown"),
                                         "total_return": result["metrics"].get("total_return")})
        report = {"status": "development only; both sealed windows spent; protocol docs/theses/t-intensity-charge.md",
                  "base": BASE, "variants": runs, "variant_count": len(runs),
                  "positive_share": round(sum(1 for row in runs if (row["annual_return"] or 0) > 0) / len(runs), 3),
                  "out_path": str(args.output.relative_to(ROOT))}
        args.output.write_text(json.dumps(report, indent=1) + "\n")
        runs.sort(key=lambda row: -(row["sharpe"] or -99))
        print(f"grid {len(runs)} variants, share with positive annual return {report['positive_share']}")
        for row in runs[:6]:
            print("  best:", json.dumps(row["config"]), "sharpe", row["sharpe"], "ann", row["annual_return"],
                  "early", row["early_sharpe"], "late", row["late_sharpe"])
        worst = runs[-3:]
        for row in worst:
            print("  worst:", json.dumps(row["config"]), "sharpe", row["sharpe"], "ann", row["annual_return"])
        return 0

    config = {"horizon": args.horizon, "quantile": args.quantile, "weight": args.weight,
              "neutral": args.neutral, "cost_mult": args.cost_mult,
              "target_vol": args.target_vol or None}
    result = run(config, signals, dates, prices, adv, group_of, min_adv=args.min_adv)
    report = {"status": "development only; both sealed windows spent; protocol docs/theses/t-intensity-charge.md",
              "min_adv": args.min_adv, "base": result}
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    print("config:", json.dumps(config))
    print("cohorts", result["cohorts"], "median names", result["names_median"],
          "median entry cost bps", result["entry_cost_bps_median"])
    print("all:", json.dumps(result["metrics"]))
    print("early:", json.dumps(result["early"]))
    print("late:", json.dumps(result["late"]))
    print("capacity at 1 percent median $", result["capacity_1pct_median"], "p10 $", result["capacity_1pct_p10"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
