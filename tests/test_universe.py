#!/usr/bin/env python3
"""Offline tests for the universe rule and the group statistics. No network."""
from __future__ import annotations

import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_rpo_universe import GROUPS, MIN_FACTS, SIC_GROUP, quarters  # noqa: E402
from run_group_event_study import BENCHMARK, tstat  # noqa: E402

failures: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        failures.append(f"{name}: got {got!r}, want {want!r}")


check("quarters cover one year", quarters("2023Q1", "2023Q4"),
      ["CY2023Q1I", "CY2023Q2I", "CY2023Q3I", "CY2023Q4I"])
check("quarters roll over a year end", quarters("2023Q4", "2024Q1"), ["CY2023Q4I", "CY2024Q1I"])
check("a single quarter works", quarters("2020Q2", "2020Q2"), ["CY2020Q2I"])
check("the instant suffix is present, because the field is a balance",
      all(period.endswith("I") for period in quarters("2015Q1", "2024Q3")), True)
check("a minimum history is required for a revision", MIN_FACTS >= 3, True)

check("every declared group has a benchmark", set(GROUPS) <= set(BENCHMARK), True)
check("no industry code maps to the placebo group", "other" not in set(SIC_GROUP.values()), True)
check("the mechanism's industries are declared",
      {"1731", "3612", "4911", "6798"} <= set(SIC_GROUP), True)
check("electrical work is a contractor", SIC_GROUP["1731"], "contractor")
check("transformers are equipment", SIC_GROUP["3612"], "equipment")
check("electric services are a utility", SIC_GROUP["4911"], "utility")

check("a t statistic of identical values is undefined rather than infinite",
      tstat([0.01, 0.01, 0.01]), None)
check("too few values give no statistic", tstat([0.01, 0.02]), None)
values = [0.01, 0.02, 0.03, 0.04]
check("the t statistic matches the textbook formula",
      round(tstat(values), 6),
      round(statistics.mean(values) / (statistics.stdev(values) / math.sqrt(len(values))), 6))

if failures:
    print("\n".join(f"  FAIL {f}" for f in failures))
    print(f"\n{14 - len(failures)}/14 passed")
    raise SystemExit(1)
print("\n14/14 passed")
