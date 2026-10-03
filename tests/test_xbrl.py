#!/usr/bin/env python3
"""Offline tests for the XBRL fact panel. No network here."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_obligation_panel import as_bool, summarise  # noqa: E402
from edgar.xbrl import attach_availability, days_to_public, extract, revisions  # noqa: E402

failures: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        failures.append(f"{name}: got {got!r}, want {want!r}")


PAYLOAD = {
    "facts": {
        "us-gaap": {
            "RevenueRemainingPerformanceObligation": {
                "units": {"USD": [
                    {"end": "2023-12-31", "val": 30000, "form": "10-K", "accn": "a-2",
                     "filed": "2024-02-20"},
                    {"end": "2023-09-30", "val": 34000, "form": "10-Q", "accn": "a-1",
                     "filed": "2023-10-26"},
                ]},
            },
            "UnapprovedChangeOrdersAmount": {"units": {"USD": [
                {"end": "2017-12-31", "val": 500, "form": "10-K", "accn": "a-3", "filed": "2018-02-22"},
            ]}},
            "Revenues": {"units": {"USD": [
                {"end": "2023-12-31", "val": 999, "form": "10-K", "accn": "a-2", "filed": "2024-02-20"},
            ]}},
        },
        "pwr": {"OrderBacklog": {"units": {"USD": [
            {"end": "2019-12-31", "val": 12000, "form": "10-K", "accn": "a-0", "filed": "2020-02-01"},
        ]}}},
    }
}

rows = extract(PAYLOAD, 1050915, "PWR")
check("only the tracked fields are extracted", len(rows), 4)
check("the namespace is kept on the concept",
      sorted({r["concept"] for r in rows}),
      ["pwr:OrderBacklog", "us-gaap:RevenueRemainingPerformanceObligation",
       "us-gaap:UnapprovedChangeOrdersAmount"])
check("a custom namespace field is picked up too", any(r["concept"] == "pwr:OrderBacklog" for r in rows), True)
check("rows are ordered by concept then period",
      [(r["concept"], r["period_end"]) for r in rows][0][1], "2019-12-31")

REGISTER = [
    {"accession": "a-1", "acceptance_utc": "2023-10-26T20:11:00+00:00",
     "earliest_availability_utc": "2023-10-26T20:26:00+00:00", "in_sealed_window": False},
    {"accession": "a-2", "acceptance_utc": "2024-02-20T21:05:00+00:00",
     "earliest_availability_utc": "2024-02-20T21:20:00+00:00", "in_sealed_window": True},
]
joined = attach_availability(rows, REGISTER)
by_accession = {r["accession"]: r for r in joined}
check("a fact is joined to its own acceptance time",
      by_accession["a-1"]["acceptance_utc"], "2023-10-26T20:11:00+00:00")
check("the sealed flag arrives with the join", by_accession["a-2"]["in_sealed_window"], True)
check("a fact whose filing is missing says so",
      by_accession["a-3"]["availability_status"], "no matching filing row")
check("a missing filing leaves availability empty", by_accession["a-3"]["earliest_availability_utc"], "")

rpo = [r for r in joined if r["concept"].endswith("RevenueRemainingPerformanceObligation")]
changed = revisions(rpo)
check("the first revision has no previous value", changed[0]["previous_value"], "")
check("the second revision carries the change", changed[1]["change"], -4000)
check("the previous value is carried forward", changed[1]["previous_value"], 34000)
check("a single fact produces no change",
      revisions([by_accession["a-3"]])[0]["change"], "")

check("the lag counts days from period end to public availability",
      days_to_public({"period_end": "2023-09-30", "earliest_availability_utc": "2023-10-26T20:26:00+00:00"}), 26)
check("an unknown availability gives no lag",
      days_to_public({"period_end": "2023-09-30", "earliest_availability_utc": ""}), None)
check("a malformed period gives no lag",
      days_to_public({"period_end": "", "earliest_availability_utc": "2023-10-26T20:26:00+00:00"}), None)

# The sealed-leak guard: csv strings make "False" truthy, which would have summarised the sealed window.
check('the string "False" is false', as_bool("False"), False)
check('the string "True" is true', as_bool("True"), True)
check("a real boolean passes through", as_bool(True), True)
check("an empty cell is false", as_bool(""), False)

# The summary must fence the sealed window and drop lags it cannot trust.
sample = [
    {"ticker": "PWR", "concept": "us-gaap:RevenueRemainingPerformanceObligation", "period_end": "2023-09-30",
     "value": 1, "change": -1, "in_sealed_window": "False", "acceptance_utc": "2023-10-26T00:00:00+00:00",
     "earliest_availability_utc": "2023-10-26T00:00:00+00:00"},
    {"ticker": "PWR", "concept": "us-gaap:RevenueRemainingPerformanceObligation", "period_end": "2024-06-30",
     "value": 2, "change": 1, "in_sealed_window": "True", "acceptance_utc": "2024-07-25T00:00:00+00:00",
     "earliest_availability_utc": "2024-07-25T00:00:00+00:00"},
    {"ticker": "PWR", "concept": "us-gaap:RevenueRemainingPerformanceObligation", "period_end": "2012-12-31",
     "value": 3, "change": "", "in_sealed_window": "False", "acceptance_utc": "",
     "earliest_availability_utc": ""},
]
text = summarise(sample)
check("the sealed fact is counted as sealed", "sealed and not summarised: 1" in text, True)
check("an undated fact is excluded and counted", "no matched filing row: 1" in text, True)
check("the summarised group holds only the dated development fact", "  1 2023-09-30" in text, True)

if failures:
    print("\n".join(f"  FAIL {f}" for f in failures))
    print(f"\n{24 - len(failures)}/24 passed")
    raise SystemExit(1)
print("\n24/24 passed")
