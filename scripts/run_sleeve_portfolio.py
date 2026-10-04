#!/usr/bin/env python3
"""Stage 3: one portfolio over the two measured sleeves inside the complex.

Each sleeve is an event portfolio on its own disclosure clock. The revenue sleeve is long high
expected surprise and short low, the capex sleeve is long low and short high, and the composite
holds both at equal gross. One unit of gross exposure per day, sized by conviction, with a declared
volatility target and declared round-trip costs. Out-of-sample rows only: the surprise models are
frozen from the first seventy percent of each panel.

    python3 scripts/run_sleeve_portfolio.py
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.market_state import load_series  # noqa: E402
from filing_specialist.model import fit_and_forecast  # noqa: E402
from filing_specialist.portfolio_stats import month_blocked_interval, portfolio_metrics  # noqa: E402
from filing_specialist.rpo_model import FEATURES, prepare_rows  # noqa: E402

VOLUME_CACHE = ROOT / "results" / "bar-volume"
HORIZON = 20
COSTS = {"base": 20.0, "doubled": 40.0}


def sleeve_events(panel: Path, direction: float, split: float) -> list[dict]:
    """Out-of-sample events with a conviction weight in [-1, 1] and both clocks."""
    rows, _ = prepare_rows(list(csv.DictReader(panel.open())))
    fitted = fit_and_forecast(rows, tuple(FEATURES), fraction=split)
    test_rows = [row for row in rows if row["label_available"] >= fitted["split"]["test_from"]]
    if len(test_rows) != len(fitted["test_labels"]):
        raise SystemExit(f"{panel.name}: the split and the forecast rows disagree")
    events = []
    for row, values in zip(test_rows, fitted["softmax_probabilities"]):
        expected = sum(k * float(p) for k, p in zip(fitted["classes"], values))
        conviction = direction * (expected - 2.0) / 2.0
        if abs(conviction) < 1e-9:
            continue
        events.append({"ticker": str(row["ticker"]), "decision": str(row["label_available"])[:10],
                       "weight": conviction, "period_end": str(row["period_end"])})
    return events


def sleeve_daily(events: list[dict], cache_dir: Path, cost_bps: float) -> tuple[list[dict], dict]:
    """Daily gross-normalised net return of one sleeve, with costs charged on entry."""
    series = {ticker: load_series(ticker, cache_dir) for ticker in {e["ticker"] for e in events}}
    prepared = []
    for event in events:
        days = sorted(series.get(event["ticker"], {}))
        after = [day for day in days if day > event["decision"]]
        if len(after) < HORIZON + 1:
            continue
        prepared.append({**event, "entry": after[0], "exit": after[HORIZON], "series": series[event["ticker"]]})
    if not prepared:
        return [], {"events_used": 0}
    calendar = sorted({day for event in prepared
                       for day in event["series"] if event["entry"] <= day <= event["exit"]})
    index = {day: position for position, day in enumerate(calendar)}
    daily = []
    for day in calendar:
        gross, weight_sum, cost = 0.0, 0.0, 0.0
        for event in prepared:
            series_day = event["series"]
            if not (event["entry"] <= day <= event["exit"]):
                continue
            position = index[day]
            if position == 0:
                continue
            previous_day = calendar[position - 1]
            if previous_day not in series_day or day not in series_day:
                continue
            change = series_day[day] / series_day[previous_day] - 1.0
            gross += event["weight"] * change
            weight_sum += abs(event["weight"])
            if day == event["entry"]:
                cost += abs(event["weight"]) * cost_bps / 1e4
        if weight_sum > 0:
            daily.append({"date": day, "gross": gross / weight_sum,
                          "net": (gross - cost) / weight_sum, "open": weight_sum})
    return daily, {"events_used": len(prepared), "sessions": len(calendar)}


def apply_vol_target(daily: list[dict], target: float, cap: float = 2.0) -> list[dict]:
    scaled, trailing = [], []
    for row in daily:
        scale = 1.0
        if len(trailing) >= 60 and target:
            realised = statistics.pstdev(trailing[-60:]) * (252 ** 0.5)
            if realised > 0:
                scale = min(cap, target / realised)
        scaled.append({**row, "net": row["net"] * scale, "scale": scale})
        trailing.append(row["net"])
    return scaled


def capacity_report(events: list[dict]) -> dict:
    adv_by_ticker = {}
    for event in events:
        path = VOLUME_CACHE / f"{event['ticker']}.json"
        if path.exists():
            try:
                bars = json.loads(path.read_text())
            except (OSError, ValueError):
                continue
            recent = [bar["close"] * bar["volume"] for bar in bars[-60:] if bar.get("volume")]
            if recent:
                adv_by_ticker[event["ticker"]] = statistics.median(recent)
    if not adv_by_ticker:
        return {"covered_tickers": 0}
    terms = [0.01 * adv_by_ticker[event["ticker"]] / max(1e-9, abs(event["weight"]))
             for event in events if event["ticker"] in adv_by_ticker]
    terms.sort()
    return {"covered_tickers": len(adv_by_ticker), "events_with_adv": len(terms),
            "capacity_1pct_median": statistics.median(terms) if terms else None,
            "capacity_1pct_p10": terms[max(0, len(terms) // 10 - 1)] if terms else None}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revenue", type=Path, default=ROOT / "results" / "revenue-vintages-pit.csv")
    parser.add_argument("--capex", type=Path, default=ROOT / "results" / "capex-vintages-pit.csv")
    parser.add_argument("--cache", type=Path, default=ROOT / "results" / "bar-cache")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "sleeve-portfolio.json")
    parser.add_argument("--target-vol", type=float, default=0.10)
    parser.add_argument("--split", type=float, default=0.7)
    args = parser.parse_args()

    revenue = sleeve_events(args.revenue, direction=1.0, split=args.split)
    capex = sleeve_events(args.capex, direction=-1.0, split=args.split)
    report = {"schema": "sleeve-portfolio-v1", "scope": "development_only",
              "protocol": "docs/plan/alpha-build.md", "horizon_sessions": HORIZON,
              "target_vol": args.target_vol, "sleeves": {}, "composite": {},
              "ready_for_performance_claim": False,
              "limitations": [
                  "development only; both sealed windows are spent",
                  "complex names only, 55 issuers, few hundred events",
                  "flat round-trip costs, capacity from 60-session median dollar volume",
                  "the models are frozen from the first seventy percent of each panel",
              ]}
    dailies = {}
    for name, events in (("revenue", revenue), ("capex", capex)):
        for cost_label, cost_bps in COSTS.items():
            daily, info = sleeve_daily(events, args.cache, cost_bps)
            report["sleeves"][f"{name}_{cost_label}"] = {"events": info, "cost_bps": cost_bps,
                                                         "metrics": portfolio_metrics(daily)}
            report["sleeves"][f"{name}_{cost_label}"]["capacity"] = capacity_report(events)
            dailies[f"{name}_{cost_label}"] = daily
    for cost_label in COSTS:
        equity = dailies[f"revenue_{cost_label}"]
        credit = dailies[f"capex_{cost_label}"]
        months = {row["date"] for row in equity} & {row["date"] for row in credit}
        combined = []
        for row in equity:
            if row["date"] in months:
                other = next(item for item in credit if item["date"] == row["date"])
                combined.append({"date": row["date"], "gross": 0.5 * row["gross"] + 0.5 * other["gross"],
                                 "net": 0.5 * row["net"] + 0.5 * other["net"]})
        scaled = apply_vol_target(combined, args.target_vol)
        report["composite"][cost_label] = {
            "metrics": portfolio_metrics(combined),
            "metrics_vol_target": portfolio_metrics(scaled),
            "days": len(combined),
        }
        dailies[f"composite_{cost_label}"] = combined
    report["intervals"] = {
        "composite_minus_revenue_base": month_blocked_interval(dailies["composite_base"],
                                                               dailies["revenue_base"]),
        "composite_minus_capex_base": month_blocked_interval(dailies["composite_base"],
                                                             dailies["capex_base"]),
        "composite_minus_best_sleeve": month_blocked_interval(
            dailies["composite_base"],
            max((dailies["revenue_base"], dailies["capex_base"]),
                key=lambda rows: portfolio_metrics(rows)["sharpe"] or -9)),
    }
    args.output.write_text(json.dumps(report, indent=1) + "\n")

    print("sleeve                       days   net      vol     sharpe   maxDD")
    for name in ("revenue_base", "revenue_doubled", "capex_base", "capex_doubled"):
        m = report["sleeves"][name]["metrics"]
        print("%-26s %5d %+7.2f%% %6.1f%% %+7.3f %+7.1f%%" % (
            name, m["days"], m["annual_return"] * 100, m["annual_vol"] * 100,
            m["sharpe"] or float("nan"), m["max_drawdown"] * 100))
    for name in ("base", "doubled"):
        m = report["composite"][name]["metrics"]
        v = report["composite"][name]["metrics_vol_target"]
        print("composite %-9s        %5d %+7.2f%% %6.1f%% %+7.3f %+7.1f%% | vol-targeted %+7.2f%% %6.1f%% %+7.3f %+7.1f%%" % (
            name, m["days"], m["annual_return"] * 100, m["annual_vol"] * 100, m["sharpe"] or float("nan"),
            m["max_drawdown"] * 100, v["annual_return"] * 100, v["annual_vol"] * 100,
            v["sharpe"] or float("nan"), v["max_drawdown"] * 100))
    for name, interval in report["intervals"].items():
        print("%-34s difference %+7.2f%% CI [%s, %s] share+ %s" % (
            name, (interval["point"] or 0.0) * 100,
            f"{interval['lower']*100:+.2f}%" if interval.get("lower") is not None else "n/a",
            f"{interval['upper']*100:+.2f}%" if interval.get("upper") is not None else "n/a",
            round(interval.get("share_positive", float("nan")), 3)))
    print("written", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
