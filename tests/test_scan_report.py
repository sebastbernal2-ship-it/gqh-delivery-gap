#!/usr/bin/env python3
"""Offline tests for the two corrections applied after the scan. No network."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from scan.report import canonical, family_counts, firm_group_series, summarise  # noqa: E402

failures: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        failures.append(f"{name}: got {got!r}, want {want!r}")


NODES = {
    "promise:power:planned-capacity-revision": {"id": "promise:power:planned-capacity-revision", "family": "promise"},
    "firm:obligation:y": {"id": "firm:obligation:y", "family": "firm"},
    "price:commodity:gas": {"id": "price:commodity:gas", "family": "price"},
    "price:commodity:copper": {"id": "price:commodity:copper", "family": "price"},
}

ROWS = [
    {"a": "promise:power:planned-capacity-revision", "b": "price:commodity:gas", "series_a": "promise_next_year_revision",
     "series_b": "gas_price", "placebo_percentile": "0.99"},
    {"a": "promise:power:planned-capacity-revision", "b": "price:commodity:gas", "series_a": "promise_total_level",
     "series_b": "gas_price", "placebo_percentile": "0.99"},
    {"a": "price:commodity:gas", "b": "price:commodity:copper", "series_a": "gas_price",
     "series_b": "copper_price", "placebo_percentile": "0.99"},
    {"a": "firm:obligation:y", "b": "price:commodity:gas", "series_a": "firm_share_negative_revision",
     "series_b": "gas_price", "placebo_percentile": "0.40"},
]

kept = canonical(ROWS)
check("one representation per node is kept", len(kept), 3)
check("the canonical promise series survives",
      any(r["series_a"] == "promise_next_year_revision" for r in kept), True)
check("a second representation of the same node is dropped",
      any(r["series_a"] == "promise_total_level" for r in kept), False)

counts = family_counts(kept, NODES)
check("pairs inside one family are counted separately", counts["same_family"], 1)
check("pairs across families are counted", counts["cross_family"], 2)
check("survivors inside a family are counted", counts["same_survivors"], 1)
check("survivors across families are counted", counts["cross_survivors"], 1)
check("the chance expectation for cross-family pairs is stated",
      round(counts["expected_cross"], 3), round(2 * 0.05, 3))

text = summarise(ROWS, NODES)
check("the summary reports both pair counts", "inside one family" in text, True)
check("the summary says a same-family pair is not a discovery", "not a discovery" in text, True)

# A group series: the share of firms whose obligation fell, and only for the requested group.
tmp = Path(tempfile.mkdtemp(prefix="scan-"))
events = tmp / "events.csv"
events.write_text(
    "cik,name,ticker,sic,group,change,value,earliest_availability_utc,in_sealed_window\n"
    "1,A,AAA,1731,contractor,-5,100,2024-01-05T20:00:00+00:00,False\n"
    "2,B,BBB,1731,contractor,5,100,2024-01-20T20:00:00+00:00,False\n"
    "3,C,CCC,7372,datacenter,-5,100,2024-01-10T20:00:00+00:00,False\n"
    "4,D,DDD,4911,utility,-5,100,2024-01-10T20:00:00+00:00,True\n")
series = firm_group_series(events, {"contractor"})
check("only the requested group is used", series, {"2024-01": 0.5})
check("the sealed row is excluded",
      firm_group_series(events, {"utility"}), {})
check("a comparison group is separate",
      firm_group_series(events, {"datacenter"}), {"2024-01": 1.0})

if failures:
    print("\n".join(f"  FAIL {f}" for f in failures))
    print(f"\n{15 - len(failures)}/15 passed")
    raise SystemExit(1)
print("\n15/15 passed")
