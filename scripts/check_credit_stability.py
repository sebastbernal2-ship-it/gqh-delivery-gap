#!/usr/bin/env python3
"""Stability and cost gates for the long window credit survivors.

Declared AFTER the long grid ran, on purpose and with the label attached: these checks can only weaken a
result, never upgrade one. They exist because six survivors at p at most 0.05 on a 24 test grid is exactly
the shape that a single regime or a handful of extreme days can produce.

Four checks, one row per surviving pair from the long grid:

1. **Sub period halves.** Sign and magnitude in each half of the development window.
2. **Influence.** Recompute after dropping the ten largest absolute credit changes.
3. **Sign agreement.** A measure whose names disagree in sign is one cluster behaving two ways, not a relation.
4. **The cost gate.** The implied per day excess return against a declared round trip cost, in basis points.

Usage:
    python scripts/check_credit_stability.py
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from run_credit_gauntlet import (  # noqa: E402
    DEVELOPMENT_END, HORIZONS, MARKET, NAMES, changes, load_panel, pearson, returns, slope,
)

PANEL = ROOT / "results" / "credit-panel.csv"
LONG = ROOT / "results" / "credit-gauntlet-long.json"
OUT_CSV = ROOT / "results" / "credit-stability.csv"
OUT_JSON = ROOT / "results" / "credit-stability.json"

# Declared round trip cost for a liquid name, in basis points of notional. Spread plus impact plus fees.
ROUND_TRIP_COST_BPS = 10.0


def main() -> int:
    long_result = json.loads(LONG.read_text())
    survivors = [(row["measure"], row["name"], int(row["horizon_days"])) for row in long_result["survivors"]]
    if not survivors:
        raise SystemExit("no survivors to check")

    panel = load_panel(PANEL)
    dates = sorted({stamp for series in panel.values() for stamp in series})
    dates = [stamp for stamp in dates if stamp <= DEVELOPMENT_END]

    market_returns = {lag: returns(panel[MARKET], dates, lag) for lag in HORIZONS}
    forward = {}
    for lag in HORIZONS:
        forward[lag] = {}
        for name in NAMES:
            own = returns(panel[f"equity:{name}"], dates, lag)
            forward[lag][name] = {stamp: own[stamp] - market_returns[lag][stamp]
                                  for stamp in own if stamp in market_returns[lag]}

    changes_by_measure = {measure: changes(panel[measure], dates) for measure, _, _ in survivors}

    rows: list[dict] = []
    for measure, name, lag in survivors:
        credit = changes_by_measure[measure]
        stamps = sorted(set(credit) & set(forward[lag][name]))
        xs = [credit[stamp] for stamp in stamps]
        ys = [forward[lag][name][stamp] for stamp in stamps]
        full_r = pearson(xs, ys) or 0.0
        implied_r = (slope(xs, ys) or 0.0) * statistics.pstdev(xs)
        implied_gross_bps = implied_r * 10000.0

        middle = len(stamps) // 2
        first_r = pearson(xs[:middle], ys[:middle]) or 0.0
        second_r = pearson(xs[middle:], ys[middle:]) or 0.0

        extremes = sorted(range(len(xs)), key=lambda index: abs(xs[index]), reverse=True)[:10]
        keep = [index for index in range(len(xs)) if index not in extremes]
        dropped_r = pearson([xs[i] for i in keep], [ys[i] for i in keep]) or 0.0

        rows.append({
            "measure": measure, "name": name, "horizon_days": lag, "n": len(xs),
            "correlation": round(full_r, 6),
            "first_half_r": round(first_r, 6), "second_half_r": round(second_r, 6),
            "sign_stable_across_halves": (first_r > 0) == (second_r > 0),
            "r_after_dropping_top_10_days": round(dropped_r, 6),
            "survives_influence_check": (full_r > 0) == (dropped_r > 0) and abs(dropped_r) >= 0.5 * abs(full_r),
            "implied_gross_bps_per_day": round(implied_gross_bps, 3),
            "round_trip_cost_bps": ROUND_TRIP_COST_BPS,
            "clears_cost_gate": implied_gross_bps > ROUND_TRIP_COST_BPS,
        })

    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    by_measure: dict[str, list[str]] = {}
    for row in rows:
        by_measure.setdefault(row["measure"], []).append(
            "+" if row["correlation"] > 0 else "-")
    summary = {
        "survivors_checked": len(rows),
        "sign_stable_across_halves": sum(row["sign_stable_across_halves"] for row in rows),
        "survive_influence_check": sum(row["survives_influence_check"] for row in rows),
        "clear_cost_gate": sum(row["clears_cost_gate"] for row in rows),
        "round_trip_cost_bps": ROUND_TRIP_COST_BPS,
        "largest_implied_gross_bps_per_day": max(row["implied_gross_bps_per_day"] for row in rows),
        "measure_sign_pattern": {measure: signs for measure, signs in by_measure.items()},
        "sign_agreement_within_measure": {measure: len(set(signs)) == 1
                                          for measure, signs in by_measure.items()},
        "declared_after_the_grid": True,
        "what_this_can_do": "weaken the finding only; it cannot upgrade a result",
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2) + "\n")

    print(f"checked {len(rows)} survivors")
    for row in rows:
        print(f"  {row['measure']:18s} {row['name']:4s} h={row['horizon_days']} r={row['correlation']:+.4f} "
              f"halves={row['first_half_r']:+.3f}/{row['second_half_r']:+.3f} "
              f"drop10={row['r_after_dropping_top_10_days']:+.4f} "
              f"gross={row['implied_gross_bps_per_day']:6.2f}bps "
              f"cost={row['round_trip_cost_bps']:.0f}bps clear={row['clears_cost_gate']}")
    print()
    print(f"sign stable across halves: {summary['sign_stable_across_halves']} of {len(rows)}")
    print(f"survives the influence check: {summary['survive_influence_check']} of {len(rows)}")
    print(f"clears the {ROUND_TRIP_COST_BPS:.0f} bps cost gate: {summary['clear_cost_gate']} of {len(rows)}")
    print(f"largest implied gross edge: {summary['largest_implied_gross_bps_per_day']:.2f} bps per day")
    print(f"sign agreement within each measure: {summary['sign_agreement_within_measure']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
