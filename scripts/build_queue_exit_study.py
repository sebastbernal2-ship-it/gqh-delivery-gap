#!/usr/bin/env python3
"""Run the declared queue exit study, exactly as docs/plan/queue-exit-study.md states it.

Development only. Crowding is cumulative earlier request MW within the state, which is point-in-time
safe. Outcomes are permuted within state-year blocks for the null. The Spearman null is computed with
an exact within-block rank formula so 5,000 draws stay cheap. Writes results/queue-exit-study.json.

    python3 scripts/build_queue_exit_study.py
"""
from __future__ import annotations

import collections
import csv
import json
import math
import random
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PANEL = ROOT / "results" / "queue-panel.csv"
OUT = ROOT / "results" / "queue-exit-study.json"
DRAWS = 5000
SEED = 42
MIN_TECH = 200


def rank(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(order):
        end = index
        while end + 1 < len(order) and values[order[end + 1]] == values[order[index]]:
            end += 1
        average = (index + end) / 2 + 1
        for position in range(index, end + 1):
            ranks[order[position]] = average
        index = end + 1
    return ranks


def main() -> int:
    raw = list(csv.DictReader(PANEL.open()))
    by_state: dict[str, list[dict]] = collections.defaultdict(list)
    for row in raw:
        by_state[row["state"]].append(row)
    for state_rows in by_state.values():
        state_rows.sort(key=lambda row: (row["q_date"], row["q_id"]))
        running = 0.0
        for row in state_rows:
            row["_preceding"] = running
            try:
                running += max(0.0, float(row["mw1"] or 0))
            except ValueError:
                pass

    rows = []
    for row in raw:
        try:
            mw = max(0.0, float(row["mw1"] or 0))
        except ValueError:
            mw = 0.0
        rows.append({"state": row["state"], "year": row["q_date"][:4] if row["q_date"] else "",
                     "type": row["type_clean"], "preceding": float(row["_preceding"]), "mw": mw,
                     "withdrawn": 1 if row["q_status"] == "withdrawn" else 0})
    n = len(rows)
    base = sum(row["withdrawn"] for row in rows) / n
    crowding = [math.log1p(row["preceding"]) for row in rows]
    size = [math.log1p(row["mw"]) for row in rows]
    rx = rank(crowding)
    rx2_sum = sum(value * value for value in rx)
    mx = sum(rx) / n
    size_rx = rank(size)
    size_rx2 = sum(value * value for value in size_rx)
    size_mx = sum(size_rx) / n
    outcome_ranks = rank([row["withdrawn"] for row in rows])
    outcome_mean = sum(outcome_ranks) / n
    outcome_sq = sum(value * value for value in outcome_ranks)
    observed_rho = (sum(a * b for a, b in zip(rx, outcome_ranks)) - n * mx * outcome_mean) / math.sqrt(
        (rx2_sum - n * mx ** 2) * (outcome_sq - n * outcome_mean ** 2))
    size_rho = (sum(a * b for a, b in zip(size_rx, outcome_ranks)) - n * size_mx * outcome_mean) / math.sqrt(
        (size_rx2 - n * size_mx ** 2) * (outcome_sq - n * outcome_mean ** 2))

    blocks: dict[tuple[str, str], list[int]] = collections.defaultdict(list)
    for index, row in enumerate(rows):
        blocks[(row["state"], row["year"])].append(index)
    block_data = []
    for key, indexes in blocks.items():
        block_rx = [rx[index] for index in indexes]
        block_ys = [rows[index]["withdrawn"] for index in indexes]
        high = [1 if math.log1p(rows[index]["preceding"]) >
                statistics.median(math.log1p(rows[i]["preceding"]) for i in indexes) else 0
                for index in indexes]
        block_data.append((block_rx, block_ys, high))

    def rho_from_blocks(block_outcomes: list[list[int]]) -> float:
        s_xy = 0.0
        s_y = 0.0
        s_y2 = 0.0
        for (block_rx, _, _), shuffled in zip(block_data, block_outcomes):
            ones = sum(shuffled)
            zeros = len(shuffled) - ones
            z_position = 0
            o_position = 0
            for r_value, outcome in zip(block_rx, shuffled):
                if outcome == 0:
                    z_position += 1
                    rank_y = z_position
                else:
                    o_position += 1
                    rank_y = zeros + o_position
                s_xy += r_value * rank_y
                s_y += rank_y
                s_y2 += rank_y * rank_y
        my = s_y / n
        return (s_xy - n * mx * my) / math.sqrt((rx2_sum - n * mx ** 2) * (s_y2 - n * my ** 2))


    def gap_of(block_outcomes: list[list[int]]) -> float:
        total = 0.0
        weight = 0
        for (_, _, high), shuffled in zip(block_data, block_outcomes):
            ones = sum(high)
            zeros = len(high) - ones
            if not ones or not zeros:
                continue
            hi_w = sum(y for h, y in zip(high, shuffled) if h)
            lo_w = sum(y for h, y in zip(high, shuffled) if not h)
            total += (hi_w / ones - lo_w / zeros) * len(high)
            weight += len(high)
        return total / weight if weight else 0.0

    observed_gap = gap_of([ys for _, ys, _ in block_data])
    block_size_ranks = [[size_rx[index] for index in indexes] for indexes in
                        [blocks[key] for key in blocks]]

    def size_rho_from_blocks(block_outcomes: list[list[int]]) -> float:
        s_xy = 0.0
        s_y = 0.0
        s_y2 = 0.0
        for block_rx, shuffled in zip(block_size_ranks, block_outcomes):
            ones = sum(shuffled)
            zeros = len(shuffled) - ones
            z_position = 0
            o_position = 0
            for r_value, outcome in zip(block_rx, shuffled):
                if outcome == 0:
                    z_position += 1
                    rank_y = z_position
                else:
                    o_position += 1
                    rank_y = zeros + o_position
                s_xy += r_value * rank_y
                s_y += rank_y
                s_y2 += rank_y * rank_y
        my = s_y / n
        return (s_xy - n * size_mx * my) / math.sqrt((size_rx2 - n * size_mx ** 2) * (s_y2 - n * my ** 2))

    tech_index = collections.defaultdict(list)
    for index, row in enumerate(rows):
        tech_index[row["type"]].append(index)
    tech_index = {tech: indexes for tech, indexes in tech_index.items() if len(indexes) >= MIN_TECH}

    def tech_spread_of(flat_outcomes: list[int]) -> float:
        shares = {tech: sum(flat_outcomes[index] for index in indexes) / len(indexes)
                  for tech, indexes in tech_index.items()}
        return max(shares.values()) - min(shares.values())

    observed_tech_spread = tech_spread_of([row["withdrawn"] for row in rows])

    random.seed(SEED)
    null_rho = []
    null_gap = []
    null_size_rho = []
    null_tech = []
    random.seed(SEED)
    for _ in range(DRAWS):
        shuffled_blocks = []
        flat = [0] * n
        for block_rx, ys, _ in block_data:
            shuffled = list(ys)
            random.shuffle(shuffled)
            shuffled_blocks.append(shuffled)
        # Rebuild the flat vector from blocks in original index order.
        flat = [None] * n
        for (state_year, indexes), shuffled in zip(blocks.items(), shuffled_blocks):
            for position, index in enumerate(indexes):
                flat[index] = shuffled[position]
        null_rho.append(rho_from_blocks(shuffled_blocks))
        null_gap.append(gap_of(shuffled_blocks))
        null_size_rho.append(size_rho_from_blocks(shuffled_blocks))
        null_tech.append(tech_spread_of(flat))
    rho_p = (1 + sum(1 for value in null_rho if value >= observed_rho)) / (1 + len(null_rho))
    gap_p = (1 + sum(1 for value in null_gap if value >= observed_gap)) / (1 + len(null_gap))
    size_p = (1 + sum(1 for value in null_size_rho if value >= size_rho)) / (1 + len(null_size_rho))
    tech_p = (1 + sum(1 for value in null_tech if value >= observed_tech_spread)) / (1 + len(null_tech))

    tech_stats = collections.defaultdict(lambda: {"n": 0, "withdrawn": 0})
    for row in rows:
        tech_stats[row["type"]]["n"] += 1
        tech_stats[row["type"]]["withdrawn"] += row["withdrawn"]
    big_tech = {tech: stats for tech, stats in tech_stats.items() if stats["n"] >= MIN_TECH}
    shares = {tech: stats["withdrawn"] / stats["n"] for tech, stats in big_tech.items()}
    top_tech = max(shares, key=shares.get)
    bottom_tech = min(shares, key=shares.get)

    report = {
        "status": "development only; both sealed windows spent; protocol docs/plan/queue-exit-study.md",
        "population": n,
        "base_withdrawal_share": round(base, 4),
        "primary_crowding": {"observed_rho": round(observed_rho, 4), "permutation_p": round(rho_p, 4),
                             "null_mean": round(statistics.mean(null_rho), 4),
                             "null_p95": round(sorted(null_rho)[int(0.95 * len(null_rho))], 4),
                             "high_low_gap": round(observed_gap, 4), "gap_permutation_p": round(gap_p, 4)},
        "secondary_size": {"observed_rho": round(size_rho, 4), "permutation_p": round(size_p, 4)},
        "secondary_technology": {"technologies": len(big_tech), "top": top_tech,
                                 "top_share": round(shares[top_tech], 4), "bottom": bottom_tech,
                                 "bottom_share": round(shares[bottom_tech], 4),
                                 "spread": round(shares[top_tech] - shares[bottom_tech], 4),
                                 "permutation_p": round(tech_p, 4),
                                 "table": {tech: {"n": stats["n"], "share": round(shares[tech], 4)}
                                           for tech, stats in sorted(big_tech.items(),
                                                                     key=lambda item: -shares[item[0]])}},
        "test_count": 3,
        "caveats": ["development only, both sealed windows open and spent",
                    "crowding uses request MW only, outcomes never enter the feature",
                    "the queue panel has no position to hold; this orders a state variable only"],
    }
    OUT.write_text(json.dumps(report, indent=1) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"population {n:,}; base withdrawal {base:.1%}")
    print(f"crowding rho {observed_rho:+.4f} (p {rho_p:.4f}); high-low gap {observed_gap:+.4f} (p {gap_p:.4f})")
    print(f"size rho {size_rho:+.4f} (p {size_p:.4f}); technology spread "
          f"{shares[top_tech] - shares[bottom_tech]:.3f} (p {tech_p:.4f}) "
          f"({top_tech} {shares[top_tech]:.1%} vs {bottom_tech} {shares[bottom_tech]:.1%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
