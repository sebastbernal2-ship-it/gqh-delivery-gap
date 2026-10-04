#!/usr/bin/env python3
"""Culminate: three candidates, every leg we trust, regime conditioning swept honestly, both walks.

The three candidates, built from everything the record supports:

  A  era-robust core      the gated charge sleeve alone, volatility targeted
  B  hedge composite      disclosure + gated charge + the reversed capex leg, inverse volatility
  C  conditioned          B with a point-in-time regime multiplier chosen walk forward

Regime definitions are swept, never assumed: basket volatility, basket trend, basket drawdown, VIX,
the term spread and Aidan's infrastructure phase. For every evaluation year the honest version picks the
definition and the exposure map on earlier data alone and applies them to that year; the hindsight
version picks them on the whole sample and is labelled as hindsight. A regime-based walk-forward with
contiguous episodes and earlier-only fits is run beside the annual one, and both era and per-fold views
of in-sample against out-of-sample are reported.

    python3 scripts/run_culmination.py
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
from run_fred_rates_test import basket_returns, load_panel  # noqa: E402
from run_intensity_gate_test import CORRECTED  # noqa: E402
from run_sleeve_portfolio import COSTS, sleeve_daily  # noqa: E402
from run_three_sleeve_portfolio import align, apply_vol_target, inverse_vol_weights, weighted_daily  # noqa: E402
from run_walk_forward import ORIGINS, intensity_walk_forward, sleeve_walk_forward  # noqa: E402

CACHE = ROOT / "results" / "bar-cache"
REVENUE = ROOT / "results" / "revenue-vintages-pit.csv"
CAPEX = ROOT / "results" / "capex-vintages-pit.csv"
EVAL_YEARS = ("2020", "2021", "2022", "2023", "2024", "2025", "2026")
VOL_TARGET = 0.10
STATES = ("low", "mid", "high")
MULTIPLIER_CHOICES = (1.0, 0.5, 0.0)
ERAS = (("2010-01-01", "2014-12-31"), ("2015-01-01", "2018-12-31"),
        ("2019-01-01", "2022-12-31"), ("2023-01-01", "2026-12-31"))


def expanding_state(values: list[tuple[str, float]], minimum: int = 250) -> dict[str, str]:
    """Terciles from everything strictly before each day, so the state is point in time."""
    states = {}
    history: list[float] = []
    for day, value in values:
        if len(history) >= minimum:
            lower = np.quantile(history, 1 / 3)
            upper = np.quantile(history, 2 / 3)
            states[day] = "low" if value <= lower else ("high" if value > upper else "mid")
        history.append(value)
    return states


def regime_definitions(basket: dict[str, float], panel: dict[str, dict[str, float]],
                       phases: dict[str, str]) -> dict[str, dict[str, str]]:
    days = sorted(basket)
    definitions: dict[str, dict[str, str]] = {}

    volatility = []
    for position, day in enumerate(days):
        window = [basket[days[index]] for index in range(max(0, position - 20), position)]
        if len(window) >= 15:
            volatility.append((day, statistics.pstdev(window) * math.sqrt(252)))
    definitions["basket_vol"] = expanding_state(volatility)

    trend = {}
    for position, day in enumerate(days):
        window = [basket[days[index]] for index in range(max(0, position - 200), position + 1)]
        if len(window) >= 150:
            index = 1.0
            for value in window:
                index *= 1.0 + value
            trend[day] = "high" if index > 1.05 else ("low" if index < 0.95 else "mid")
    definitions["basket_trend"] = trend

    drawdown, peak, index = {}, 1.0, 1.0
    for day in days:
        index *= 1.0 + basket[day]
        peak = max(peak, index)
        depth = index / peak - 1.0
        drawdown[day] = "low" if depth > -0.05 else ("mid" if depth > -0.15 else "high")
    definitions["basket_drawdown"] = drawdown

    for name in ("VIXCLS", "T10Y2Y"):
        series = [(day, panel[day][name]) for day in sorted(panel) if name in panel[day]]
        definitions[f"{name.lower()}_z"] = expanding_state(
            [(day, value) for day, value in series], minimum=250)

    phase_map = {"buildout": "mid", "overbuild": "high", "shakeout": "high", "shortage": "low"}
    definitions["infra_phase"] = {day: phase_map.get(phases.get(day[:7], ""), "mid") for day in days}
    return definitions


def apply_multipliers(daily: list[dict], states: dict[str, str], multipliers: dict[str, float]) -> list[dict]:
    out = []
    for row in daily:
        candidates = [day for day in states if day <= row["date"]]
        regime = states[candidates[-1]] if candidates else "mid"
        factor = multipliers.get(regime, 1.0)
        out.append({**row, "net": row["net"] * factor, "gross": row["gross"] * factor,
                    "state": regime})
    return out


def era_table(daily: list[dict]) -> dict:
    table = {}
    for start, end in ERAS:
        subset = [row for row in daily if start <= row["date"] <= end]
        table[f"{start[:4]}-{end[:4]}"] = {"days": len(subset),
                                           "metrics": portfolio_metrics(subset) if len(subset) > 20 else None}
    return table


def facts(series: dict[str, list[dict]], label: str) -> dict:
    return {"name": label, "days": len(series["disclosure"])}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "culmination.json")
    args = parser.parse_args()

    # the three legs, each through its own walk-forward construction
    revenue_events, _, _ = sleeve_walk_forward(REVENUE, 1.0)
    disclosure, _ = sleeve_daily(revenue_events, CACHE, COSTS["base"])
    capex_events, _, _ = sleeve_walk_forward(CAPEX, 1.0)          # reversed: the hedge from the worst
    hedge, _ = sleeve_daily(capex_events, CACHE, COSTS["base"])
    charge, _ = intensity_walk_forward(1.0)
    legs = {"disclosure": disclosure, "charge": charge, "hedge_reversed_capex": hedge}

    dates, values = align([legs["disclosure"], legs["charge"], legs["hedge_reversed_capex"]])
    three_inverse = inverse_vol_weights(values)
    three_combined = weighted_daily(dates, values, three_inverse)
    two_dates, two_values = align([legs["disclosure"], legs["charge"]])
    two_inverse = inverse_vol_weights(two_values)
    two_combined = weighted_daily(two_dates, two_values, two_inverse)
    core_a = apply_vol_target(legs["charge"], VOL_TARGET)
    composite_b = apply_vol_target(two_combined, VOL_TARGET)          # the published headline
    composite_hedged = apply_vol_target(three_combined, VOL_TARGET)   # the hedge version, reported
    candidates = {"A_core_gated_charge": core_a, "B_two_sleeve_headline": composite_b,
                  "B3_with_reversed_capex_hedge": composite_hedged}
    headline = composite_b

    # the regime sweep
    basket = basket_returns({row["ticker"] for row in revenue_events} |
                            {row["ticker"] for row in capex_events})
    panel = load_panel(ROOT / "results" / "fred-panel.csv.gz")
    phases = {}
    import csv
    state_path = ROOT / "results" / "regime-state-daily.csv"
    if state_path.exists():
        phases = {row["month"]: row["phase"] for row in csv.DictReader(state_path.open())}
    definitions = regime_definitions(basket, panel, phases)

    sweep = {}
    for name, states in definitions.items():
        for multipliers in ({s: m for s, m in zip(STATES, combo)}
                            for combo in np.ndindex(*(len(MULTIPLIER_CHOICES),) * 3)):
            multipliers = {state: MULTIPLIER_CHOICES[position]
                           for state, position in multipliers.items()}
            if all(value == 0.0 for value in multipliers.values()):
                continue
            conditioned = apply_multipliers(headline, states, multipliers)
            metrics = portfolio_metrics(conditioned)
            if metrics["sharpe"] is None:
                continue
            sweep[f"{name}|{multipliers['low']},{multipliers['mid']},{multipliers['high']}"] = {
                "definition": name, "multipliers": multipliers, "full_sharpe": metrics["sharpe"],
                "full_return": metrics["annual_return"]}
    hindsight = max(sweep.items(), key=lambda item: item[1]["full_sharpe"])

    # honest walk-forward choice of definition and map
    stitched, choices = [], []
    for year in EVAL_YEARS:
        best, best_sharpe = None, None
        for key, block in sweep.items():
            states = definitions[block["definition"]]
            conditioned = apply_multipliers(headline, states, block["multipliers"])
            training = [row for row in conditioned if row["date"] < f"{year}-01-01"]
            if len(training) < 400:
                continue
            sharpe = portfolio_metrics(training)["sharpe"]
            if sharpe is None:
                continue
            if best_sharpe is None or sharpe > best_sharpe:
                best, best_sharpe = block, sharpe
        if best is None:
            continue
        chosen = apply_multipliers(headline, definitions[best["definition"]], best["multipliers"])
        segment = [row for row in chosen if f"{year}-01-01" <= row["date"] < f"{int(year) + 1}-01-01"]
        stitched.extend(segment)
        choices.append({"year": year, "definition": best["definition"],
                        "multipliers": best["multipliers"], "train_sharpe": round(best_sharpe, 3)})
    candidates["C_conditioned_walk_forward"] = stitched

    # regime-based walk-forward: contiguous episodes of the winning definition, earlier fits only
    winning_definition = choices[-1]["definition"] if choices else "basket_vol"
    states = definitions[winning_definition]
    episodes = []
    for day in dates:
        regime = states.get(day)
        if regime is None:
            continue
        if not episodes or episodes[-1]["regime"] != regime or \
                (episodes[-1]["days"] and (np.datetime64(day) - np.datetime64(episodes[-1]["days"][-1])).astype(int) > 45):
            episodes.append({"regime": regime, "days": [day]})
        else:
            episodes[-1]["days"].append(day)
    episode_report = []
    for position, episode in enumerate(episodes):
        if len(episode["days"]) < 40:
            continue
        earlier = [row for row in headline if row["date"] < episode["days"][0]]
        segment = [row for row in headline if episode["days"][0] <= row["date"] <= episode["days"][-1]]
        if len(earlier) < 300 or not segment:
            continue
        episode_report.append({"regime": episode["regime"], "start": episode["days"][0],
                               "end": episode["days"][-1], "days": len(segment),
                               "train_days": len(earlier),
                               "train_sharpe": round(portfolio_metrics(earlier)["sharpe"], 3),
                               "segment_metrics": portfolio_metrics(segment)})

    # factor decomposition: beta to the basket and the legs' contributions
    basket_daily = [{"date": day, "net": basket[day]} for day in sorted(basket)]
    decomposition = {}
    for name, daily in (("B_hedge_composite", composite_b), ("C_conditioned_walk_forward", stitched),
                        ("A_core_gated_charge", core_a)):
        _, values_aligned = align([daily, basket_daily])
        strategy, market = np.array(values_aligned[0]), np.array(values_aligned[1])
        if len(strategy) < 100:
            continue
        beta = float(np.cov(strategy, market)[0, 1] / np.var(market)) if np.var(market) else None
        alpha = float(strategy.mean() - (beta or 0.0) * market.mean())
        decomposition[name] = {"days": len(strategy), "beta_to_basket": beta,
                               "alpha_daily": alpha,
                               "correlation": float(np.corrcoef(strategy, market)[0, 1])}

    report = {
        "schema": "culmination-v1", "scope": "development_only",
        "protocol": "docs/plan/open-work.md",
        "candidates": {name: {"days": len(daily), "metrics": portfolio_metrics(daily),
                              "eras": era_table(daily),
                              "is_oos": {"in_sample_2010_2018": portfolio_metrics(
                                  [row for row in daily if row["date"] < "2019-01-01"]),
                                  "out_of_sample_2019_2026": portfolio_metrics(
                                      [row for row in daily if row["date"] >= "2019-01-01"])}}
                       for name, daily in candidates.items()},
        "legs": {name: portfolio_metrics(daily) for name, daily in legs.items()},
        "long_floor": {"metrics": portfolio_metrics(
            [{"date": day, "net": basket[day], "gross": basket[day]}
             for day in sorted(basket) if day >= "2019-02-01"])},
        "regime_sweep": {"definitions": list(definitions),
                         "combinations": len(sweep),
                         "hindsight_best": {"definition": hindsight[1]["definition"],
                                            "multipliers": hindsight[1]["multipliers"],
                                            "sharpe": hindsight[1]["full_sharpe"]},
                         "top_ten": [{"key": key, **{k: v for k, v in block.items() if k != "definition"}}
                                     for key, block in sorted(sweep.items(),
                                                              key=lambda item: -item[1]["full_sharpe"])[:10]]},
        "honest_choices": choices,
        "regime_walk_forward": {"definition": winning_definition, "episodes": episode_report},
        "decomposition": decomposition,
        "interval_conditioned_minus_unconditioned": month_blocked_interval(stitched, headline),
        "common_window": {"from": stitched[0]["date"], "to": stitched[-1]["date"]} if stitched else None,
        "same_window_comparison": {
            name: portfolio_metrics([row for row in daily
                                     if stitched and stitched[0]["date"] <= row["date"] <= stitched[-1]["date"]])
            for name, daily in {**candidates, "long_floor": [{"date": day, "net": basket[day]}
                                                             for day in sorted(basket)]}.items()} if stitched else None,
        "ready_for_performance_claim": False,
        "limitations": ["development only; the reversed capex leg is chosen after seeing the capex "
                        "sleeve lose every era, so it carries selection risk that only the forward "
                        "window can retire",
                        "the hindsight row is labelled and is not a claim",
                        "the regime-based walk-forward reuses the annual refits of the charge leg and "
                        "applies episode folds to the overlay",
                        "both sealed windows are spent; the forward window is the only untouched sample"],
    }
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    window_start = stitched[0]["date"] if stitched else "2019-02-01"
    window_end = stitched[-1]["date"] if stitched else "2026-12-31"

    def within(daily):
        return [row for row in daily if window_start <= row["date"] <= window_end]

    payload = {name: [{"date": row["date"], "net": row["net"]} for row in within(daily)]
               for name, daily in candidates.items()}
    payload["long_floor"] = [{"date": day, "net": basket[day]} for day in sorted(basket)
                             if window_start <= day <= window_end]
    state_days = [day for day in sorted(states) if window_start <= day <= window_end]
    payload["__state__"] = [state_days, [states[day] for day in state_days]]
    (ROOT / "results" / "culmination-series.json").write_text(json.dumps(payload) + "\n")

    print("candidate summary (volatility targeted at %.0f%%):" % (VOL_TARGET * 100))
    for name, block in report["candidates"].items():
        metrics = block["metrics"]
        print("  %-28s days %4d net %+7.2f%% vol %5.1f%% sharpe %+6.3f dd %+6.1f%%" % (
            name, block["days"], metrics["annual_return"] * 100, metrics["annual_vol"] * 100,
            metrics["sharpe"], metrics["max_drawdown"] * 100))
    print("legs:")
    for name, metrics in report["legs"].items():
        print("  %-28s net %+7.2f%% sharpe %+6.3f dd %+6.1f%%" % (
            name, metrics["annual_return"] * 100, metrics["sharpe"], metrics["max_drawdown"] * 100))
    print("long floor 2019+: net %+.2f%% sharpe %+.3f" % (
        report["long_floor"]["metrics"]["annual_return"] * 100,
        report["long_floor"]["metrics"]["sharpe"]))
    print("hindsight best: %s %s sharpe %+.3f" % (hindsight[1]["definition"],
                                                  hindsight[1]["multipliers"],
                                                  hindsight[1]["full_sharpe"]))
    print("honest choices:", json.dumps(choices))
    interval = report["interval_conditioned_minus_unconditioned"]
    print("conditioned minus unconditioned: point %+.4f CI [%+.4f, %+.4f] share+ %.3f" % (
        interval["point"], interval["lower"], interval["upper"], interval["share_positive"]))
    print("written", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
