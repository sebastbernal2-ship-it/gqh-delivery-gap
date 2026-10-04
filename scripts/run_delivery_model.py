#!/usr/bin/env python3
"""Ask what moves delivery, controls first, then factors, on data the model did not see.

The object is the project promise, not a price. The question is whether the water factors shift the chance
that a promise moves in a given month, over and above the project controls.

Declared before fitting, so that nothing here becomes a story after the fact:

- **Drought severity**: expected to raise the chance of a revision for water dependent technologies, because
  cooling and hydro output depend on water. Weak or absent for solar and wind.
- **Precipitation anomaly**: expected to raise it, because heavy weather stops site work.
- **Market wide lead time**: a higher share of contractors and equipment makers reporting falling obligations,
  and stronger growth in what they have contracted, are both expected to raise it, because longer lead times
  push schedules.
- **State pipeline momentum**: more planned capacity arriving in a state is expected to raise it, because
  congestion is what a queue is.
- **Fuel and rates**: no sign is declared. They are reported as exploratory, and a coefficient with no
  declared sign is not evidence of anything on its own.
- **Promise horizon**: a control rather than a claim, because a project promised further out has more months
  in which a revision can occur.

Missing factor values are median imputed within technology, and every imputed factor carries a missing flag,
so imputation can never be mistaken for signal. The split is by time: everything through 2019 trains, 2020
onwards tests.

Usage:
    python scripts/run_delivery_model.py
    python scripts/run_delivery_model.py --outcome event_large --factor-set bottleneck
"""
from __future__ import annotations

import argparse
import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from models.hazard import auc, bootstrap, fit, log_likelihood, odds_ratios  # noqa: E402

ENVIRONMENT_FACTORS = ["precip_anomaly", "drought_severity", "gas_level", "rate_level",
                       "lead_time_share_negative", "lead_time_growth", "pipeline_momentum",
                       "promise_horizon_months"]
BOTTLENECK_FACTORS = ["dc_construction_musd", "power_construction_musd", "equipment_construction_musd",
                      "gscpi", "delivery_times", "promise_horizon_months", "pipeline_momentum"]
# Declared signs for the bottleneck set, written before fitting: more building and longer waits are both
# expected to raise the chance that a promise moves.
FACTORS = ENVIRONMENT_FACTORS
EXPLORATORY: set[str] = {"gas_level", "rate_level"}
SPLIT = "2020-01"
WATER_DEPENDENT = ("Conventional Hydroelectric", "Natural Gas Fired Combined Cycle",
                   "Natural Gas Fired Combustion Turbine", "Natural Gas Internal Combustion Engine")
CONSTRUCTION_HEAVY = ("Solar Photovoltaic", "Onshore Wind Turbine", "Batteries")
# For the bottleneck set the split is about heavy equipment: turbines, transformers and switchgear dominate
# these technologies, while solar and batteries are mostly panels, cells and inverters.
EQUIPMENT_HEAVY = ("Onshore Wind Turbine", "Natural Gas Fired Combined Cycle",
                   "Natural Gas Fired Combustion Turbine", "Conventional Hydroelectric")
EQUIPMENT_LIGHT = ("Solar Photovoltaic", "Batteries")

def load(path: Path) -> list[dict]:
    with path.open() as handle:
        return list(csv.DictReader(handle))


