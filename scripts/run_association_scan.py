#!/usr/bin/env python3
"""Scan the declared node pairs, with each pair measured against its own generated null.

The rules the framework demands, and where each one lives in this file:

- **Coverage before measurement**: pairs come from the declared node space, not from what happens to have
  data. A node whose series is not wired is reported as missing with a reason.
- **Multiplicity counted first**: the pair count and the number of pairs measured are printed before any
  statistic, by check_scan.py and again in the summary.
- **Every pair calibrated**: each is measured against a block-shuffled null and a twelve-month seasonal
  shift, so a survivor has beaten its own placebo rather than a textbook p-value.
- **Nothing is a strategy**: a survivor is a candidate for a mechanism conversation, and the report says so.

Usage:
    python scripts/run_association_scan.py --draws 200
"""
from __future__ import annotations

import argparse
import csv
import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from check_scan import load, pairs  # noqa: E402
from scan.windows import FIREWALL, clip, describe, get  # noqa: E402
from scan.series import build  # noqa: E402
from scan.report import summarise as correction_summary  # noqa: E402
from scan.stats import measure, multiplicity_report  # noqa: E402

FIELDS = ["pair", "a", "b", "series_a", "series_b", "coverage", "n", "level_rho", "change_rho",
          "placebo_median", "placebo_percentile", "seasonal_rho", "lead_lag", "lead_lag_rho"]


def align(xs: dict[str, float], ys: dict[str, float]) -> tuple[list[float], list[float], list[str]]:
    months = sorted(set(xs) & set(ys))
    return [xs[m] for m in months], [ys[m] for m in months], months


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--draws", type=int, default=200)
    parser.add_argument("--expectations", default="results/capacity-expectations.csv")
    parser.add_argument("--events", default="results/rpo-events.csv")
    parser.add_argument("--out", default="results/scan-pairs.csv")
    parser.add_argument("--window", default="compute-era",
                        help="which declared study window this measurement belongs to")
    parser.add_argument("--open-sealed", action="store_true",
                        help="include this window's holdout. Only at the sealed test, once")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args(argv)
    window = get(args.window)

    nodes = load()
    declared = pairs(nodes)
    measurable = [p for p in declared if p["coverage"] == "measurable"]
    print(f"declared pairs: {len(declared)}   measurable by declaration: {len(measurable)}")

    series, missing = build([n["id"] for n in nodes], ROOT / args.expectations, ROOT / args.events)
    print(f"series built: {len(series)}")
    if missing:
        print(f"nodes with no series wired in this pass: {len(missing)}")
        for node_id, reason in sorted(missing.items()):
            print(f"   {node_id}: {reason}")

    by_node = {node["id"]: [label for label in build_labels(node["id"]) if label in series]
               for node in nodes}
    rows = []
    results = []
    for pair in measurable:
        for label_a in by_node.get(pair["a"], []):
            for label_b in by_node.get(pair["b"], []):
                xs, ys, months = align(clip(series[label_a], window, include_holdout=args.open_sealed),
                                       clip(series[label_b], window, include_holdout=args.open_sealed))
                if len(months) < 12:
                    rows.append({"pair": f"{label_a} ~ {label_b}", "a": pair["a"], "b": pair["b"],
                                 "series_a": label_a, "series_b": label_b, "coverage": "too few months",
                                 "n": len(months)})
                    continue
                result = measure(f"{label_a} ~ {label_b}", xs, ys, draws=args.draws)
                results.append(result)
                rows.append({"pair": result.pair, "a": pair["a"], "b": pair["b"],
                             "series_a": label_a, "series_b": label_b, "coverage": "measured",
                             "n": result.n, "level_rho": result.level_rho,
                             "change_rho": result.change_rho, "placebo_median": result.placebo_median,
                             "placebo_percentile": result.placebo_percentile,
                             "seasonal_rho": result.seasonal_rho, "lead_lag": result.lead_lag,
                             "lead_lag_rho": result.lead_lag_rho})

    if not args.summary:
        out = ROOT / args.out
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        print(f"wrote {args.out} ({len(rows)} rows)")

    print("")
    if args.open_sealed:
        print(f"SEALED WINDOW OPENED BY REQUEST: measuring {window.name} from {window.history_start} "
              f"through {window.sealed_end}. This is the one shot, and the result is reported as it is.")
    else:
        print(f"measured inside the {window.name} window: development {window.history_start} to "
              f"{window.development_end}, holdout {window.sealed_start} to {window.sealed_end} untouched")
    print(FIREWALL)
    print("")
    print(multiplicity_report(results))
    print("")
    print(correction_summary(rows, {node["id"]: node for node in nodes}))
    print("")
    print("series-level counts, since a node may contribute more than one representation:")
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["coverage"]] = counts.get(row["coverage"], 0) + 1
    for state, count in sorted(counts.items()):
        print(f"  {state:16s} {count}")
    return 0


def build_labels(node_id: str) -> list[str]:
    from scan.series import SERIES
    return SERIES.get(node_id, [])


if __name__ == "__main__":
    raise SystemExit(main())