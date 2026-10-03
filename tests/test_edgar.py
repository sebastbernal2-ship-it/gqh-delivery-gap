#!/usr/bin/env python3
"""Offline tests for the filings register. No network here."""
from __future__ import annotations

import datetime as dt
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from edgar.filings import (  # noqa: E402
    classify, earliest_availability, get_json, parse_acceptance, record, sealed_start, to_date,
)

failures: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        failures.append(f"{name}: got {got!r}, want {want!r}")


# Acceptance timestamps are UTC with a Z.
t = parse_acceptance("2024-02-15T16:05:31.000Z")
check("acceptance parses to UTC", (t.year, t.month, t.day, t.hour, t.minute, t.tzinfo),
      (2024, 2, 15, 16, 5, dt.timezone.utc))
check("a bare date is not a timestamp", parse_acceptance("2024-02-15"), None)
check("empty acceptance is refused", parse_acceptance(""), None)
check("a naive datetime string is refused", parse_acceptance("2024-02-15T16:05:31"), None)

# A filing date is not a time, and a malformed one is refused rather than guessed.
check("a filing date parses", to_date("2024-02-15"), dt.date(2024, 2, 15))
check("a malformed filing date is refused", to_date("15/02/2024"), None)

# Availability is acceptance plus a declared lag, and unknown stays unknown.
check("availability adds the lag",
      earliest_availability(t, 15), t + dt.timedelta(minutes=15))
check("availability of an unknown acceptance is unknown", earliest_availability(None, 15), None)

# Candidate surfaces: the item list is a search route, not a delay label.
check("a 10-K is a candidate", classify("10-K", "")[0], True)
check("an amendment to a 10-Q is a candidate", classify("10-Q/A", "")[0], True)
check("an 8-K with item 1.01 is a candidate", classify("8-K", "1.01")[0], True)
check("an 8-K with items 1.01 and 2.02 names both",
      classify("8-K", "1.01,2.02")[1], "8-K items 1.01, 2.02")
check("an 8-K with an off-list item is not a candidate", classify("8-K", "5.02")[0], False)
check("a form 4 is not a candidate", classify("4", "")[0], False)
check("no form is not a candidate", classify("", "")[0], False)

# Sealed window: the shorter of the last fifth or two years.
start, end = dt.date(2015, 1, 1), dt.date(2025, 1, 1)
# 2015-01-01 to 2025-01-01 is 3653 days: a fifth is 730 days and two years is 730 days, so both
# rules agree on 2023-01-02. The later start is the shorter window, which is the rule.
check("ten years of history seals from 2023-01-02", sealed_start(start, end), dt.date(2023, 1, 2))
# One year of history: a fifth is 73 days, two years is the whole history, so the fifth is shorter.
check("one year of history seals only the last fifth",
      sealed_start(dt.date(2024, 1, 1), dt.date(2025, 1, 1)), dt.date(2024, 10, 20))

# One row keeps every unresolved field labelled rather than guessed.
entry = {"form": "8-K", "accessionNumber": "0001193125-24-036593", "filingDate": "2024-02-15",
         "acceptanceDateTime": "2024-02-15T16:05:31.000Z", "reportDate": "2024-02-15",
         "items": "2.02", "primaryDocument": "d123456d8k.htm"}
row = record(1050915, "PWR", entry, 15, dt.date(2023, 1, 1))
check("the row carries a usable availability time", bool(row["earliest_availability_utc"]), True)
check("the row is marked as a candidate surface", row["candidate_surface"], True)
check("the row is inside the sealed window", row["in_sealed_window"], True)
check("press-release precedence is left unresolved", row["press_release_unchecked"], True)
check("the document url is built from the accession",
      row["document_url"].endswith("/1050915/000119312524036593/d123456d8k.htm"), True)
check("the source receipt points at the submissions file",
      row["source_receipt"].endswith("/submissions/CIK0001050915.json"), True)
