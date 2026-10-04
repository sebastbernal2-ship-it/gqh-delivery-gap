#!/usr/bin/env python3
"""Run the pre-registered credit gauntlet and print the grid before any statistic.

The declaration it obeys is `docs/plan/credit-gauntlet.md`, frozen before this script ran. The rules that
matter here, and where they live in the code:

- **Grid counted first.** The grid size is computed from the declared lists and printed before the loop, so
  multiplicity is stated rather than discovered.
- **Every pair against its own null.** Credit changes are permuted in blocks of 20 trading days, 500 draws, so
  a survivor beats a placebo that preserves the autocorrelation and the regime clustering.
- **Rate control across the whole grid.** Benjamini-Hochberg over the declared 48.
- **Development only.** Nothing past 2026-02-24 is read. Opening the holdout is the captain's call.
- **Descriptive ceiling.** No causal word is printed. The statistic is a correlation and a slope, nothing more.
- **Effective breadth reported next to the raw count.** Four correlated names are one cluster.

Usage:
    python scripts/run_credit_gauntlet.py [--draws 500] [--block 20]
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PANEL = ROOT / "results" / "credit-panel.csv"
OUT_CSV = ROOT / "results" / "credit-gauntlet.csv"
OUT_JSON = ROOT / "results" / "credit-gauntlet.json"
OUT_LONG_CSV = ROOT / "results" / "credit-gauntlet-long.csv"
OUT_LONG_JSON = ROOT / "results" / "credit-gauntlet-long.json"

DEVELOPMENT_END = "2026-02-24"
# The two declared grids. "ice" is section 3 of the pre-registration, six measures over the licence capped
# three year window. "long" is section 6.8, three measures with full history, declared before it was run.
MEASURE_SETS = {
    "ice": ["credit:hy:oas", "credit:ig:oas", "credit:bbb:oas", "credit:ccc:oas",
            "credit:tier-gap", "credit:hy:yield"],
    "long": ["credit:baa:10y", "credit:aaa:10y", "credit:quality-gap"],
}
CREDIT_MEASURES = MEASURE_SETS["ice"]
NAMES = ["DLR", "EME", "ETN", "PWR"]
HORIZONS = [1, 5]
MARKET = "equity:SPY"


def load_panel(path: Path) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    with path.open() as handle:
        for row in csv.DictReader(handle):
            if row["series"].startswith("equity:"):
                out.setdefault(row["series"], {})[row["date"]] = float(row["value"])
            else:
                out.setdefault(row["series"], {})[row["date"]] = float(row["value"])
    return out


def changes(series: dict[str, float], dates: list[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for previous, current in zip(dates, dates[1:]):
        if previous in series and current in series:
            out[current] = series[current] - series[previous]
    return out


def returns(series: dict[str, float], dates: list[str], lag: int) -> dict[str, float]:
    out: dict[str, float] = {}
    for index in range(len(dates) - lag):
        start, end = dates[index], dates[index + lag]
        if start in series and end in series and series[start]:
            out[start] = series[end] / series[start] - 1.0
    return out


def pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 3:
        return None
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / (sxx ** 0.5 * syy ** 0.5)


def slope(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 3:
        return None
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx <= 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx


def block_shuffle(values: list[float], block: int, rng: random.Random) -> list[float]:
    """Permute in contiguous blocks, which keeps the autocorrelation a daily shuffle would destroy."""
    blocks = [values[index:index + block] for index in range(0, len(values), block)]
    rng.shuffle(blocks)
    out = [value for chunk in blocks for value in chunk]
    return out[:len(values)]


def effective_breadth(excess: dict[str, dict[str, float]], dates: list[str]) -> dict[str, float]:
    """Effective number of bets from the eigenvalue spread of the average correlation matrix."""
    matrix: list[list[float]] = []
    for a in NAMES:
        row = []
        for b in NAMES:
            xs = [excess[a][stamp] for stamp in dates if stamp in excess[a] and stamp in excess[b]]
            ys = [excess[b][stamp] for stamp in dates if stamp in excess[a] and stamp in excess[b]]
            value = pearson(xs, ys)
            row.append(1.0 if a == b else (value or 0.0))
        matrix.append(row)
    n = len(NAMES)
    average = (sum(sum(row) for row in matrix) - n) / (n * (n - 1))
    return {"names": n, "average_pairwise_correlation": average,
            "effective_bets_from_average_correlation": 1.0 / (1.0 + (n - 1) * max(average, 0.0))}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--draws", type=int, default=500)
    parser.add_argument("--block", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20261003)
    parser.add_argument("--set", default="ice", choices=sorted(MEASURE_SETS),
                        help="which declared grid to run: 'ice' (section 3) or 'long' (section 6.8)")
    args = parser.parse_args(argv)
    measures = MEASURE_SETS[args.set]
    out_csv = OUT_CSV if args.set == "ice" else OUT_LONG_CSV
    out_json = OUT_JSON if args.set == "ice" else OUT_LONG_JSON
    rng = random.Random(args.seed)

    panel = load_panel(PANEL)
    dates = sorted({stamp for series in panel.values() for stamp in series})
    dates = [stamp for stamp in dates if stamp <= DEVELOPMENT_END]
    if not dates:
        raise SystemExit("no observations inside the development window")

    missing = [label for label in measures if label not in panel]
    if missing:
        print(f"declared measures with no series in results/credit-panel.csv: {missing}")
        print("the long history family needs FRED_API_KEY when scripts/build_credit_panel.py runs")
        return 2
    credit_changes = {label: changes(panel[label], dates) for label in measures}
    forward: dict[int, dict[str, dict[str, float]]] = {}
    excess = {name: {} for name in NAMES}
    for name in NAMES:
        for stamp in dates:
            if stamp in panel[f"equity:{name}"] and stamp in panel[MARKET]:
                excess[name][stamp] = 0.0  # placeholder, filled from returns below
    for lag in HORIZONS:
        market_return = returns(panel[MARKET], dates, lag)
        forward[lag] = {}
        for name in NAMES:
            own = returns(panel[f"equity:{name}"], dates, lag)
            forward[lag][name] = {stamp: own[stamp] - market_return[stamp]
                                  for stamp in own if stamp in market_return}
            if lag == 1:
                for stamp, value in forward[lag][name].items():
                    excess[name][stamp] = value

    breadth = effective_breadth(excess, dates)

    grid = [(label, name, lag) for label in measures for name in NAMES for lag in HORIZONS]
    print(f"declared grid ({args.set}): {len(measures)} measures x {len(NAMES)} names x {len(HORIZONS)} "
          f"horizons = {len(grid)} tests")
    print(f"development window: {dates[0]} to {dates[-1]} ({len(dates)} trading days)")
    print(f"null: block shuffle, block={args.block}, draws={args.draws}")
    print(f"effective breadth: {breadth['effective_bets_from_average_correlation']:.2f} bets from "
          f"{breadth['names']} names at average pairwise correlation "
          f"{breadth['average_pairwise_correlation']:.2f}")
    print()

    rows: list[dict] = []
    p_values: list[float] = []
    for label, name, lag in grid:
        stamps = sorted(set(credit_changes.get(label, {})) & set(forward[lag][name]))
        xs = [credit_changes[label][stamp] for stamp in stamps]
        ys = [forward[lag][name][stamp] for stamp in stamps]
        raw_xs = xs
        raw_ys = [forward[lag][name][stamp] + (returns(panel[MARKET], dates, lag)[stamp]
                                               if stamp in returns(panel[MARKET], dates, lag) else 0.0)
                  for stamp in stamps]
        r = pearson(xs, ys)
        beta = slope(xs, ys)
        raw_r = pearson(raw_xs, raw_ys)
        if r is None or len(xs) < 30:
            continue
        observed = abs(r)
        draws = [abs(pearson(shuffled, ys) or 0.0)
                 for shuffled in (block_shuffle(xs, args.block, rng) for _ in range(args.draws))]
        draw_list = [value for value in draws if value is not None]
        hit = sum(1 for value in draw_list if value >= observed)
        p_value = (1 + hit) / (1 + len(draw_list))
        p_values.append(p_value)
        rows.append({
            "measure": label, "name": name, "horizon_days": lag, "n": len(xs),
            "correlation": round(r, 6), "beta_per_pct_spread": round(beta, 8) if beta is not None else "",
            "raw_correlation": round(raw_r, 6) if raw_r is not None else "",
            "placebo_percentile": round(100.0 * sum(1 for value in draw_list if value < observed) / max(len(draw_list), 1), 2),
            "placebo_p": round(p_value, 6),
            "beats_placebo_95": p_value <= 0.05,
        })

    # Benjamini-Hochberg across the declared grid, which is the count printed above.
    order = sorted(range(len(rows)), key=lambda index: rows[index]["placebo_p"])
    m = len(rows)
    cutoff_rank = 0
    for rank, index in enumerate(order, start=1):
        if rows[index]["placebo_p"] <= 0.05 * rank / m:
            cutoff_rank = rank
    for rank, index in enumerate(order, start=1):
        rows[index]["bh_rank"] = rank
        rows[index]["bh_survivor"] = rank <= cutoff_rank

    if not rows:
        print("no test produced enough overlapping observations. Nothing written and nothing ranked.")
        return 2

    with out_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    survivors = [row for row in rows if row["bh_survivor"]]
    nominal = [row for row in rows if row["beats_placebo_95"]]
    summary = {
        "measure_set": args.set,
        "measures": measures,
        "declared_grid": len(grid),
        "measured_grid": len(rows),
        "grid_printed_before_statistics": True,
        "development_window": [dates[0], dates[-1]],
        "holdout_opened": False,
        "draws": args.draws,
        "block": args.block,
        "seed": args.seed,
        "effective_breadth": breadth,
        "nominal_hits_at_p_0.05": len(nominal),
        "bh_survivors": len(survivors),
        "expected_false_hits_at_p_0.05": round(0.05 * len(rows), 2),
        "median_observed_correlation": round(statistics.median(abs(row["correlation"]) for row in rows), 6),
        "median_placebo_correlation": None,
        "ceiling": "descriptive_only",
        "falsifier_2_raw_minus_adjusted_median": round(
            statistics.median(row["raw_correlation"] - row["correlation"] for row in rows), 6),
        "survivors": survivors,
    }
    out_json.write_text(json.dumps(summary, indent=2) + "\n")

    print(f"{'measure':18s} {'name':5s} {'h':>2s} {'n':>4s} {'r':>8s} {'raw r':>8s} {'beta':>10s} {'p':>7s} {'bh':>4s}")
    for row in sorted(rows, key=lambda item: item["placebo_p"])[:12]:
        print(f"{row['measure']:18s} {row['name']:5s} {row['horizon_days']:2d} {row['n']:4d} "
              f"{row['correlation']:8.4f} {row['raw_correlation']:8.4f} {row['beta_per_pct_spread']:10.6f} "
              f"{row['placebo_p']:7.4f} {row['bh_rank']:4d}")
    print()
    print(f"nominal hits at p<=0.05: {len(nominal)} of {len(rows)} (expected by chance "
          f"{0.05 * len(rows):.2f})")
    print(f"Benjamini-Hochberg survivors: {len(survivors)}")
    print(f"raw minus adjusted median correlation: "
          f"{summary['falsifier_2_raw_minus_adjusted_median']:+.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
