#!/usr/bin/env python3
"""Render the culmination: equity with regime boundaries, per-era and per-regime comparison bars.

Everything is drawn from results/culmination.json, so the figures cannot disagree with the numbers.
Regime boundaries are the transitions of the rule the honest walk-forward chose, the basket's own
drawdown state, and they are drawn as vertical markers exactly as the captain asked.

    python3 scripts/render_culmination.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FIGURES = ROOT / "results" / "figures"
COLORS = {"A_core_gated_charge": "#1f77b4", "B_two_sleeve_headline": "#2ca02c",
          "B3_with_reversed_capex_hedge": "#9467bd", "C_conditioned_walk_forward": "#d62728",
          "long_floor": "#7f7f7f"}


def main() -> int:
    report = json.loads((ROOT / "results" / "culmination.json").read_text())
    FIGURES.mkdir(parents=True, exist_ok=True)

    # every series as (dates, returns) for the common window so the comparison is honest
    import csv
    series: dict[str, tuple[list[str], list[float]]] = {}
    state_path = ROOT / "results" / "culmination-series.json"
    if state_path.exists():
        payload = json.loads(state_path.read_text())
        for name, rows in payload.items():
            series[name] = ([row["date"] for row in rows], [row["net"] for row in rows])
    if not series:
        print("no stored series; run the analysis first")
        return 1

    # figure one: cumulative net with regime boundaries
    figure, axis = plt.subplots(figsize=(12, 6.5))
    boundaries = report.get("regime_walk_forward", {}).get("boundaries") or []
    state_series = series.pop("__state__", None)
    for name, (dates, returns) in series.items():
        curve = np.cumprod([1.0 + value for value in returns])
        axis.plot(range(len(dates)), curve, label=name, color=COLORS.get(name, None), linewidth=1.6)
    if state_series:
        state_dates, states = state_series
        for position in range(1, len(states)):
            if states[position] != states[position - 1]:
                axis.axvline(position, color="#cccccc", linewidth=0.8, zorder=0)
        axis.set_title("Culmination equity, common window, grey lines are regime transitions")
    else:
        axis.set_title("Culmination equity, common window")
    axis.set_yscale("log")
    axis.set_xlabel("sessions from window start")
    axis.set_ylabel("cumulative net (log scale)")
    axis.legend(loc="upper left", fontsize=9)
    axis.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(FIGURES / "culmination-equity.svg")
    plt.close(figure)

    # figure two: Sharpe by era and candidate
    eras = ["2019-2022", "2023-2026"]
    candidates = [name for name in report["candidates"]]
    figure, axis = plt.subplots(figsize=(10, 5))
    width = 0.8 / max(1, len(candidates))
    for position, name in enumerate(candidates):
        values = []
        for era in eras:
            block = report["candidates"][name]["eras"].get(era) or {}
            metrics = block.get("metrics") or {}
            values.append(metrics.get("sharpe") or 0.0)
        axis.bar([index + position * width for index in range(len(eras))], values, width,
                 label=name, color=COLORS.get(name, None))
    axis.set_xticks([index + 0.4 - width / 2 for index in range(len(eras))])
    axis.set_xticklabels(eras)
    axis.set_ylabel("Sharpe")
    axis.set_title("Sharpe by era, every candidate on its own available days")
    axis.legend(fontsize=8)
    axis.grid(alpha=0.25, axis="y")
    figure.tight_layout()
    figure.savefig(FIGURES / "culmination-eras.svg")
    plt.close(figure)

    # figure three: conditioned against unconditioned over the same window
    same = report.get("same_window_comparison") or {}
    figure, axis = plt.subplots(figsize=(10, 5))
    names = [name for name in same if same[name]]
    sharpes = [same[name]["sharpe"] for name in names]
    drawdowns = [abs(same[name]["max_drawdown"]) for name in names]
    positions = np.arange(len(names))
    axis.bar(positions - 0.2, sharpes, 0.4, label="Sharpe", color="#2ca02c")
    axis.bar(positions + 0.2, drawdowns, 0.4, label="max drawdown (absolute)", color="#d62728")
    axis.set_xticks(positions)
    axis.set_xticklabels([name.replace("_", " ") for name in names], fontsize=8, rotation=15, ha="right")
    axis.set_title("Same window: conditioned against the unconditioned headline and the floor")
    axis.legend()
    axis.grid(alpha=0.25, axis="y")
    figure.tight_layout()
    figure.savefig(FIGURES / "culmination-regimes.svg")
    plt.close(figure)

    print("wrote", FIGURES / "culmination-equity.svg")
    print("wrote", FIGURES / "culmination-eras.svg")
    print("wrote", FIGURES / "culmination-regimes.svg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
