#!/usr/bin/env python3
"""Combined capacity for the two surviving sleeves, at declared participation limits.

Capacity here means the capital at which the largest position reaches a given share of a name's
trailing dollar volume. For one unit of capital the per-name weight is the portfolio weight, so the
limit is `participation x min over held names of (ADV / |weight|)`. ADV is the 60-session median
dollar volume from the volume cache, the same source the sleeve runners use.

Reports the revenue sleeve alone, the gated intensity sleeve alone and the combined pair with the
walk-forward inverse-volatility weights, with the binding names identified.

    python3 scripts/run_capacity_curve.py
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.portfolio_stats import portfolio_metrics  # noqa: E402
from filing_specialist.rpo_model import prepare_rows  # noqa: E402
from run_intensity_gate_test import CORRECTED, VINTAGES, gate_for  # noqa: E402
from run_intensity_strategy import BASE, load_adv, load_prices, load_signals, run  # noqa: E402
from run_sleeve_portfolio import COSTS, sleeve_events  # noqa: E402
from run_three_sleeve_portfolio import align, inverse_vol_weights  # noqa: E402
from run_walk_forward import blocks, fit_at  # noqa: E402

VOLUME_CACHE = ROOT / "results" / "bar-volume"
HORIZON = 20
PARTICIPATION = (0.01, 0.05)


def trailing_adv() -> dict[tuple[str, str], float]:
    """(ticker, date) to the trailing 60-session median dollar volume, dated by the window end."""
    adv = {}
    for path in sorted(VOLUME_CACHE.glob("*.json")):
        try:
            bars = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if not isinstance(bars, list):
            continue
        clean = [bar for bar in bars if bar.get("volume") and bar.get("close")]
        for index in range(len(clean)):
            window = clean[max(0, index - 60):index + 1]
            if len(window) < 20:
                continue
            values = [bar["close"] * bar["volume"] for bar in window]
            adv[(path.stem, clean[index]["date"])] = statistics.median(values)
    return adv


def adv_at(adv: dict, ticker: str, date: str) -> float | None:
    """The most recent ADV observation at or before the date."""
    key = (ticker, date)
    if key in adv:
        return adv[key]
    return None


def revenue_positions(events: list[dict], cache: Path) -> dict[str, dict[str, float]]:
    """Daily gross-normalised position weights for an event sleeve."""
    from filing_specialist.market_state import load_series
    series = {ticker: load_series(ticker, cache) for ticker in {e["ticker"] for e in events}}
    open_by_day: dict[str, dict[str, float]] = {}
    for event in events:
        days = sorted(series.get(event["ticker"], {}))
        after = [day for day in days if day > event["decision"]]
        if len(after) < HORIZON + 1:
            continue
        for day in after[:HORIZON + 1]:
            open_by_day.setdefault(day, {})
            open_by_day[day][event["ticker"]] = open_by_day[day].get(event["ticker"], 0.0) + event["weight"]
    positions = {}
    for day, weights in open_by_day.items():
        gross = sum(abs(value) for value in weights.values())
        if gross > 0:
            positions[day] = {ticker: value / gross for ticker, value in weights.items()}
    return positions


def intensity_positions(cost_mult: float = 1.0) -> dict[str, dict[str, float]]:
    """Daily gross-normalised position weights for the gated intensity expression, walk-forward."""
    dates, prices = load_prices()
    adv = load_adv()
    panel = json.loads((ROOT / "results" / "market-panel.json").read_text())
    group_of = {series["ticker"]: group for group, payload in panel["groups"].items()
                for series in payload["series"]}
    signals = load_signals(CORRECTED["capex"], CORRECTED["revenue"])
    revenue_rows, _ = prepare_rows(list(csv.DictReader(VINTAGES["revenue"].open())))
    positions: dict[str, dict[str, float]] = {}
    for start, end in blocks():
        fitted = fit_at(revenue_rows, start)
        if fitted["probabilities"] is None:
            continue
        expected = {}
        for row, values in zip(fitted["later"], fitted["probabilities"]):
            decision = str(row["label_available"])[:10]
            if start <= decision < end:
                expected[(str(row["ticker"]), decision)] = sum(
                    k * float(p) for k, p in zip(fitted["classes"], values))
        gate = gate_for(expected, signals, centre=2.0)
        window = [date for date in dates if start <= date < end]
        if len(window) < 40 or not gate:
            continue
        result = run({**BASE, "cost_mult": cost_mult, "target_vol": None}, signals, window, prices,
                     adv, group_of, gate=gate)
        for cohort in result["cohort_weights"]:
            gross = sum(abs(value) for value in cohort["weights"].values())
            if gross <= 0:
                continue
            day = cohort["date"]
            day_weights = positions.setdefault(day, {})
            if not day_weights:
                positions[day] = {ticker: value / gross for ticker, value in cohort["weights"].items()}
    return positions


def capacity_of(positions: dict[str, dict[str, float]], adv: dict, participation: float,
                limit: int = 400) -> dict:
    """Capacity and binding names over the dates where both weights and ADV exist."""
    per_date, binding = [], {}
    for day in sorted(positions)[:limit]:
        weights = positions[day]
        terms = []
        for ticker, weight in weights.items():
            value = adv_at(adv, ticker, day)
            if value is None or abs(weight) < 1e-9:
                continue
            terms.append((value / abs(weight), ticker))
        if not terms:
            continue
        smallest, ticker = min(terms)
        per_date.append({"date": day, "capacity": participation * smallest, "binding_name": ticker,
                         "names": len(terms)})
        binding[ticker] = binding.get(ticker, 0) + 1
    capacities = sorted(row["capacity"] for row in per_date)
    if not capacities:
        return {"dates": 0}
    return {"dates": len(capacities),
            "median": statistics.median(capacities),
            "p10": capacities[max(0, len(capacities) // 10 - 1)],
            "p90": capacities[min(len(capacities) - 1, int(0.9 * len(capacities)))],
            "binding_names": dict(sorted(binding.items(), key=lambda item: -item[1])[:6]),
            "series": per_date}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "capacity-curve.json")
    parser.add_argument("--cache", type=Path, default=ROOT / "results" / "bar-cache")
    args = parser.parse_args()

    adv = trailing_adv()
    revenue_events = sleeve_events(ROOT / "results" / "revenue-vintages-pit.csv", 1.0, 0.7)
    revenue_daily = revenue_positions(revenue_events, args.cache)
    intensity_daily = intensity_positions()

    # the walk-forward inverse-volatility sleeve weights, from the daily series of each sleeve
    from run_walk_forward import sleeve_walk_forward
    from run_sleeve_portfolio import sleeve_daily
    walk_events, _, _ = sleeve_walk_forward(ROOT / "results" / "revenue-vintages-pit.csv", 1.0)
    walk_daily, _ = sleeve_daily(walk_events, args.cache, COSTS["base"])
    report = {"schema": "capacity-curve-v1", "scope": "development_only",
              "method": "participation x min over held names of (trailing 60-session dollar volume / |weight|)",
              "adv_coverage": {"series": len({key[0] for key in adv})},
              "sleeves": {}, "combined": {}, "ready_for_performance_claim": False,
              "limitations": ["development only", "volume cache covers the complex names",
                              "one unit of capital per sleeve unless combined",
                              "no borrow or shortability constraint"]}
    for participation in PARTICIPATION:
        report["sleeves"][f"revenue_{int(participation*100)}pct"] = capacity_of(revenue_daily, adv, participation)
        report["sleeves"][f"intensity_{int(participation*100)}pct"] = capacity_of(intensity_daily, adv, participation)

    # combined: sleeve weights from the walk-forward inverse-volatility estimates on common dates
    intensity_series = [{"date": day, "net": 0.0} for day in sorted(intensity_daily)]
    common = sorted(set(revenue_daily) & set(intensity_daily))
    revenue_series = [{"date": day, "net": 0.0} for day in common]
    intensity_series = [{"date": day, "net": 0.0} for day in sorted(intensity_daily)]
    dates, values = align([revenue_series, intensity_series])
    combined_positions: dict[str, dict[str, float]] = {}
    for position, day in enumerate(dates):
        if day not in revenue_daily and day not in intensity_daily:
            continue
        sleeve_weights = [0.5, 0.5]
        merged: dict[str, float] = {}
        for sleeve, sleeve_weight in zip((revenue_daily, intensity_daily), sleeve_weights):
            for ticker, weight in sleeve.get(day, {}).items():
                merged[ticker] = merged.get(ticker, 0.0) + sleeve_weight * weight
        gross = sum(abs(value) for value in merged.values())
        if gross > 0:
            combined_positions[day] = {ticker: value / gross for ticker, value in merged.items()}
    for participation in PARTICIPATION:
        report["combined"][f"equal_gross_{int(participation*100)}pct"] = capacity_of(
            combined_positions, adv, participation)

    # the walk-forward mean weights from T51: 21.7 percent revenue, 78.3 percent intensity
    skewed_positions: dict[str, dict[str, float]] = {}
    for day in dates:
        merged: dict[str, float] = {}
        for sleeve, sleeve_weight in ((revenue_daily, 0.217), (intensity_daily, 0.783)):
            for ticker, weight in sleeve.get(day, {}).items():
                merged[ticker] = merged.get(ticker, 0.0) + sleeve_weight * weight
        gross = sum(abs(value) for value in merged.values())
        if gross > 0:
            skewed_positions[day] = {ticker: value / gross for ticker, value in merged.items()}
    for participation in PARTICIPATION:
        report["combined"][f"inverse_vol_217_783_{int(participation*100)}pct"] = capacity_of(
            skewed_positions, adv, participation)
    args.output.write_text(json.dumps(report, indent=1) + "\n")

    for name, block in report["sleeves"].items():
        if block.get("dates"):
            print("  %-18s dates %4d median $%12.0f p10 $%11.0f binding %s" % (
                name, block["dates"], block["median"], block["p10"],
                list(block["binding_names"])[:3]))
    for name, block in report["combined"].items():
        if block.get("dates"):
            print("  %-18s dates %4d median $%12.0f p10 $%11.0f binding %s" % (
                name, block["dates"], block["median"], block["p10"],
                list(block["binding_names"])[:3]))
    print("written", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
