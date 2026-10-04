#!/usr/bin/env python3
"""Recalibrate the gate's model with temperature scaling, then re-run the engine A/B.

T54 showed the revenue model is overconfident exactly in the confident bins, which is where a
confirmation gate acts. This fits one scalar temperature on the earlier part of the walk-forward
out-of-sample predictions and leaves the later part untouched for evaluation, then rebuilds the gate
from the recalibrated distribution and compares three engine runs on the same window as T44: no gate,
the raw gate, and the recalibrated gate, each at base and doubled costs.

    python3 scripts/run_gate_recalibration.py
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.calibration_diagnostics import (expected_calibration_error,  # noqa: E402
                                                       reliability)
from filing_specialist.model import (apply_scaler, fit_scaler, fit_softmax,  # noqa: E402
                                     matrix_from_rows, softmax)
from filing_specialist.portfolio_stats import month_blocked_interval  # noqa: E402
from filing_specialist.rpo_model import FEATURES, prepare_rows  # noqa: E402
from run_intensity_gate_test import CORRECTED, VINTAGES, gate_for  # noqa: E402
from run_intensity_strategy import BASE, load_adv, load_prices, load_signals, run  # noqa: E402
from run_walk_forward import ORIGINS, blocks  # noqa: E402

WINDOW_START = "2023-07-28"          # the same out-of-sample window T44 used
GRID = tuple(round(0.25 + 0.05 * step, 2) for step in range(96))   # 0.25 .. 5.00


def walk_forward_logits(panel: Path) -> tuple[np.ndarray, np.ndarray, list[str], list[str]]:
    """Logits, labels, dates and tickers for out-of-sample rows across the annual origins."""
    rows, _ = prepare_rows(list(csv.DictReader(panel.open())))
    logits, labels, dates, tickers = [], [], [], []
    for start, end in blocks(ORIGINS):
        train = [row for row in rows if str(row["label_available"])[:10] < start]
        later = [row for row in rows if str(row["label_available"])[:10] >= start]
        if len(train) < 50 or not later:
            continue
        train_matrix, train_labels = matrix_from_rows(train, tuple(FEATURES))
        later_matrix, _ = matrix_from_rows(later, tuple(FEATURES))
        classes = tuple(sorted({int(row["label_bin"]) for row in train}))
        stats = fit_scaler(train_matrix)
        parameters = fit_softmax(apply_scaler(train_matrix, stats), train_labels, classes)
        design = np.column_stack([apply_scaler(later_matrix, stats), np.ones(len(later))])
        block_logits = design @ parameters
        for row, value in zip(later, block_logits):
            decision = str(row["label_available"])[:10]
            if not (start <= decision < end):
                continue
            logits.append(value)
            labels.append(classes.index(int(row["label_bin"])))
            dates.append(decision)
            tickers.append(str(row["ticker"]))
    return np.array(logits), np.array(labels), dates, tickers


def temperature_nll(logits: np.ndarray, labels: np.ndarray, temperature: float) -> float:
    probabilities = softmax(logits / temperature)
    picked = np.clip(probabilities[np.arange(len(labels)), labels], 1e-15, 1.0)
    return float(-np.log(picked).mean())


def fit_temperature(logits: np.ndarray, labels: np.ndarray, grid: tuple[float, ...] = GRID) -> dict:
    """The grid minimum of the negative log likelihood in one scalar temperature."""
    scores = [(temperature, temperature_nll(logits, labels, temperature)) for temperature in grid]
    best_temperature, best_nll = min(scores, key=lambda item: item[1])
    return {"temperature": best_temperature, "nll": best_nll,
            "nll_at_one": temperature_nll(logits, labels, 1.0)}


def diagnostics(logits: np.ndarray, labels: np.ndarray, temperature: float) -> dict:
    probabilities = softmax(logits / temperature)
    confidence = probabilities.max(axis=1)
    correct = [1 if row.argmax() == label else 0 for row, label in zip(probabilities, labels)]
    table = reliability(list(confidence), correct, bins=10)
    return {"rows": len(labels), "expected_calibration_error": expected_calibration_error(table),
            "sharpness": float(confidence.mean()), "reliability": table}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, default=VINTAGES["revenue"])
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results" / "gate-recalibration.json")
    args = parser.parse_args()

    logits, labels, dates, tickers = walk_forward_logits(args.panel)
    if len(labels) < 200:
        raise SystemExit("not enough out-of-sample rows to calibrate")
    # the earlier sixty percent of out-of-sample rows calibrate; the later forty percent evaluate
    order = np.argsort(dates)
    split = int(0.6 * len(order))
    calibration, evaluation = order[:split], order[split:]
    fit = fit_temperature(logits[calibration], labels[calibration])
    report = {
        "schema": "gate-recalibration-v1", "scope": "development_only",
        "protocol": "docs/plan/alpha-build.md", "window_start": WINDOW_START,
        "rows": {"calibration": len(calibration), "evaluation": len(evaluation)},
        "split_dates": {"calibration_through": dates[calibration[-1]],
                        "evaluation_from": dates[evaluation[0]]},
        "temperature": fit,
        "calibration_arm": {"raw": diagnostics(logits[calibration], labels[calibration], 1.0),
                            "recalibrated": diagnostics(logits[calibration], labels[calibration],
                                                        fit["temperature"])},
        "evaluation_arm": {"raw": diagnostics(logits[evaluation], labels[evaluation], 1.0),
                           "recalibrated": diagnostics(logits[evaluation], labels[evaluation],
                                                       fit["temperature"])},
        "ready_for_performance_claim": False,
        "limitations": [
            "development only; the temperature is fitted on earlier out-of-sample rows and evaluated "
            "on later ones, so both arms are out of sample with respect to the classifier",
            "one scalar temperature cannot fix class-specific overconfidence",
            "the engine window is the same one T44 used, so it is development evidence",
        ],
    }

    # the engine A/B on the declared window
    dates_full, prices = load_prices()
    adv = load_adv()
    panel = json.loads((ROOT / "results" / "market-panel.json").read_text())
    group_of = {series["ticker"]: group for group, payload in panel["groups"].items()
                for series in payload["series"]}
    signals = load_signals(CORRECTED["capex"], CORRECTED["revenue"])
    window = [date for date in dates_full if date >= WINDOW_START]

    def expected_scores(temperature: float) -> dict:
        probabilities = softmax(logits / temperature)
        expected = {}
        order_by_date = {}
        for position, (ticker, decision) in enumerate(zip(tickers, dates)):
            expected.setdefault((ticker, decision), float(
                sum(index * value for index, value in enumerate(probabilities[position]))))
            order_by_date.setdefault(ticker, []).append(decision)
        for ticker in order_by_date:
            order_by_date[ticker] = sorted(set(order_by_date[ticker]))
        scores = {}
        for signal in signals:
            known = [day for day in order_by_date.get(signal["ticker"], []) if day <= signal["filed"]]
            if known:
                scores[(signal["ticker"], signal["filed"])] = expected[(signal["ticker"], known[-1])]
        return scores

    raw_gate = gate_for(expected_scores(1.0), signals, centre=2.0)
    recal_gate = gate_for(expected_scores(fit["temperature"]), signals, centre=2.0)
    runs = {"no_gate_base": ({}, 1.0), "raw_gate_base": ({"gate": raw_gate}, 1.0),
            "recalibrated_gate_base": ({"gate": recal_gate}, 1.0),
            "no_gate_doubled": ({}, 2.0), "raw_gate_doubled": ({"gate": raw_gate}, 2.0),
            "recalibrated_gate_doubled": ({"gate": recal_gate}, 2.0)}
    report["coverage"] = {"raw_gate_signals": len(raw_gate), "recalibrated_gate_signals": len(recal_gate),
                          "signals_in_window": sum(1 for s in signals if s["filed"] >= WINDOW_START)}
    report["runs"] = {}
    for name, (extra, cost_mult) in runs.items():
        result = run({**BASE, "cost_mult": cost_mult, "target_vol": None}, signals, window, prices,
                     adv, group_of, gate=extra.get("gate"))
        report["runs"][name] = {"cohorts": result["cohorts"], "names_median": result["names_median"],
                                "metrics": result["metrics"], "daily": result["daily"]}
    report["intervals"] = {
        "recalibrated_minus_raw_base": month_blocked_interval(report["runs"]["recalibrated_gate_base"]["daily"],
                                                              report["runs"]["raw_gate_base"]["daily"]),
        "recalibrated_minus_no_gate_base": month_blocked_interval(
            report["runs"]["recalibrated_gate_base"]["daily"], report["runs"]["no_gate_base"]["daily"]),
    }
    for name, block in report["runs"].items():
        metrics = block["metrics"]
        print("%-26s cohorts %3d names %4.1f net %+7.2f%% vol %5.1f%% sharpe %+6.3f dd %+6.1f%%" % (
            name, block["cohorts"], block["names_median"] or 0.0, metrics["annual_return"] * 100,
            metrics["annual_vol"] * 100, metrics["sharpe"] or float("nan"),
            metrics["max_drawdown"] * 100))
    print("temperature %.2f | NLL %.4f vs %.4f at T=1" % (fit["temperature"], fit["nll"], fit["nll_at_one"]))
    print("evaluation ECE raw %.4f -> recalibrated %.4f" % (
        report["evaluation_arm"]["raw"]["expected_calibration_error"],
        report["evaluation_arm"]["recalibrated"]["expected_calibration_error"]))
    for name, interval in report["intervals"].items():
        print("%-34s difference %+7.2f%% CI [%s, %s] share+ %s" % (
            name, (interval["point"] or 0.0) * 100,
            f"{interval['lower']*100:+.2f}%" if interval.get("lower") is not None else "n/a",
            f"{interval['upper']*100:+.2f}%" if interval.get("upper") is not None else "n/a",
            round(interval.get("share_positive", float("nan")), 3)))
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    print("written", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
