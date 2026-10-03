#!/usr/bin/env python3
"""Offline tests for the two declared windows and the firewall between them."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from scan.windows import COMPUTE_ERA, FIREWALL, MECHANISM, WINDOWS, clip, describe, get  # noqa: E402

failures: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        failures.append(f"{name}: got {got!r}, want {want!r}")


def caught(call) -> object:
    try:
        call()
    except Exception as exc:
        return exc
    return None


check("two studies are declared", sorted(WINDOWS), ["compute-era", "mechanism-and-strategy"])
check("the mechanism study keeps its long history", MECHANISM.history_start, "2015-07")
check("the mechanism study keeps its twenty four month holdout", MECHANISM.sealed_start, "2022-10")
check("the compute study starts where its archive starts", COMPUTE_ERA.history_start, "2022-06")
check("the compute study seals the most recent fifth", COMPUTE_ERA.sealed_start, "2024-04")

check("the compute development window opens at its history start",
      COMPUTE_ERA.in_development("2022-06"), True)
check("the compute development window closes in March 2024",
      COMPUTE_ERA.in_development("2024-03"), True)
check("the first holdout month is not development", COMPUTE_ERA.in_development("2024-04"), False)
check("the holdout is the last six months",
      [COMPUTE_ERA.in_holdout(m) for m in ("2024-03", "2024-04", "2024-09", "2024-10")],
      [False, True, True, False])

# The overlap is the whole reason the firewall exists: study two explores inside study one's holdout.
check("the compute development window overlaps the mechanism holdout",
      MECHANISM.in_holdout("2023-01") and COMPUTE_ERA.in_development("2023-01"), True)
check("the firewall forbids the compute study from changing the strategy study",
      "Nothing measured in the compute era study may change the design" in FIREWALL, True)

series = {"2015-08": 1.0, "2019-01": 2.0, "2022-09": 3.0, "2022-10": 4.0, "2023-06": 5.0,
          "2024-04": 6.0}
check("clipping keeps only development months",
      sorted(clip(series, MECHANISM)), ["2015-08", "2019-01", "2022-09"])
check("the holdout is excluded from development", "2022-10" in clip(series, MECHANISM), False)
check("the holdout can be opened explicitly",
      sorted(clip(series, MECHANISM, include_holdout=True)),
      ["2015-08", "2019-01", "2022-09", "2022-10", "2023-06", "2024-04"])
# 2022-10 belongs to the compute study's development window even though it is inside the mechanism
# study's holdout. That overlap is the reason the firewall exists, and this asserts it rather than hides it.
check("the compute study clips to its own development window",
      sorted(clip(series, COMPUTE_ERA)), ["2022-09", "2022-10", "2023-06"])
check("the compute study also ignores anything before its history",
      "2019-01" in clip(series, COMPUTE_ERA), False)

check("an unknown window is refused rather than defaulted",
      isinstance(caught(lambda: get("nope")), KeyError), True)
check("a known window is returned by name", get("compute-era"), COMPUTE_ERA)
check("the description names both studies",
      all(name in describe() for name in ("compute-era", "mechanism-and-strategy")), True)

if failures:
    print("\n".join(f"  FAIL {f}" for f in failures))
    print(f"\n{20 - len(failures)}/20 passed")
    raise SystemExit(1)
print("\n20/20 passed")
