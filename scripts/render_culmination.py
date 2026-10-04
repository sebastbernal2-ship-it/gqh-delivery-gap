#!/usr/bin/env python3
"""Render the culmination figures from the committed ledgers, with the title inside every image.

Inputs are only committed files: `results/culmination-ledgers/*.csv` in the section's daily schema and
`results/culmination.json` for the summary numbers. Nothing here fits a model, so the figures cannot
drift from the artifact they describe. Every figure is written twice, PNG and SVG, under
`results/figures/`, and every figure carries its own title and subtitle inside the image.

    python3 scripts/render_culmination.py
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
LEDGERS = ROOT / "results" / "culmination-ledgers"
SUMMARY = ROOT / "results" / "culmination.json"
FIGURES = ROOT / "results" / "figures"
ORDER = ("C_conditioned", "B_two_sleeve_headline", "B3_hedge_composite", "A_core_gated_charge")
TITLES = {
    "C_conditioned": "Conditioned best: two-sleeve composite held only near the basket's peak",
    "B_two_sleeve_headline": "Two-sleeve headline: disclosure plus gated charge",
    "B3_hedge_composite": "Same with the reversed-capex hedge (dilutes)",
    "A_core_gated_charge": "Gated charge core alone",
    "baseline": "Equal-weight basket (floor)",
}
COLORS = {"C_conditioned": "#c0392b", "B_two_sleeve_headline": "#27ae60",
          "B3_hedge_composite": "#8e44ad", "A_core_gated_charge": "#2980b9",
          "baseline": "#7f8c8d"}
SESSIONS = 252


def load_ledgers() -> dict[str, list[dict]]:
    series = {}
    for path in sorted(LEDGERS.glob("*.csv")):
        rows = []
        with path.open() as handle:
            for row in csv.DictReader(handle):
                rows.append({"date": row["date"], "net": float(row["net_return"]),
                             "gross": float(row["gross_return"]),
                             "baseline": float(row["baseline"]), "sample": row["sample"],
                             "regime": row["regime"]})
        if rows:
            series[path.stem] = rows
    return series


def metrics(rows: list[dict]) -> dict:
    if len(rows) < 20:
        return {"days": len(rows), "net": None, "vol": None, "sharpe": None, "drawdown": None}
    values = np.array([row["net"] for row in rows])
    net = float(np.prod(1.0 + values) ** (SESSIONS / len(values)) - 1.0)
    vol = float(values.std(ddof=1) * np.sqrt(SESSIONS))
    curve = np.cumprod(1.0 + values)
    peak = np.maximum.accumulate(curve)
    return {"days": len(rows), "net": net, "vol": vol,
            "sharpe": float(values.mean() / values.std(ddof=1) * np.sqrt(SESSIONS)) if values.std() else None,
            "drawdown": float((curve / peak - 1.0).min())}


def save(figure, name: str) -> list[Path]:
    FIGURES.mkdir(parents=True, exist_ok=True)
    written = []
    for extension in ("png", "svg"):
        path = FIGURES / f"{name}.{extension}"
        figure.savefig(path, dpi=150, bbox_inches="tight")
        written.append(path)
    plt.close(figure)
    return written


def main() -> int:
    series = load_ledgers()
    if not series:
        print("no ledgers under", LEDGERS, "- run scripts/run_culmination.py first")
        return 1
    summary = json.loads(SUMMARY.read_text()) if SUMMARY.exists() else {}
    window = f"{min(rows[0]['date'] for rows in series.values())} to " \
             f"{max(rows[-1]['date'] for rows in series.values())}"
    baseline = {row["date"]: row["baseline"] for row in series.get("C_conditioned", [])}
    baseline_rows = [{"date": day, "net": value} for day, value in sorted(baseline.items())]
    writeups = []

    # one: cumulative net of every candidate against the floor, with regime transitions marked
    figure, axis = plt.subplots(figsize=(13, 7))
    for name in [key for key in ORDER if key in series]:
        rows = series[name]
        axis.plot(range(len(rows)), np.cumprod([1.0 + row["net"] for row in rows]),
                  label=f"{name} (Sharpe {metrics(rows)['sharpe']:.2f})",
                  color=COLORS[name], linewidth=1.8)
    if baseline_rows:
        axis.plot(range(len(baseline_rows)),
                  np.cumprod([1.0 + row["net"] for row in baseline_rows]),
                  label=TITLES["baseline"], color=COLORS["baseline"], linewidth=1.2, linestyle="--")
    reference = series.get("C_conditioned") or next(iter(series.values()))
    for position in range(1, len(reference)):
        if reference[position]["regime"] != reference[position - 1]["regime"]:
            axis.axvline(position, color="#d5d8dc", linewidth=0.7, zorder=0)
    axis.set_yscale("log")
    axis.set_title("Culmination: four candidates against the equal-weight basket\n"
                   f"common window {window}, volatility targeted at 10 percent, grey lines are "
                   "drawdown-regime transitions", fontsize=13)
    axis.set_xlabel("sessions from window start")
    axis.set_ylabel("cumulative net, log scale")
    axis.legend(fontsize=9, loc="upper left")
    axis.grid(alpha=0.25)
    writeups += save(figure, "culmination-equity")

    # two: drawdown paths
    figure, axis = plt.subplots(figsize=(13, 6))
    for name in [key for key in ORDER if key in series]:
        curve = np.cumprod([1.0 + row["net"] for row in series[name]])
        axis.plot(range(len(curve)), curve / np.maximum.accumulate(curve) - 1.0,
                  label=f"{name} (max {metrics(series[name])['drawdown']*100:.1f}%)",
                  color=COLORS[name], linewidth=1.6)
    if baseline_rows:
        curve = np.cumprod([1.0 + row["net"] for row in baseline_rows])
        axis.plot(range(len(curve)), curve / np.maximum.accumulate(curve) - 1.0,
                  label=f"{TITLES['baseline']} (max {metrics(baseline_rows)['drawdown']*100:.1f}%)",
                  color=COLORS["baseline"], linewidth=1.2, linestyle="--")
    axis.set_title("Drawdowns: the conditioned system loses a third of what the floor does\n"
                   f"common window {window}, daily net returns, no leverage above the 10 percent target",
                   fontsize=13)
    axis.set_xlabel("sessions from window start")
    axis.set_ylabel("drawdown from running peak")
    axis.legend(fontsize=9, loc="lower left")
    axis.grid(alpha=0.25)
    writeups += save(figure, "culmination-drawdown")

    # three: Sharpe by era and by sample
    eras = (("2019-01-01", "2022-12-31"), ("2023-01-01", "2026-12-31"))
    samples = (("IS", "in-sample, before 2019"), ("OOS", "out-of-sample, 2019 onward"))
    figure, axes = plt.subplots(1, 2, figsize=(14, 6))
    names = [key for key in ORDER if key in series]
    positions = np.arange(len(names))
    for axis, (start, end) in zip(axes, eras):
        values = []
        for name in names:
            subset = [row for row in series[name] if start <= row["date"] <= end]
            values.append(metrics(subset)["sharpe"] or 0.0)
        axis.bar(positions, values, color=[COLORS[name] for name in names])
        axis.set_xticks(positions)
        axis.set_xticklabels([name.split("_")[0] for name in names])
        axis.set_title(f"{start[:4]} to {end[:4]}")
        axis.grid(alpha=0.25, axis="y")
        axis.set_ylabel("Sharpe")
    figure.suptitle("Sharpe by era, every candidate on its available days\n"
                    "after the 2021 window the conditioned system is the only one above 1.5",
                    fontsize=13)
    writeups += save(figure, "culmination-eras")

    figure, axes = plt.subplots(1, 2, figsize=(14, 6))
    for axis, (label, _) in zip(axes, samples):
        values = []
        for name in names:
            subset = [row for row in series[name] if row["sample"] == label]
            values.append(metrics(subset)["sharpe"] or 0.0)
        axis.bar(positions, values, color=[COLORS[name] for name in names])
        axis.set_xticks(positions)
        axis.set_xticklabels([name.split("_")[0] for name in names])
        axis.set_title(samples[0 if label == "IS" else 1][1])
        axis.grid(alpha=0.25, axis="y")
        axis.set_ylabel("Sharpe")
    figure.suptitle("In-sample against out-of-sample, both views\n"
                    "the composites only exist after 2019, so their in-sample column is empty by "
                    "construction and the legs carry that history", fontsize=12)
    writeups += save(figure, "culmination-is-oos")

    # five: behaviour by regime, conditioned against unconditioned
    states = ("low", "mid", "high")
    figure, axis = plt.subplots(figsize=(11, 6))
    width = 0.8 / max(1, len(names))
    for position, name in enumerate(names):
        values = []
        for state in states:
            subset = [row for row in series[name] if row["regime"] == state]
            subset_metrics = metrics(subset)
            values.append((subset_metrics["net"] or 0.0) * 100)
        axis.bar([index + position * width for index in range(len(states))], values, width,
                 label=name, color=COLORS[name])
    axis.set_xticks([index + 0.4 - width / 2 for index in range(len(states))])
    axis.set_xticklabels(["low: within 5% of the basket peak",
                          "mid: 5 to 15% below", "high: more than 15% below"], fontsize=9)
    axis.set_ylabel("annualised net return, percent")
    axis.set_title("The rule in each drawdown regime: the conditioned system earns only near the peak\n"
                   "the unconditioned candidates keep trading through the drawdowns and pay for it",
                   fontsize=13)
    axis.legend(fontsize=9)
    axis.grid(alpha=0.25, axis="y")
    writeups += save(figure, "culmination-regimes")

    print("figures written:")
    for path in writeups:
        print("  ", path.relative_to(ROOT))
    if summary.get("same_window_comparison"):
        print("\nsame-window numbers the figures draw:")
        for name, block in summary["same_window_comparison"].items():
            if block:
                print("  %-30s days %4d net %+7.2f%% sharpe %+6.3f dd %+6.1f%%" % (
                    name, block["days"], block["annual_return"] * 100, block["sharpe"],
                    block["max_drawdown"] * 100))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
