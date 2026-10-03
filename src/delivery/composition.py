"""Composition check: is the delivery gap concentrated where the mechanism says it is?

Speculative technologies should cancel and slip much more than firm dispatchable ones.
If gas slips as much as solar, something is wrong with the matching, not with the market.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from .cohort import _key, select_window
from .parse import read_vintage
from .vintages import vintage_path


def composition(cohort: tuple[int, int], realization: tuple[int, int], data_dir: Path,
                horizon_months: int = 12) -> list[dict]:
    promised_all = read_vintage(vintage_path(data_dir, *cohort))["planned"]
    cohort_index = (cohort[0] - 2000) * 12 + (cohort[1] - 1)
    promised = select_window(promised_all, cohort_index, cohort_index + horizon_months)
    real = read_vintage(vintage_path(data_dir, *realization))
    operating = set(_key(real["operating"]))
    cancelled = set(_key(real["cancelled"]))

    buckets: dict[str, dict] = defaultdict(
        lambda: {"n": 0, "mw": 0.0, "arrived_mw": 0.0, "cancelled_mw": 0.0})
    for row in promised.to_dict("records"):
        tech = str(row.get("technology") or "Unknown")
        mw = float(row.get("mw") or 0.0)
        bucket = buckets[tech]
        bucket["n"] += 1
        bucket["mw"] += mw
        key = (str(row["plant_id"]), str(row["generator_id"]))
        if key in operating:
            bucket["arrived_mw"] += mw
        elif key in cancelled:
            bucket["cancelled_mw"] += mw

    rows = []
    for tech, bucket in sorted(buckets.items(), key=lambda kv: -kv[1]["mw"]):
        decided = bucket["arrived_mw"] + bucket["cancelled_mw"]
        rows.append({
            "technology": tech,
            "units": bucket["n"],
            "promised_mw": round(bucket["mw"], 1),
            "arrived_mw": round(bucket["arrived_mw"], 1),
            "cancelled_mw": round(bucket["cancelled_mw"], 1),
            "cancelled_share": round(bucket["cancelled_mw"] / decided, 4) if decided else 0.0,
        })
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Delivery gap by technology")
    parser.add_argument("--cohort", default="2025-01")
    parser.add_argument("--realization", default="2026-08")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--top", type=int, default=12)
    parser.add_argument("--horizon-months", type=int, default=12)
    args = parser.parse_args(argv)

    year, month = args.cohort.split("-")
    ry, rm = args.realization.split("-")
    rows = composition((int(year), int(month)), (int(ry), int(rm)), Path(args.data_dir),
                       args.horizon_months)

    print(f"cohort {args.cohort} -> realization {args.realization}")
    print(f"{'technology':36s}{'units':>7s}{'promised_mw':>13s}{'arrived_mw':>12s}"
          f"{'cancelled_mw':>14s}{'canc_share':>12s}")
    for row in rows[: args.top]:
        print(f"{row['technology'][:36]:36s}{row['units']:7d}{row['promised_mw']:13.0f}"
              f"{row['arrived_mw']:12.0f}{row['cancelled_mw']:14.0f}"
              f"{row['cancelled_share']:11.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
