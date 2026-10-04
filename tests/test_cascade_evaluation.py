"""Offline checks for post-trigger paths and cost stress."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_cascade_tape import (  # noqa: E402
    unconditional_paths,
    post_trigger_paths,
    summarize_paths,
)


ROWS = [
    {"time": i, "mid": str(value), "depth_bid_notional": "1000", "depth_ask_notional": "800"}
    for i, value in enumerate([100, 110, 111, 112, 113, 114, 115, 116])
]

paths = post_trigger_paths(ROWS, [1], horizons=(1, 3, 10))
assert [row["horizon"] for row in paths] == [1, 3]
assert round(paths[0]["raw_return"], 6) == round(111 / 110 - 1, 6)
assert round(paths[0]["net_return_9bps"], 6) == round(111 / 110 - 1 - 0.0009, 6)
assert paths[0]["capacity_notional"] == 800.0
assert paths[0]["reversal_return"] == -paths[0]["continuation_return"]

baseline = unconditional_paths(ROWS, horizon=1, exclude_hits={1})
summary = summarize_paths(paths[:1], baseline, cost_bps=9.0)
assert summary["count"] == 1
assert summary["mean_net_return"] == paths[0]["net_return_9bps"]
assert summary["mean_double_cost_return"] == paths[0]["raw_return"] - 0.0018
assert summary["baseline_count"] == len(baseline)
assert summary["median_capacity_notional"] == 800.0
assert summarize_paths([], baseline) is None

print("cascade evaluation: 10/10 passed")
