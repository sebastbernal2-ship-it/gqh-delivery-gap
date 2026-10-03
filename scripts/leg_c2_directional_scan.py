#!/usr/bin/env python3
"""Directional lead-lag scan on canonical node series, using development data only."""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scan import report, stats  # noqa: E402
from scan.fdr import benjamini_hochberg  # noqa: E402
from scan.series import SERIES, build  # noqa: E402
from scan.windows import clip, get  # noqa: E402

FIELDS = ["from_node", "to_node", "months", "best_lag", "correlation",
          "null_95th_percentile", "q_value", "family_split", "verdict"]
MIN_MONTHS = 12
MAX_LAG = 3
FDR_RATE = 0.10


def canonical_series(nodes: list[dict], available: dict[str, dict[str, float]]) -> dict[str, tuple[str, dict[str, float]]]:
    """Choose one available representation per node, honoring report.py's canonical map."""
    chosen: dict[str, tuple[str, dict[str, float]]] = {}
    for node in nodes:
        node_id = node["id"]
        labels = SERIES.get(node_id, [])
        forced = report.CANONICAL.get(node_id)
        if forced:
            labels = [forced]
        labels = [label for label in labels if label in available]
        if labels:
            label = labels[0]
            chosen[node_id] = (label, available[label])
    return chosen


def lag_correlations(xs: list[float], ys: list[float]) -> list[float]:
    """Changes in the mover lead changes in the follower by zero through three months."""
    dx, dy = stats.changes(xs), stats.changes(ys)
    out = []
    for lag in range(MAX_LAG + 1):
        left, right = (dx, dy) if lag == 0 else (dx[:-lag], dy[lag:])
        out.append(stats.spearman(left, right) if len(left) >= 3 else float("nan"))
    return out


def null_distribution(xs: list[float], ys: list[float], draws: int, seed: int) -> list[float]:
    """Use stats.py's block permutation and calibrate the selected lag's absolute correlation."""
    rng = random.Random(seed)
    values = []
    for _ in range(draws):
        shuffled = stats.block_shuffle(ys, block=3, rng=rng)
        candidates = [abs(value) for value in lag_correlations(xs, shuffled) if math.isfinite(value)]
        if candidates:
            values.append(max(candidates))
    return sorted(values)


def empirical_p(null: list[float], observed: float) -> float:
    if not null or not math.isfinite(observed):
        return 1.0
    at_least = sum(value >= abs(observed) for value in null)
    return (at_least + 1) / (len(null) + 1)


def q_values(pairs: list[tuple[str, float]]) -> dict[str, float]:
    """Benjamini-Hochberg adjusted p-values, including monotonicity from the tail."""
    ordered = sorted(pairs, key=lambda item: item[1])
    total = len(ordered)
    adjusted = [1.0] * total
    running = 1.0
    for index in range(total - 1, -1, -1):
        rank = index + 1
        running = min(running, ordered[index][1] * total / rank)
        adjusted[index] = min(1.0, running)
    return {name: value for (name, _), value in zip(ordered, adjusted)}


def stable_seed(label: str, base: int) -> int:
    digest = hashlib.sha256(label.encode()).digest()
    return base + int.from_bytes(digest[:4], "big")


def scan(nodes: list[dict], series: dict[str, tuple[str, dict[str, float]]],
         window, draws: int, seed: int) -> tuple[list[dict], dict]:
    families = {node["id"]: node["family"] for node in nodes}
    clipped = {node_id: clip(values, window) for node_id, (_, values) in series.items()}
    raw: list[dict] = []
    p_by_pair: list[tuple[str, float]] = []
    for from_node, to_node in itertools.permutations(sorted(clipped), 2):
        months = sorted(set(clipped[from_node]) & set(clipped[to_node]))
        if len(months) < MIN_MONTHS:
            continue
        xs = [clipped[from_node][month] for month in months]
        ys = [clipped[to_node][month] for month in months]
        correlations = lag_correlations(xs, ys)
        valid = [(lag, value) for lag, value in enumerate(correlations) if math.isfinite(value)]
        if not valid:
            continue
        best_lag, correlation = max(valid, key=lambda item: abs(item[1]))
        label = f"{from_node}->{to_node}"
        null = null_distribution(xs, ys, draws, stable_seed(label, seed))
        null95 = null[math.ceil(0.95 * len(null)) - 1] if null else float("nan")
        p_value = empirical_p(null, correlation)
        row = {"from_node": from_node, "to_node": to_node, "months": len(months),
               "best_lag": best_lag, "correlation": correlation,
               "null_95th_percentile": null95, "q_value": None,
               "family_split": "within" if families[from_node] == families[to_node] else "across",
               "verdict": "pending"}
        raw.append(row)
        p_by_pair.append((label, p_value))

    q_map = q_values(p_by_pair)
    bh = benjamini_hochberg(p_by_pair, rate=FDR_RATE)
    survivors = set(bh["survivors"])
    for row in raw:
        label = f"{row['from_node']}->{row['to_node']}"
        row["q_value"] = q_map[label]
        row["verdict"] = "survives" if label in survivors else "does_not_survive"
    return raw, bh


def fmt(value: float) -> str:
    return "" if not math.isfinite(float(value)) else f"{float(value):.8g}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--draws", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20261003)
    parser.add_argument("--window", default="mechanism-and-strategy")
    parser.add_argument("--expectations", default="results/capacity-expectations.csv")
    parser.add_argument("--events", default="results/rpo-events.csv")
    parser.add_argument("--out", default="results/leg-c2-association-edges.csv")
    args = parser.parse_args(argv)
    if args.draws < 1:
        parser.error("--draws must be positive")

    nodes = [json.loads(line) for line in (ROOT / "docs/scan/nodes.jsonl").read_text().splitlines() if line.strip()]
    built, missing = build([node["id"] for node in nodes], ROOT / args.expectations, ROOT / args.events)
    selected = canonical_series(nodes, built)
    window = get(args.window)
    rows, bh = scan(nodes, selected, window, args.draws, args.seed)

    output = ROOT / args.out
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "correlation": fmt(row["correlation"]),
                             "null_95th_percentile": fmt(row["null_95th_percentile"]),
                             "q_value": fmt(row["q_value"])})

    survivors = [row for row in rows if row["verdict"] == "survives"]
    cross = [row for row in survivors if row["family_split"] == "across"]
    print(f"window: {window.name}, development only: {window.history_start} to {window.development_end}")
    print(f"canonical usable node series: {len(selected)}; ordered pairs tested: {len(rows)}")
    print(f"survivors at BH FDR {FDR_RATE:.0%}: {len(survivors)}; expected false among survivors: {bh['expected_false']:.2f}")
    print(f"nominal 5% null expectation across tested pairs: {len(rows) * 0.05:.2f}")
    print(f"cross-family survivors: {len(cross)}; within-family survivors: {len(survivors) - len(cross)}")
    print(f"series missing or unavailable: {len(missing)}")
    print(f"wrote {args.out} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
