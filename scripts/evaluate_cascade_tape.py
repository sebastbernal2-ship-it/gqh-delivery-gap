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

from live.hyperliquid import count_overdispersion, now_iso, refractory_excess, trigger  # noqa: E402

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


def post_trigger_paths(rows: list[dict], hits: list[int], horizons: tuple[int, ...] = (1, 5, 15, 60)) -> list[dict]:
    """Return complete post-trigger paths with raw, costed, reversal, and capacity fields."""
    paths = []
    for hit in hits:
        if hit <= 0 or hit >= len(rows):
            continue
        event_mid = float(rows[hit]["mid"])
        prior_mid = float(rows[hit - 1]["mid"])
        event_move = event_mid / prior_mid - 1.0 if prior_mid else 0.0
        if event_move == 0.0:
            continue
        capacity = min(float(rows[hit].get("depth_bid_notional") or 0),
                       float(rows[hit].get("depth_ask_notional") or 0))
        for horizon in horizons:
            endpoint = hit + horizon
            if endpoint >= len(rows):
                continue
            raw_return = float(rows[endpoint]["mid"]) / event_mid - 1.0
            continuation_return = raw_return if event_move > 0 else -raw_return
            paths.append({
                "hit": hit,
                "horizon": horizon,
                "raw_return": raw_return,
                "continuation_return": continuation_return,
                "reversal_return": -continuation_return,
                "net_return_9bps": raw_return - 0.0009,
                "net_return_18bps": raw_return - 0.0018,
                "capacity_notional": capacity,
            })
    return paths


def unconditional_paths(rows: list[dict], horizon: int, exclude_hits: set[int] | None = None) -> list[dict]:
    """Return same-horizon unconditional returns for the declared comparison."""
    excluded = exclude_hits or set()
    paths = []
    for index in range(len(rows) - horizon):
        if index in excluded:
            continue
        start = float(rows[index]["mid"])
        end = float(rows[index + horizon]["mid"])
        if start:
            paths.append({"start": index, "horizon": horizon, "raw_return": end / start - 1.0})
    return paths


def summarize_paths(paths: list[dict], baseline: list[dict], cost_bps: float = 9.0) -> dict | None:
    """Summarize a trigger path against its unconditional same-horizon baseline."""
    if not paths:
        return None
    cost = cost_bps / 10_000
    raw = [float(path["raw_return"]) for path in paths]
    capacities = [float(path["capacity_notional"]) for path in paths]
    base = [float(path["raw_return"]) for path in baseline]
    ordered = sorted(capacities)
    middle = len(ordered) // 2
    median_capacity = ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2
    return {
        "count": len(paths),
        "mean_raw_return": sum(raw) / len(raw),
        "mean_net_return": sum(value - cost for value in raw) / len(raw),
        "mean_double_cost_return": sum(value - 2 * cost for value in raw) / len(raw),
        "mean_reversal_return": sum(float(path["reversal_return"]) for path in paths) / len(paths),
        "positive_fraction": sum(value > 0 for value in raw) / len(raw),
        "baseline_count": len(base),
        "baseline_mean_return": sum(base) / len(base) if base else None,
        "median_capacity_notional": median_capacity,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tape", default=str(TAPE_DIR))
    parser.add_argument("--json", default=None, help="write the machine-readable summary here")
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
        times = [row["time"] for row in rows if row.get("time") is not None]
        hits, evaluable = [], 0
        for index in range(len(rows)):
            if index < 60:
                continue
            evaluable += 1
            if trigger(mids[:index + 1], interest[:index + 1]):
                hits.append(index)
        gaps = [hits[i + 1] - hits[i] for i in range(len(hits) - 1)]
        trigger_paths = post_trigger_paths(rows, hits)
        path_stats = {}
        for horizon in (1, 5, 15, 60):
            selected = [path for path in trigger_paths if path["horizon"] == horizon]
            baseline = unconditional_paths(rows, horizon, exclude_hits=set(hits))
            path_stats[horizon] = summarize_paths(selected, baseline)
        summary[coin] = {"samples": len(rows), "evaluable": evaluable, "hits": hits,
                         "first": min(times) if times else None,
                         "last": max(times) if times else None,
                         "spread": statistics.median(spreads) if spreads else None,
                         "depth": statistics.median(depths) if depths else None,
                         "gaps": gaps, "path_stats": path_stats}
        print(f"{coin:6s} {len(rows):>8d} {evaluable:>10d} {len(hits):>9d} "
              f"{(statistics.median(spreads) if spreads else float('nan')):>11.2f} "
              f"{(statistics.median(depths) if depths else float('nan')):>12,.0f}")

    print("")
    print("post-trigger paths, raw and net of 9/18 bps round-trip costs:")
    for coin, stats in sorted(summary.items()):
        for horizon, path_summary in stats["path_stats"].items():
            if path_summary is None:
                continue
            print(f"  {coin} +{horizon:>2} samples: n={path_summary['count']} "
                  f"raw={path_summary['mean_raw_return']:.5f} "
                  f"net9={path_summary['mean_net_return']:.5f} "
                  f"net18={path_summary['mean_double_cost_return']:.5f} "
                  f"reversal={path_summary['mean_reversal_return']:.5f} "
                  f"unconditional={path_summary['baseline_mean_return']:.5f} "
                  f"capacity={path_summary['median_capacity_notional']:,.0f}")
    if total_triggers := sum(len(s["hits"]) for s in summary.values()):
        complete_paths = sum(
            path_summary["count"]
            for stats in summary.values()
            for path_summary in stats["path_stats"].values()
            if path_summary is not None
        )
        print(f"  complete trigger paths: {complete_paths}")
    else:
        print("  no complete trigger paths")

    print("")
    print("the two structural tests the protocol declares:")
    for coin, stats in sorted(summary.items()):
        buckets = [0] * 4
        for hit in stats["hits"]:
            buckets[min(3, hit // 240)] += 1
        overdispersion = count_overdispersion(buckets)
        refractory = refractory_excess([float(g) for g in stats["gaps"]])
        stats["overdispersion"] = overdispersion
        stats["refractory"] = refractory
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
    if args.json:
        report = {
            "generated": now_iso(),
            "tape_files": len(paths),
            "nominal_minutes": minutes,
            "total_triggers": total_triggers,
            "markets": {
                coin: {
                    "samples": stats["samples"],
                    "evaluable": stats["evaluable"],
                    "triggers": len(stats["hits"]),
                    "first": stats["first"],
                    "last": stats["last"],
                    "spread_bps_median": stats["spread"],
                    "depth_10bps_median": stats["depth"],
                    "paths": stats["path_stats"],
                    "clustering": stats.get("overdispersion"),
                    "refractory": stats.get("refractory"),
                }
                for coin, stats in sorted(summary.items())
            },
        }
        Path(args.json).write_text(json.dumps(report, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
