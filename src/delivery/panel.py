"""The delivery-gap state variable.

For each cohort, match every promised unit to what a later vintage says actually
happened, then measure the transport cost between promised and realized delivery
dates, for the country and for each balancing authority.

Only units promised inside the cohort's observable window are measured. A unit promised
years out has no measurable delay yet, and mixing it in would understate the delay.

This is the input to the strategy, not a trading result.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .cohort import match_cohort, select_window
from .metrics import transport_cost
from .parse import read_vintage
from .vintages import fetch_vintages, vintage_path

# The most recent measurable cohort is 12 months before the realization vintage.
# With August 2026 as the latest live vintage, that is 2025-08.
DEFAULT_COHORTS = [(2024, 1), (2024, 7), (2025, 1), (2025, 7)]
# September 2026 is not downloadable from EIA (the file returns 503). August is live.
DEFAULT_REALIZATION = (2026, 8)
DEFAULT_HORIZON_MONTHS = 12


def git_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
        return out.stdout.strip() or "0" * 40
    except Exception:
        return "0" * 40


def cohort_metrics(cohort: tuple[int, int], realization: tuple[int, int], data_dir: Path,
                   horizon_months: int = DEFAULT_HORIZON_MONTHS) -> dict:
    months_between = (realization[0] * 12 + realization[1]) - (cohort[0] * 12 + cohort[1])
    if months_between < horizon_months:
        raise ValueError(
            f"realization {realization[0]}-{realization[1]:02d} is only {months_between} months "
            f"after cohort {cohort[0]}-{cohort[1]:02d}; a {horizon_months} month horizon "
            f"cannot be observed yet")

    realized = read_vintage(vintage_path(data_dir, *realization))
    promised_all = read_vintage(vintage_path(data_dir, *cohort))["planned"]

    cohort_index = (cohort[0] - 2000) * 12 + (cohort[1] - 1)
    promised = select_window(promised_all, cohort_index, cohort_index + horizon_months,
                             report=True)
    excluded = int(promised.attrs.get("excluded", 0))

    matched = match_cohort(promised, realized["operating"], realized["cancelled"],
                           realized["planned"])

    overall = transport_cost(matched["pairs"], canceled_mw=matched["cancelled_mw"])
    per_region = {}
    for region, bucket in sorted(matched["by_region"].items()):
        region_pairs = [p for p in matched["pairs"] if p["ba_code"] == region]
        metrics = transport_cost(region_pairs, canceled_mw=bucket["cancelled_mw"])
        metrics["mw_promised"] = round(bucket["mw_promised"], 1)
        per_region[region] = metrics

    return {
        "cohort": f"{cohort[0]}-{cohort[1]:02d}",
        "realization_vintage": f"{realization[0]}-{realization[1]:02d}",
        "months_between": months_between,
        "horizon_months": horizon_months,
        "n_promised_in_window": int(len(promised)),
        "n_excluded_far_future": excluded,
        "n_arrived": matched["n_arrived"],
        "n_censored": matched["n_censored"],
        "n_unexplained": matched["n_unexplained"],
        "overall": overall,
        "by_region": per_region,
    }


def realization_for(cohort: tuple[int, int], horizon_months: int, lag_months: int,
                    latest: tuple[int, int] = DEFAULT_REALIZATION) -> tuple[int, int] | None:
    """Earliest measurable vintage at least horizon + lag months after the cohort.

    A fixed lag makes cohorts comparable: every cohort is observed for the same amount of
    time after its window closes, so a shorter measured delay is a fact, not censoring.
    """
    index = (cohort[0] - 2000) * 12 + (cohort[1] - 1) + horizon_months + lag_months
    if index > (latest[0] - 2000) * 12 + (latest[1] - 1):
        return None
    return (2000 + index // 12, index % 12 + 1)


def build_panel(cohorts, realization, data_dir: Path, manifest_path: Path,
                results_path: Path, fetch: bool = True,
                horizon_months: int = DEFAULT_HORIZON_MONTHS,
                lag_months: int | None = None) -> dict:
    data_dir, manifest_path, results_path = Path(data_dir), Path(manifest_path), Path(results_path)

    # With a lag, each cohort gets its own realization vintage so the observations are
    # comparable. Without one, every cohort is measured against the single latest vintage.
    plan: list[tuple[tuple[int, int], tuple[int, int]]] = []
    if lag_months is None:
        plan = [(c, realization) for c in cohorts]
    else:
        for cohort in cohorts:
            chosen = realization_for(cohort, horizon_months, lag_months, realization)
            if chosen is not None:
                plan.append((cohort, chosen))

    if fetch:
        targets = sorted(set(list(cohorts) + [real for _, real in plan] + [realization]))
        fetch_vintages(targets, data_dir, manifest_path)

    per_cohort = [cohort_metrics(c, real, data_dir, horizon_months) for c, real in plan]

    payload = {
        "kind": "state",
        "engine": "e0",
        "measure": "MW weighted transport cost between promised and realized energization dates",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": git_commit(),
        "coverage": {
            "cohorts": [f"{y}-{m:02d}" for y, m in cohorts],
            "realization_vintage": f"{realization[0]}-{realization[1]:02d}",
            "latest_available_vintage": f"{realization[0]}-{realization[1]:02d}",
            "lag_months": lag_months,
            "horizon_months": horizon_months,
            "manifest": str(manifest_path),
        },
        "observations": per_cohort,
        "notes": ("Promised dates come from the cohort vintage Planned sheet. Realized dates "
                  "come from the realization vintage Operating sheet. A unit still in Planned "
                  "has not been energized yet. Cancellations are reported as their own mass and "
                  "never folded into the delay. Vintages are frozen and never revised."),
    }
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(json.dumps(payload, indent=2) + "\n")
    return payload


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Build the delivery-gap state variable")
    parser.add_argument("--cohorts",
                        default=",".join(f"{y}-{m:02d}" for y, m in DEFAULT_COHORTS))
    parser.add_argument("--realization",
                        default=f"{DEFAULT_REALIZATION[0]}-{DEFAULT_REALIZATION[1]:02d}")
    parser.add_argument("--horizon-months", type=int, default=DEFAULT_HORIZON_MONTHS)
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--manifest", default="data/manifest.json")
    parser.add_argument("--out", default="results/e0_state.json")
    parser.add_argument("--lag-months", type=int, default=None,
                        help="observation lag after the window closes; per cohort realization")
    parser.add_argument("--no-fetch", action="store_true")
    args = parser.parse_args(argv)

    cohorts = []
    for token in args.cohorts.split(","):
        year, month = token.strip().split("-")
        cohorts.append((int(year), int(month)))
    year, month = args.realization.split("-")

    payload = build_panel(cohorts, (int(year), int(month)), Path(args.data_dir),
                          Path(args.manifest), Path(args.out), fetch=not args.no_fetch,
                          horizon_months=args.horizon_months, lag_months=args.lag_months)

    print(f"state variable written to {args.out}")
    for obs in payload["observations"]:
        overall = obs["overall"]
        print(f"  cohort {obs['cohort']}: {obs['n_promised_in_window']} promised in window "
              f"({obs['n_excluded_far_future']} beyond horizon), {obs['n_arrived']} arrived, "
              f"W1 {overall['w1_months']:.2f} mo, median {overall['median_delay_months']:.1f} mo, "
              f"p90 {overall['p90_delay_months']:.1f} mo, "
              f"cancelled {overall['cancelled_share']:.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
