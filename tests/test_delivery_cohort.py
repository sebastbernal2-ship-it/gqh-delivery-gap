#!/usr/bin/env python3
"""Tests for cohort matching between a promised vintage and a realization vintage.

Run: python3 tests/test_delivery_cohort.py

A cohort is the set of units promised in one vintage. For each unit we look for what
actually happened in a later vintage:
  in Operating            -> realized, with an actual operating month
  in Canceled or Postponed -> cancelled, mass reported separately
  still in Planned         -> not yet realized, censored and excluded
The realization vintage's Planned sheet is passed in, because "still planned" and
"gone without explanation" are different facts and only that sheet separates them.
  gone from every sheet    -> unexplained, counted separately
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pandas as pd  # noqa: E402

from delivery.cohort import match_cohort  # noqa: E402


def planned(rows):
    return pd.DataFrame(rows, columns=["plant_id", "generator_id", "mw", "month_index",
                                       "ba_code", "technology"])


def operating(rows):
    return pd.DataFrame(rows, columns=["plant_id", "generator_id", "mw",
                                       "operating_month_index"])


def canceled(rows):
    return pd.DataFrame(rows, columns=["plant_id", "generator_id", "mw"])


def main() -> int:
    failures = []

    def check(name, got, want):
        if got != want:
            failures.append(name)
            print(f"FAIL {name}: got {got!r} want {want!r}")
        else:
            print(f"ok   {name}")

    promised = planned([
        [1, "A", 100.0, 10, "PJM", "Solar"],     # arrives 2 months late
        [2, "B", 50.0, 10, "PJM", "Gas"],        # arrives on time
        [3, "C", 20.0, 10, "ERCOT", "Wind"],     # cancelled
        [4, "D", 10.0, 10, "ERCOT", "Solar"],    # still planned
    ])
    actual = operating([
        [1, "A", 100.0, 12],
        [2, "B", 50.0, 10],
    ])
    canc = canceled([[3, "C", 20.0]])

    still = planned([[4, "D", 10.0, 10, "ERCOT", "Solar"]])
    out = match_cohort(promised, actual, canc, still)

    check("arrived units matched", out["n_arrived"], 2)
    check("cancelled mw", out["cancelled_mw"], 20.0)
    check("censored units (still planned)", out["n_censored"], 1)
    check("unexplained units", out["n_unexplained"], 0)
    check("realized pairs carry the delay", sorted(
        p["realized"] - p["promised"] for p in out["pairs"]), [0, 2])
    check("pair mw is the operating mw", sorted(p["mw"] for p in out["pairs"]), [50.0, 100.0])
    check("by region keys", sorted(out["by_region"]), ["ERCOT", "PJM"])
    check("PJM arrived mw", out["by_region"]["PJM"]["mw_arrived"], 150.0)
    check("ERCOT cancelled mw", out["by_region"]["ERCOT"]["cancelled_mw"], 20.0)

    # A unit that vanished from every sheet is reported, not silently dropped.
    out2 = match_cohort(planned([[9, "Z", 5.0, 1, "MISO", "Gas"]]), operating([]),
                        canceled([]), planned([]))
    check("vanished unit counted", out2["n_unexplained"], 1)
    check("vanished unit adds no pair", len(out2["pairs"]), 0)

    # MW from the promised vintage is used when the operating row has none.
    out3 = match_cohort(planned([[7, "Y", 33.0, 1, "PJM", "Gas"]]),
                        operating([[7, "Y", None, 3]]), canceled([]), planned([]))
    check("mw falls back to the promised row", out3["pairs"][0]["mw"], 33.0)


    # The window filter: only units promised inside the observable window are measured.
    # A unit promised years out cannot have its delay measured yet, and including it
    # would mix a measured delay with an unmeasurable promise.
    from delivery.cohort import select_window  # noqa: E402

    wide = planned([
        [1, "A", 100.0, 10, "PJM", "Solar"],
        [2, "B", 100.0, 40, "PJM", "Solar"],
        [3, "C", 100.0, 5, "PJM", "Solar"],
    ])
    windowed = select_window(wide, 10, 22)
    check("window keeps promised dates in range", list(windowed["generator_id"]), ["A"])
    check("window reports what it excluded",
          int(select_window(wide, 10, 22, report=True).attrs["excluded"]), 2)

    print(f"\n{14 - len(failures)}/14 passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
