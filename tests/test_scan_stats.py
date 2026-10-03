#!/usr/bin/env python3
"""Offline tests for the scan statistics and its null. No network, no market data."""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from scan.stats import (  # noqa: E402
    block_shuffle, changes, lead_lag, measure, multiplicity_report, pearson, ranks,
    seasonal_shift, spearman,
)

failures: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        failures.append(f"{name}: got {got!r}, want {want!r}")


def close(name: str, got, want, tol=0.02) -> None:
    if not (abs(got - want) <= tol):
        failures.append(f"{name}: got {got!r}, want about {want!r}")


check("ranks handle a tie by averaging", ranks([10, 20, 20, 30]), [1.0, 2.5, 2.5, 4.0])
check("changes are period to period", changes([1, 3, 6]), [2, 3])
check("a perfect positive relation is 1", round(spearman([1, 2, 3, 4, 5], [2, 4, 6, 8, 10]), 6), 1.0)
check("a perfect negative relation is -1", round(spearman([1, 2, 3, 4, 5], [5, 4, 3, 2, 1]), 6), -1.0)
check("a constant series has no correlation",
      math.isnan(spearman([1, 1, 1, 1], [1, 2, 3, 4])), True)
check("too few points gives no correlation", math.isnan(pearson([1, 2], [1, 2])), True)

# Ranks make the statistic robust to a single wild value, which a level regression would not be.
check("a rank correlation ignores the size of an outlier",
      round(spearman([1, 2, 3, 4, 5], [1, 2, 3, 4, 5000]), 6), 1.0)

values = list(range(40))
shuffled = block_shuffle(values, block=3, rng=random.Random(7))
check("a block shuffle keeps every value", sorted(shuffled), sorted(values))
check("a block shuffle moves values", shuffled != values, True)
# Blocks are permuted, not broken: every original full block must survive as a contiguous run.
original_blocks = [values[i:i + 3] for i in range(0, len(values) - 3, 3)]
def appears_intact(block: list[int], sequence: list[int]) -> bool:
    return any(sequence[i:i + len(block)] == block for i in range(len(sequence) - len(block) + 1))
check("every original block survives the shuffle intact",
      all(appears_intact(block, shuffled) for block in original_blocks), True)
check("a seasonal shift keeps the length", len(seasonal_shift(values, 12)), len(values))
check("a seasonal shift moves the series by a year", seasonal_shift([1, 2, 3, 4, 5], 2), [3, 4, 5, 1, 2])
check("a seasonal shift on a short series changes nothing", seasonal_shift([1, 2], 12), [1, 2])

# A shared trend in levels is not a relation in changes. Two series that both climb, with unrelated
# step patterns, correlate near one in levels and not at all in changes: the trap the statistic avoids.
trend = [float(i) for i in range(40)]
steps = [0.0]
for i in range(1, 40):
    steps.append(steps[-1] + (3.0 if (i // 4) % 2 == 0 else 0.2))
result = measure("trend vs steps", trend, steps, draws=40)
check("levels look strongly related", result.level_rho > 0.9, True)
check("changes show almost none of it",
      not (result.change_rho == result.change_rho) or abs(result.change_rho) < result.level_rho - 0.3, True)

# A genuinely aligned pair, and a genuinely unrelated pair, against the same null machinery.
rng = random.Random(11)
base = [math.sin(i / 3.0) + rng.gauss(0, 0.05) for i in range(60)]
aligned = [value + rng.gauss(0, 0.05) for value in base]
unrelated = [rng.gauss(0, 1) for _ in range(60)]
good = measure("aligned", base, aligned, draws=60)
bad = measure("unrelated", base, unrelated, draws=60)
check("an aligned pair beats its own null", good.placebo_percentile > 0.9, True)
check("an unrelated pair does not beat its own null", bad.placebo_percentile < 0.9, True)
check("an unrelated pair shows little change relation", abs(bad.change_rho) < 0.5, True)

# A lag needs a non-degenerate series: a straight line has one change value and no rank correlation.
lag, lag_rho = lead_lag(base, aligned, max_lag=3)
check("a lag is reported", isinstance(lag, int), True)
check("a lag correlation is reported", lag_rho == lag_rho, True)

report = multiplicity_report([good, bad])
check("the report states how many were measured", "pairs measured: 2" in report, True)
check("the report states the expected count by chance", "expected by chance" in report, True)
check("the report refuses to call a survivor a strategy",
      "never a strategy" in report, True)

empty = multiplicity_report([bad])
check("a scan with no survivor says so", "no pair beat its own null" in empty, True)

if failures:
    print("\n".join(f"  FAIL {f}" for f in failures))
    print(f"\n{24 - len(failures)}/24 passed")
    raise SystemExit(1)
print("\n24/24 passed")
