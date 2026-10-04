#!/usr/bin/env python3
"""Is the intensity charge anything beyond asset growth?

Protocol: docs/plan/intensity-vs-assetgrowth-study.md. Development only. Writes
results/intensity-vs-assetgrowth-study.json.

    python3 scripts/build_intensity_vs_assetgrowth_study.py
"""
from __future__ import annotations

import collections
import csv
import importlib.util
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "results" / "complex-assets-quarterly.csv"
OUT = ROOT / "results" / "intensity-vs-assetgrowth-study.json"
HORIZONS = (5, 20, 60)
DRAWS = 5000
SEED = 42
MIN_NAMES = 4


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


seg = load_module("intensity_segment", ROOT / "scripts" / "build_intensity_segment_study.py")
rank = seg.rank
spearman = seg.spearman
month_gap = seg.month_gap


def main() -> int:
    observations = seg.load_observations()
    assets: dict[str, dict[str, float]] = collections.defaultdict(dict)
    for row in csv.DictReader(ASSETS.open()):
        try:
            assets[row["ticker"]][row["period_end"]] = float(row["value_usd"])
        except ValueError:
            pass

    for observation in observations:
        ticker = observation["ticker"]
        series = assets.get(ticker, {})
        current = next((value for end, value in series.items()
                        if abs(month_gap(end, observation["period_end"])) <= 20), None)
        year_ago_end = f"{int(observation['period_end'][:4]) - 1}{observation['period_end'][4:]}"
        prior = next((value for end, value in series.items()
                      if abs(month_gap(end, year_ago_end)) <= 20), None)
        if current and prior and current > 0 and prior > 0:
            observation["asset_growth"] = __import__("math").log(current / prior)
    usable = [observation for observation in observations if "asset_growth" in observation]

    def residualise(pairs: list[tuple[float, float]]) -> list[float]:
        """Residual of intensity rank after asset growth rank, within the quarter."""
        rx = rank([a for a, _ in pairs])
        ry = rank([b for _, b in pairs])
        n = len(rx)
        mx, my = sum(rx) / n, sum(ry) / n
        covariance = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
        variance = sum((b - my) ** 2 for b in ry)
        slope = covariance / variance if variance else 0.0
        return [a - slope * (b - my) - mx for a, b in zip(rx, ry)]

    report = {"status": "development only; protocol docs/plan/intensity-vs-assetgrowth-study.md",
              "observations": len(usable), "names": len({o["ticker"] for o in usable}), "horizons": {}}
    random.seed(SEED)
    for horizon in HORIZONS:
        key = f"excess_{horizon}"
        rows = [row for row in usable if key in row]
        by_quarter: dict[str, list[dict]] = collections.defaultdict(list)
        for row in rows:
            by_quarter[row["quarter"]].append(row)
        quarters = {quarter: group for quarter, group in by_quarter.items() if len(group) >= MIN_NAMES}
        def stats_for(target: str) -> tuple[float, list[float], int]:
            values, observed_pairs = [], []
            for quarter, group in quarters.items():
                xs = [row["intensity_change"] for row in group]
                ys = [row[key] for row in group]
                if target == "residual":
                    pairs = [(row["intensity_change"], row["asset_growth"]) for row in group]
                    residual = residualise(pairs)
                    correlation = spearman(residual, ys)
                elif target == "asset_growth":
                    correlation = spearman([row["asset_growth"] for row in group], ys)
                else:
                    correlation = spearman(xs, ys)
                if correlation == correlation:
                    values.append((correlation, len(group)))
                observed_pairs.extend(zip(xs, ys))
            if not values:
                return float("nan"), [], 0
            weight = sum(count for _, count in values)
            return sum(value * count for value, count in values) / weight, values, weight
        observed_intensity, _, _ = stats_for("intensity")
        observed_assets, _, _ = stats_for("asset_growth")
        observed_residual, _, _ = stats_for("residual")
        # Null for the residual test: permute intensity ranks within quarter, keep asset growth, recompute.
        null = []
        for _ in range(DRAWS):
            values = []
            for quarter, group in quarters.items():
                ys = [row[key] for row in group]
                shuffled = [row["intensity_change"] for row in group]
                random.shuffle(shuffled)
                pairs = [(shuffled[i], group[i]["asset_growth"]) for i in range(len(group))]
                residual = residualise(pairs)
                correlation = spearman(residual, ys)
                if correlation == correlation:
                    values.append((correlation, len(group)))
            if values:
                total = sum(count for _, count in values)
                null.append(sum(value * count for value, count in values) / total)
        upper = (1 + sum(1 for value in null if value >= observed_residual)) / (1 + len(null))
        lower = (1 + sum(1 for value in null if value <= observed_residual)) / (1 + len(null))
        # predictor overlap
        overlaps = []
        for quarter, group in quarters.items():
            correlation = spearman([row["intensity_change"] for row in group],
                                   [row["asset_growth"] for row in group])
            if correlation == correlation:
                overlaps.append(correlation)
        report["horizons"][str(horizon)] = {
            "n": len(rows), "quarters": len(quarters),
            "intensity_rho": round(observed_intensity, 4),
            "asset_growth_rho": round(observed_assets, 4),
            "intensity_residual_rho": round(observed_residual, 4),
            "residual_two_sided_p": round(min(1.0, 2 * min(upper, lower)), 4),
            "predictor_overlap_mean": round(sum(overlaps) / len(overlaps), 4) if overlaps else None}
    OUT.write_text(json.dumps(report, indent=1) + "\n")
    print(f"observations {len(usable)} across {report['names']} names")
    for horizon, stats in report["horizons"].items():
        print(f"h={horizon}: intensity {stats['intensity_rho']:+.3f}, asset growth {stats['asset_growth_rho']:+.3f}, "
              f"intensity residual {stats['intensity_residual_rho']:+.3f} (p {stats['residual_two_sided_p']}), "
              f"overlap {stats['predictor_overlap_mean']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
