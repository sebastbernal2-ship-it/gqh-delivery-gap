#!/usr/bin/env python3
"""Stage 1: does a signed expectation-gap gate improve the intensity strategy?

Window: the out-of-sample thirty percent of the driver vintages only, because the surprise model is
frozen from the first seventy. The engine trades the corrected (earliest-filed) clock. The gate is
the model's expected bin on the same disclosure, centred so that zero means "as expected":

- revenue gate: expected bin minus two, so a positive value confirms a long and a negative a short;
- combined gate: revenue minus capex expected bin, so a revenue beat with a capex miss is the
  strongest confirmation.

    python3 scripts/run_intensity_gate_test.py
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.model import fit_and_forecast  # noqa: E402
from filing_specialist.rpo_model import FEATURES, prepare_rows  # noqa: E402
from run_intensity_strategy import BASE, load_adv, load_prices, load_signals, run  # noqa: E402

CORRECTED = {"capex": ROOT / "results" / "complex-capex-quarterly-pit.csv",
             "revenue": ROOT / "results" / "complex-revenue-quarterly-pit.csv"}
VINTAGES = {"revenue": ROOT / "results" / "revenue-vintages-pit.csv",
            "capex": ROOT / "results" / "capex-vintages-pit.csv"}


def surprises(path: Path, split: float) -> tuple[dict, dict]:
    """Expected bin per (ticker, availability date) on out-of-sample rows only."""
    rows, _ = prepare_rows(list(csv.DictReader(path.open())))
    fitted = fit_and_forecast(rows, tuple(FEATURES), fraction=split)
    test_rows = [row for row in rows if row["label_available"] >= fitted["split"]["test_from"]]
    if len(test_rows) != len(fitted["test_labels"]):
        raise SystemExit(f"{path.name}: the split and the forecast rows disagree")
    expected = {}
    for row, values in zip(test_rows, fitted["softmax_probabilities"]):
        score = float(sum(k * float(p) for k, p in zip(fitted["classes"], values)))
        expected[(str(row["ticker"]), str(row["label_available"])[:10])] = score
    return expected, fitted["split"]


def gate_for(expected: dict, signals: list[dict], centre: float) -> dict:
    """The most recent known surprise per (ticker, filing), signed around `centre`."""
    by_ticker: dict[str, list[tuple[str, float]]] = {}
    for (ticker, date), score in expected.items():
        by_ticker.setdefault(ticker, []).append((date, score))
    for rows in by_ticker.values():
        rows.sort()
    gate = {}
    for signal in signals:
        rows = by_ticker.get(signal["ticker"])
        if not rows:
            continue
        known = [score for date, score in rows if date <= signal["filed"]]
        if known:
            gate[(signal["ticker"], signal["filed"])] = known[-1] - centre
    return gate


def month_blocked_interval(left: list[dict], right: list[dict], resamples: int = 1000,
                           seed: int = 20261004) -> dict:
    """Percentile interval for the annualised net difference, resampling whole calendar months."""
    import random
    import statistics

    def mean_by_month(rows: list[dict]) -> dict[str, float]:
        buckets: dict[str, list[float]] = {}
        for row in rows:
            buckets.setdefault(row["date"][:7], []).append(row["net"])
        return {month: statistics.mean(values) for month, values in buckets.items()}

    left_months, right_months = mean_by_month(left), mean_by_month(right)
    months = sorted(set(left_months) & set(right_months))
    if len(months) < 6:
        return {"point": None, "lower": None, "upper": None, "months": len(months)}
    point = (statistics.mean(left_months[m] for m in months)
             - statistics.mean(right_months[m] for m in months)) * 252
    rng = random.Random(seed)
    draws = []
    for _ in range(resamples):
        sample = [months[rng.randrange(len(months))] for _ in range(len(months))]
        draws.append((statistics.mean(left_months[m] for m in sample)
                      - statistics.mean(right_months[m] for m in sample)) * 252)
    draws.sort()
    return {"point": point, "lower": draws[int(0.025 * len(draws))],
            "upper": draws[int(0.975 * len(draws)) - 1], "months": len(months),
            "share_positive": sum(1 for value in draws if value > 0) / len(draws)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results" / "intensity-gate-test.json")
    parser.add_argument("--split", type=float, default=0.7)
    parser.add_argument("--target-vol", type=float, default=0.10)
    args = parser.parse_args()

    dates, prices = load_prices()
    adv = load_adv()
    panel = json.loads((ROOT / "results" / "market-panel.json").read_text())
    group_of = {series["ticker"]: group for group, payload in panel["groups"].items()
                for series in payload["series"]}
    signals = load_signals(CORRECTED["capex"], CORRECTED["revenue"])

    revenue, revenue_split = surprises(VINTAGES["revenue"], args.split)
    capex, capex_split = surprises(VINTAGES["capex"], args.split)
    starts = [block["test_from"] for block in (revenue_split, capex_split)]
    window_start = max(starts)[:10]
    window = [date for date in dates if date >= window_start]
    if len(window) < 60:
        raise SystemExit("the out-of-sample window is too short to run")

    covers = {
        "signals": len(signals),
        "signals_in_window": sum(1 for s in signals if s["filed"] >= window_start),
        "revenue_surprises": len(revenue),
        "capex_surprises": len(capex),
    }
    revenue_gate = gate_for(revenue, signals, centre=2.0)
    capex_gate = gate_for(capex, signals, centre=2.0)
    combined_gate = {key: value for key, value in revenue_gate.items()}
    for key, value in capex_gate.items():
        if key in combined_gate:
            combined_gate[key] = combined_gate[key] - value

    runs = {
        "baseline_base": ({}, 1.0),
        "baseline_doubled": ({}, 2.0),
        "baseline_vol_target": ({"target_vol": args.target_vol}, 1.0),
        "revenue_gate_base": ({"gate": revenue_gate}, 1.0),
        "revenue_gate_doubled": ({"gate": revenue_gate}, 2.0),
        "revenue_gate_vol_target": ({"gate": revenue_gate, "target_vol": args.target_vol}, 1.0),
        "combined_gate_base": ({"gate": combined_gate}, 1.0),
        "combined_gate_doubled": ({"gate": combined_gate}, 2.0),
        "combined_gate_vol_target": ({"gate": combined_gate, "target_vol": args.target_vol}, 1.0),
    }
    report = {
        "schema": "intensity-gate-test-v1", "scope": "development_only",
        "protocol": "docs/plan/alpha-build.md",
        "window": {"from": window_start, "to": window[-1], "sessions": len(window)},
        "coverage": covers,
        "runs": {},
        "ready_for_performance_claim": False,
        "limitations": [
            "out-of-sample window only, about three years, few cohorts",
            "the surprise model is frozen from the first seventy percent of the driver vintages",
            "missing surprise data never confirms, so gated exposure is below the baseline by design",
            "no borrow cost, no capacity expansion, one price source",
        ],
    }
    daily_series = {}
    for name, (extra, cost_mult) in runs.items():
        config = {**BASE, "cost_mult": cost_mult, "target_vol": extra.get("target_vol")}
        result = run(config, signals, window, prices, adv, group_of, gate=extra.get("gate"))
        daily_series[name] = result["daily"]
        metrics = result["metrics"]
        report["runs"][name] = {
            "cohorts": result["cohorts"], "names_median": result["names_median"],
            "annual_return": metrics["annual_return"], "annual_vol": metrics["annual_vol"],
            "sharpe": metrics["sharpe"], "max_drawdown": metrics["max_drawdown"],
            "hit_rate": metrics["hit_rate"], "total_return": metrics["total_return"],
            "entry_cost_bps_median": result["entry_cost_bps_median"],
            "capacity_1pct_median": result["capacity_1pct_median"],
        }
        print("%-26s cohorts %3d names %4.1f | net %+6.2f%% vol %5.1f%% sharpe %+5.3f dd %+6.1f%%" % (
            name, result["cohorts"], result["names_median"] or 0.0,
            metrics["annual_return"] * 100, metrics["annual_vol"] * 100,
            metrics["sharpe"] if metrics["sharpe"] is not None else float("nan"),
            metrics["max_drawdown"] * 100))
    report["intervals"] = {
        "revenue_gate_minus_baseline_base": month_blocked_interval(
            daily_series["revenue_gate_base"], daily_series["baseline_base"]),
        "revenue_gate_minus_baseline_doubled": month_blocked_interval(
            daily_series["revenue_gate_doubled"], daily_series["baseline_doubled"]),
        "combined_gate_minus_revenue_gate": month_blocked_interval(
            daily_series["combined_gate_base"], daily_series["revenue_gate_base"]),
    }
    for name, interval in report["intervals"].items():
        print("%-38s difference %+6.2f%% interval %s months %s share+ %s" % (
            name, (interval["point"] or 0.0) * 100,
            f"[{interval['lower']*100:+.2f}%, {interval['upper']*100:+.2f}%]"
            if interval.get("lower") is not None else "n/a",
            interval.get("months"), interval.get("share_positive")))
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    print("window", window_start, "to", window[-1], "|", len(window), "sessions | coverage", json.dumps(covers))
    print("written", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
