"""Regenerate every number the note quotes. `make all` calls this.

Stage 1: the delivery-gap state variable (results/e0_state.json).
Later stages add the event-vol engine, the coupling engine and the execution engine.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from delivery.panel import build_panel, DEFAULT_COHORTS, DEFAULT_REALIZATION  # noqa: E402

LAG_MONTHS = 6


def main() -> int:
    payload = build_panel(DEFAULT_COHORTS, DEFAULT_REALIZATION, Path("data"),
                          Path("data/manifest.json"), Path("results/e0_state.json"),
                          fetch=True, lag_months=LAG_MONTHS)
    print(f"e0 state variable: {len(payload['observations'])} comparable cohorts")
    for obs in payload["observations"]:
        overall = obs["overall"]
        print(f"  {obs['cohort']} -> {obs['realization_vintage']}: "
              f"{obs['n_promised_in_window']} promised, {obs['n_arrived']} arrived, "
              f"W1 {overall['w1_months']:.2f} mo, median {overall['median_delay_months']:.1f} mo, "
              f"cancelled {overall['cancelled_share']:.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
