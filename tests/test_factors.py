#!/usr/bin/env python3
"""Offline tests for the factor parsers, using recorded response shapes."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from factors.drought import parse_csv  # noqa: E402
from factors.weather import known_at, monthly_series, state_anomaly  # noqa: E402

failures: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        failures.append(f"{name}: got {got!r}, want {want!r}")


# The drought service answers in CSV, with a header whose columns vary between states. Both shapes are
# recorded here, because locating columns by position silently produced impossible values once.
SHORT = (
    "MapDate,StateAbbreviation,None,D0,D1,D2,D3,D4,ValidStart\n"
    "20220628,TX,3.71,96.29,86.39,64.99,43.79,15.82,2022-06-28\n"
    "20220621,TX,7.01,92.99,81.18,64.62,43.83,17.11,2022-06-21\n"
)
LONG = (
    "MapDate,StateAbbreviation,None,D0,D1,D2,D3,D4,ValidStart,ValidEnd,StatisticFormatID\n"
    "20220628,TX,3.71,96.29,86.39,64.99,43.79,15.82,2022-06-28,2022-07-05,1\n"
    "20220628,TX,3.71,96.29,86.39,64.99,43.79,15.82,2022-06-28,2022-07-05,9\n"
)

short = parse_csv(SHORT)
long = parse_csv(LONG)
check("the short shape is read", sorted(short), ["2022-06"])
check("the classes are not summed, because they are nested",
      round(short["2022-06"], 3), round((64.99 + 64.62) / 2, 3))
check("the long shape is read too", round(long["2022-06"], 3), 64.99)
check("a non percent statistic format is ignored rather than averaged in", len(long), 1)

impossible = "MapDate,StateAbbreviation,None,D0,D1,D2,D3,D4,ValidStart\n20220628,TX,1,2,3,150,4,5,2022-06-28\n"
check("an impossible share is dropped", parse_csv(impossible), {})
check("an empty body yields nothing", parse_csv(""), {})
check("a header without the class column yields nothing", parse_csv("MapDate,State\n20220628,TX\n"), {})

series = {"2024-01": 1.0, "2024-02": 2.0, "2024-03": 3.0}
check("a value is known one month after its own month", known_at("2024-03", series, lag=1), 2.0)
check("nothing is known before the series starts", known_at("2024-01", series, lag=1), None)

anomaly = state_anomaly({f"2020-{m:02d}": float(m) for m in range(1, 13)})
check("an anomaly is produced per month", len(anomaly), 12)
check("a short series yields no anomalies", state_anomaly({"2020-01": 1.0}), {})

if failures:
    print("\n".join(f"  FAIL {f}" for f in failures))
    print(f"\n{15 - len(failures)}/15 passed")
    raise SystemExit(1)
print("\n15/15 passed")