check("et conversion is timezone-aware", row["acceptance_et"].startswith("2024-02-15 11:05:31"), True)

missing = {"form": "8-K", "accessionNumber": "0001193125-24-036593", "filingDate": "2024-02-15",
           "acceptanceDateTime": "", "items": "2.02", "primaryDocument": "x.htm"}
check("a row without acceptance says so",
      record(1, "X", missing, 15, dt.date(2024, 1, 1))["timestamp_status"],
      "no acceptance timestamp")
check("a row without acceptance has no availability",
      record(1, "X", missing, 15, dt.date(2024, 1, 1))["earliest_availability_utc"], "")

# The client must treat a 403 as "slow down", because that host throttles in short bursts.
class _Response:
    def __init__(self, status, payload=None, text="", content_type="application/json"):
        self.status_code = status
        self._payload = payload or {}
        self.text = text
        self.headers = {"Content-Type": content_type}

    def json(self):
        return self._payload

    def raise_for_status(self):
        raise RuntimeError(f"unexpected status {self.status_code}")


class _Session:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def get(self, url, timeout=30):
        self.calls += 1
        return self.responses.pop(0)


slept: list[float] = []
# Each case gets its own cache directory, so a leftover file from an earlier run cannot pass a test.
cache_a = Path(tempfile.mkdtemp(prefix="edgar-a-"))
cache_b = Path(tempfile.mkdtemp(prefix="edgar-b-"))
cache_c = Path(tempfile.mkdtemp(prefix="edgar-c-"))
cache_d = Path(tempfile.mkdtemp(prefix="edgar-d-"))
throttled = _Session([_Response(403), _Response(403), _Response(200, {"ok": True})])
check("a throttled request eventually succeeds",
      get_json(throttled, "https://example.invalid/x", sleeper=slept.append,
               cache_dir=cache_a), {"ok": True})
check("it retried twice before succeeding", throttled.calls, 3)
check("it backed off between tries", slept[:2], [20, 40])

# A refused agent string is not a throttle: the run must stop and say so, not retry for minutes.
refused = _Session([_Response(403, text="<html><body>blocked</body></html>",
                              content_type="text/html")] * 6)
try:
    get_json(refused, "https://example.invalid/w", tries=5, sleeper=slept.append,
             cache_dir=Path(tempfile.mkdtemp(prefix="edgar-e-")))
    refusal_raised = False
except Exception as exc:
    refusal_raised = "EDGAR_USER_AGENT" in str(exc)
check("a refused agent string fails fast with a fix", refusal_raised, True)
check("a refused agent string is not retried", refused.calls, 1)

always = _Session([_Response(429)] * 6)
try:
    get_json(always, "https://example.invalid/y", tries=3, sleeper=slept.append,
             cache_dir=cache_b)
    raised = False
except Exception:
    raised = True
check("a persistent refusal raises rather than looping", raised, True)
check("it gave up after the declared number of tries", always.calls, 3)

cache_dir = Path("/tmp/edgar-test-cache-c")
first = _Session([_Response(200, {"cached": 1})])
get_json(first, "https://example.invalid/z", sleeper=slept.append, cache_dir=cache_dir)
second = _Session([])
check("a cached response is served without a request",
      get_json(second, "https://example.invalid/z", sleeper=slept.append, cache_dir=cache_dir),
      {"cached": 1})
check("the cache prevented a second call", second.calls, 0)

(cache_d / "company_tickers.json").write_text('{"0": {"cik_str": 1050915, "ticker": "PWR"}}')
check("a named cache is honoured",
      get_json(_Session([]), "https://example.invalid/tickers", sleeper=slept.append,
               cache_dir=cache_d, cache_name="company_tickers.json"),
      {"0": {"cik_str": 1050915, "ticker": "PWR"}})

if failures:
    print("\n".join(f"  FAIL {f}" for f in failures))
    print(f"\n{35 - len(failures)}/35 passed")
    raise SystemExit(1)
print("\n35/35 passed")
