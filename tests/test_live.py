#!/usr/bin/env python3
"""Offline tests for the tape parser and the pre-registered trigger. No network."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from live.hyperliquid import (  # noqa: E402
    MARKETS, count_overdispersion, refractory_excess, returns, trigger,
)

failures: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        failures.append(f"{name}: got {got!r}, want {want!r}")


check("the markets are declared before collection", MARKETS, ("BTC", "ETH", "GAS", "SPX"))
check("returns are proportional changes", [round(r, 4) for r in returns([100, 110, 121])], [0.1, 0.1])

# A quiet series must not trigger, whatever the open interest does.
quiet = [100.0 + 0.01 * (i % 3) for i in range(80)]
flat_oi = [1000.0] * 80
check("a quiet series does not trigger", trigger(quiet, flat_oi), False)

# A large move with a stable open interest is an announcement, not a cascade.
spike = list(quiet)
spike[-1] = spike[-2] * 1.10
check("a large move without an open interest fall does not trigger", trigger(spike, flat_oi), False)

# A quiet unwind is not a cascade either.
dropping = [1000.0 - i for i in range(80)]
check("an open interest fall without a large move does not trigger", trigger(quiet, dropping), False)

# The conjunction triggers.
check("a large move with an open interest fall triggers", trigger(spike, [1000.0] * 79 + [900.0]), True)

# Not enough history is never a trigger: the rule needs its own baseline.
check("a short series cannot trigger", trigger([100.0, 110.0], [1000.0, 900.0]), False)
check("a flat series cannot trigger on a zero denominator", trigger([100.0] * 80, [1000.0] * 80), False)

clustered = count_overdispersion([0, 0, 5, 0, 0, 6, 0, 1, 0, 0])
poissonish = count_overdispersion([1, 1, 1, 1, 1, 1, 1, 1])
check("clustered counts are called overdispersed", clustered["overdispersed"], True)
check("even counts are not called overdispersed", poissonish["overdispersed"], False)
check("too few buckets gives no verdict", count_overdispersion([1])["overdispersed"], None)

# Intervals equal to the mean are not short: short means half the mean or less.
gaps = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
check("regular intervals are not short", refractory_excess(gaps)["observed_short"], 0)
bursty = [0.2, 0.2, 0.2, 2.0, 2.0, 2.0]
check("a burst of short intervals is counted as short", refractory_excess(bursty)["observed_short"], 3)
check("too few gaps gives nothing", refractory_excess([1.0]), None)

if failures:
    print("\n".join(f"  FAIL {f}" for f in failures))
    print(f"\n{18 - len(failures)}/18 passed")
    raise SystemExit(1)
print("\n18/18 passed")
