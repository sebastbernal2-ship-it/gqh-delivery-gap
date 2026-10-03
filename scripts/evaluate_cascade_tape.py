#!/usr/bin/env python3
"""Apply the pre-registered cascade rule to a recorded tape, and report what it says.

The rule is not chosen here. It is the one committed in `docs/plan/cascade-protocol.md` before collection
started: a large move (3 trailing standard deviations) together with an open interest fall (1 percent), and
the structural tests are the two the protocol names.

The output is a description of the recorded window. It is not a backtest, and the summary says so.

Usage:
    python scripts/evaluate_cascade_tape.py
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from live.hyperliquid import count_overdispersion, refractory_excess, trigger  # noqa: E402

TAPE_DIR = ROOT / "data" / "tape"


def load(paths: list[Path]) -> dict[str, list[dict]]:
    by_market: dict[str, list[dict]] = defaultdict(list)
    for path in sorted(paths):
        with path.open() as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                by_market[row["coin"]].append(row)
    for rows in by_market.values():
        rows.sort(key=lambda r: (r.get("time") or 0, r.get("observed") or ""))
    return by_market


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tape", default=str(TAPE_DIR))
    args = parser.parse_args(argv)

    paths = sorted(Path(args.tape).glob("tape-*.jsonl"))
    if not paths:
        print("no tape recorded yet")
        return 1
    by_market = load(paths)
    minutes = 0.0
    for rows in by_market.values():
        if len(rows) > 1:
            minutes = max(minutes, (len(rows) - 1) * 15 / 60)

    print(f"tape files: {len(paths)}   markets: {len(by_market)}   about {minutes:.0f} minutes of samples")
    print(f"{'market':6s} {'samples':>8s} {'evaluable':>10s} {'triggers':>9s} {'spread bps':>11s} "
          f"{'depth 10bps':>12s}")
    summary: dict[str, dict] = {}
    for coin, rows in sorted(by_market.items()):
        mids = [row["mid"] for row in rows if row.get("mid")]
        interest = [row["open_interest"] for row in rows if row.get("open_interest") is not None]
        spreads = [row["spread_bps"] for row in rows if row.get("spread_bps") is not None]
        depths = [min(row.get("depth_bid_notional") or 0, row.get("depth_ask_notional") or 0)
                  for row in rows]
        hits, evaluable = [], 0
        for index in range(len(rows)):
            if index < 60:
                continue
            evaluable += 1
            if trigger(mids[:index + 1], interest[:index + 1]):
                hits.append(index)
        gaps = [hits[i + 1] - hits[i] for i in range(len(hits) - 1)]
        summary[coin] = {"samples": len(rows), "evaluable": evaluable, "hits": hits,
                         "spread": statistics.median(spreads) if spreads else None,
                         "depth": statistics.median(depths) if depths else None,
                         "gaps": gaps}
        print(f"{coin:6s} {len(rows):>8d} {evaluable:>10d} {len(hits):>9d} "
              f"{(statistics.median(spreads) if spreads else float('nan')):>11.2f} "
              f"{(statistics.median(depths) if depths else float('nan')):>12,.0f}")

    print("")
    print("the two structural tests the protocol declares:")
    for coin, stats in sorted(summary.items()):
        buckets = [0] * 4
        for hit in stats["hits"]:
            buckets[min(3, hit // 240)] += 1
        overdispersion = count_overdispersion(buckets)
        refractory = refractory_excess([float(g) for g in stats["gaps"]])
        print(f"  {coin}: clustering overdispersed={overdispersion['overdispersed']} "
              f"(mean {overdispersion['mean']:.2f}, variance {overdispersion['variance']:.2f}); "
              f"refractory={refractory}")

    total_triggers = sum(len(s["hits"]) for s in summary.values())
    print("")
    if total_triggers == 0:
        print("no trigger fired in this window. That is a description of the window, not a refutation of the")
        print("mechanism: with a sixty sample baseline and a few thousand samples, a rare event can simply not")
        print("appear. The protocol says every conclusion must name its sample length.")
    else:
        print(f"{total_triggers} triggers fired. Post trigger paths are reported in the protocol's four")
        print("windows, and every conclusion must still name its sample length.")
    print("")
    print("This is not a backtest, and nothing here is a strategy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