def number(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def median_by_technology(rows: list[dict], factor: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for technology in {row["technology"] for row in rows}:
        values = [number(row[factor]) for row in rows
                  if row["technology"] == technology and number(row[factor]) is not None]
        out[technology] = statistics.median(values) if values else 0.0
    return out


def build(rows: list[dict], technologies: list[str], month_effects: bool = False,
          interaction_group: tuple[str, ...] | None = None, objective: str = "event"):
    """Controls, then factors with imputation flags. Returns names, matrix, outcome and months."""
    imputation = {factor: median_by_technology(rows, factor) for factor in FACTORS}
    names = ["log_capacity", "age_months", "start_year"] + [f"tech_{t[:14]}" for t in technologies]
    names += FACTORS + [f"missing_{f}" for f in FACTORS]
    month_names: list[str] = []
    interaction_names: list[str] = []
    if month_effects:
        # Market wide factors are identical for every project in a month, so a time trend absorbs them. Month
        # effects remove that trend and leave the identification to differential exposure.
        month_names = [m for m in sorted({row["month"] for row in rows})][1:]
        names += [f"month_{m}" for m in month_names]
    if interaction_group:
        interaction_names = [f"{factor}_x_group" for factor in FACTORS]
        names += interaction_names
    matrix, outcome, months = [], [], []
    for row in rows:
        technology = row["technology"]
        feature = [number(row["log_capacity"]) or 0.0, number(row["age_months"]) or 0.0,
                   number(row["start_year"]) or 0.0]
        feature += [1.0 if technology == t else 0.0 for t in technologies]
        for factor in FACTORS:
            value = number(row[factor])
            feature.append(value if value is not None else imputation[factor].get(technology, 0.0))
        for factor in FACTORS:
            feature.append(0.0 if number(row[factor]) is not None else 1.0)
        if month_effects:
            feature += [1.0 if row["month"] == m else 0.0 for m in month_names]
        if interaction_group:
            inside = 1.0 if row["technology"] in interaction_group else 0.0
            feature += [feature[3 + len(technologies) + FACTORS.index(f)] * inside for f in FACTORS]
        matrix.append(feature)
        outcome.append(float(row[objective]))
        months.append(row["month"])
    return names, np.array(matrix, dtype=float), np.array(outcome, dtype=float), months


def standardise(train_x, test_x, start: int, end: int):
    """Factors are centred and scaled on training rows only, so test scale cannot leak in."""
    train_out, test_out = train_x.copy(), test_x.copy()
    for column in range(start, end):
        mean = train_x[:, column].mean()
        spread = train_x[:, column].std() or 1.0
        train_out[:, column] = (train_x[:, column] - mean) / spread
        test_out[:, column] = (test_x[:, column] - mean) / spread
    return train_out, test_out


def placebo_block(x, months, start: int, end: int, seed: int = 11):
    """Shuffle the factor block across projects within each month, keeping its joint distribution."""
    rng = np.random.default_rng(seed)
    out = x.copy()
    by_month: dict[str, list[int]] = defaultdict(list)
    for index, month in enumerate(months):
        by_month[month].append(index)
    for indices in by_month.values():
        block = [x[i, start:end].copy() for i in indices]
        order = rng.permutation(len(block))
        for position, index in enumerate(indices):
            out[index, start:end] = block[order[position]]
    return out


def fit_group(rows: list[dict], technologies: list[str], start: int, end: int, trials: int,
              group: tuple[str, ...] | None = None, month_effects: bool = False,
              objective: str = "event"):
    """Fit one subset and return its odds ratios by name, for the specificity comparison."""
    names, x, y, months = build(rows, technologies, month_effects=month_effects,
                                interaction_group=group, objective=objective)
    train = np.array([m < SPLIT for m in months])
    x_train, x_test = standardise(x[train], x[~train], start, end)
    weights, _ = fit(x_train, y[train])
    spread = bootstrap(x_train, y[train], trials=trials)
    by_name = {names[i]: ratio for i, ratio in enumerate(odds_ratios(weights, spread))}
    return by_name, x_train, x_test, y, train


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", default="results/delivery-model-panel.csv")
    parser.add_argument("--outcome", choices=("event", "event_large", "event_withdraw"), default="event",
                        help="which outcome column to model; declared in docs/plan/object-redefinition.md")
    parser.add_argument("--factor-set", choices=("environment", "bottleneck"), default="environment")
    parser.add_argument("--month-effects", action="store_true",
                        help="absorb the calendar so market wide factors are identified by differential exposure")
    parser.add_argument("--interaction-group", default="",
                        help="comma separated technologies that form the exposed group for interactions")
    parser.add_argument("--view", default="results/delivery-model.md")
    parser.add_argument("--coefficients", default="results/delivery-model-coefficients.csv")
    args = parser.parse_args(argv)

    global FACTORS, EXPLORATORY
    if args.factor_set == "bottleneck":
        FACTORS = BOTTLENECK_FACTORS
        EXPLORATORY = set()
        print("bottleneck factor set: signs declared before fitting. Construction spending and delivery times "
              "are both expected to raise the chance of a revision.")
    group = tuple(t.strip() for t in args.interaction_group.split(",") if t.strip()) or None
    rows = load(ROOT / args.panel)
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[row["technology"]] += 1
    technologies = [t for t, _ in sorted(counts.items(), key=lambda kv: -kv[1])[:8]]
    names, x, y, months = build(rows, technologies, month_effects=args.month_effects,
                                interaction_group=group, objective=args.outcome)
    controls_end = 3 + len(technologies)
    factor_end = controls_end + len(FACTORS)
    print(f"objective: {args.outcome} | features: {len(names)} | month effects: {args.month_effects} "
          f"| interaction group: {group}")

    train = np.array([m < SPLIT for m in months])
    print(f"rows: {len(rows)}  train: {int(train.sum())}  test: {int((~train).sum())}")
    print(f"events: train {int(y[train].sum())}, test {int(y[~train].sum())}")

    x_train, x_test = standardise(x[train], x[~train], controls_end, factor_end)
    zeroed_train, zeroed_test = x_train.copy(), x_test.copy()
    zeroed_train[:, controls_end:factor_end] = 0.0
    zeroed_test[:, controls_end:factor_end] = 0.0

    base_weights, _ = fit(zeroed_train, y[train])
    full_weights, _ = fit(x_train, y[train])
    placebo_weights, _ = fit(placebo_block(x_train, list(np.array(months)[train]), controls_end, factor_end),
                             y[train])

    print("")
    print(f"{'model':26s} {'train AUC':>10s} {'test AUC':>9s} {'test log lik':>13s}")
    for label, weights, xs_train, xs_test in (
            ("controls only", base_weights, zeroed_train, zeroed_test),
            ("controls plus factors", full_weights, x_train, x_test),
            ("placebo factors", placebo_weights, x_train, x_test)):
        print(f"{label:26s} {auc(xs_train, y[train], weights):>10.4f} "
              f"{auc(xs_test, y[~train], weights):>9.4f} "
              f"{log_likelihood(xs_test, y[~train], weights):>13.1f}")

    spread = bootstrap(x_train, y[train], trials=30)
    ratios = odds_ratios(full_weights, spread)
    print("")
    print("odds ratios per standard deviation, with a bootstrap interval:")
    coefficients = []
    for position, name in enumerate(names):
        if position < controls_end:
            continue
        if args.month_effects and name.startswith("month_"):
            continue
        if args.month_effects and not name.endswith("_x_group"):
            continue
        ratio = ratios[position]
        note = "exploratory, no sign declared" if name in EXPLORATORY else ""
        flag = "spans one" if ratio["spans_one"] else "clear of one"
        print(f"  {name:28s} {ratio['odds_ratio']:6.3f} [{ratio['odds_low']:6.3f}, "
              f"{ratio['odds_high']:6.3f}] {flag:12s} {note}")
        coefficients.append({"name": name, "odds_ratio": round(ratio["odds_ratio"], 4),
                             "odds_low": round(ratio["odds_low"], 4),
                             "odds_high": round(ratio["odds_high"], 4),
                             "spans_one": ratio["spans_one"], "note": note})

    with (ROOT / args.coefficients).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(coefficients[0]))
        writer.writeheader()
        writer.writerows(coefficients)

    print("")
    print("specificity: the same model on two groups the mechanism treats differently")
    if args.factor_set == "bottleneck":
        pairs = (("equipment heavy", EQUIPMENT_HEAVY), ("equipment light", EQUIPMENT_LIGHT))
        focus = ("gscpi", "delivery_times")
    else:
        pairs = (("water dependent", WATER_DEPENDENT), ("construction heavy", CONSTRUCTION_HEAVY))
        focus = ("drought_severity", "precip_anomaly")
    print(f"{'group':20s} {'rows':>7s} {focus[0][:11]:>12s} {focus[1][:12]:>13s}")
    lines = []
    for label, group in pairs:
        subset = [row for row in rows if row["technology"] in group]
        if len(subset) < 500:
            print(f"{label:22s} {len(subset):>7d} too few rows")
            continue
        by_name, _, _, _, _ = fit_group(subset, technologies, controls_end, factor_end, 12, group,
                                        args.month_effects, objective=args.outcome)
        first = by_name.get(focus[0], {})
        second = by_name.get(focus[1], {})
        print(f"{label:20s} {len(subset):>7d} {first.get('odds_ratio', float('nan')):>12.3f} "
              f"{second.get('odds_ratio', float('nan')):>13.3f}")
        lines.append(f"| {label} | {len(subset)} | "
                     f"{first.get('odds_ratio', float('nan')):.3f} "
                     f"[{first.get('odds_low', float('nan')):.3f}, "
                     f"{first.get('odds_high', float('nan')):.3f}] | "
                     f"{second.get('odds_ratio', float('nan')):.3f} "
                     f"[{second.get('odds_low', float('nan')):.3f}, "
                     f"{second.get('odds_high', float('nan')):.3f}] |")

    view = ["# What moves delivery", "",
            "Generated by `make delivery-model`. The object is a project promise, not a price.", "",
            f"Rows: {len(rows)} project months, {int(y.sum())} of them revision months. "
            f"Training through 2019, testing from 2020.", "",
            "## Specificity", "",
            f"| group | rows | {focus[0]} odds ratio | {focus[1]} odds ratio |",
            "|---|---|---|---|"] + lines + [
            "", "Signs were declared before fitting. Drought and precipitation are expected to raise the",
            "chance of a revision. Fuel and rates carry no declared sign, so their coefficients are",
            "exploratory and cannot be evidence on their own.", ""]
    Path(ROOT / args.view).write_text("\n".join(view))
    print("")
    print(f"wrote {args.view} and {args.coefficients}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
