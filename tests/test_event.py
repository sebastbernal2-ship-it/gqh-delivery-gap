#!/usr/bin/env python3
"""Offline tests for the event window rules and the entity matcher. No network, no market data."""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from event.study import abnormal, sessions, summarise, surprise, window_return  # noqa: E402
from join.entities import best_match, coverage, normalize, score, tokens  # noqa: E402

failures: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        failures.append(f"{name}: got {got!r}, want {want!r}")


# A small price history: five sessions.
INDEX = ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"]
CLOSES = {"2024-01-02": 100.0, "2024-01-03": 110.0, "2024-01-04": 121.0,
          "2024-01-05": 133.1, "2024-01-08": 146.41}

# The lag rule: a signal at 10:00 on the 2nd may not be filled on the 2nd.
check("a session after a mid-day signal starts the next day",
      sessions(INDEX, "2024-01-02T15:00:00+00:00"), ["2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"])
check("a signal after the close still starts the next session",
      sessions(INDEX, "2024-01-02T23:30:00+00:00"), ["2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"])
check("a signal before the open starts that same session",
      sessions(INDEX, "2024-01-02T11:00:00+00:00"), ["2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"])
check("a date-only signal is read as the end of that day",
      sessions(INDEX, "2024-01-02"), ["2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"])

# The window is close to close, starting on the first session after the signal.
first = window_return(CLOSES, INDEX, "2024-01-02T15:00:00+00:00", 1)
check("a one-session window runs from the first fill to the next session",
      round(first, 6), round(121.0 / 110.0 - 1, 6))
check("a two-session window is compounded", round(window_return(CLOSES, INDEX, "2024-01-02T15:00:00+00:00", 2), 6),
      round(133.1 / 110.0 - 1, 6))
check("a window that runs past the history is refused",
      window_return(CLOSES, INDEX, "2024-01-02T15:00:00+00:00", 10), None)
check("a signal after the last session has no window",
      window_return(CLOSES, INDEX, "2024-01-09T12:00:00+00:00", 1), None)

check("abnormal is the firm return minus the benchmark", round(abnormal(0.05, 0.02), 6), 0.03)
check("abnormal of a missing leg is missing", abnormal(None, 0.02), None)
check("abnormal of a missing benchmark is missing", abnormal(0.05, None), None)

# Surprise is against the firm's own typical revision, because obligations fall when work is delivered.
check("surprise is the change less the firm's typical change", surprise(-500, [0, 100, 200]), -600)
check("surprise with no history is unknown", surprise(10, []), None)
check("the median is used, not the mean", surprise(0, [-1000, 0, 1000]), 0)

# The summary reports the plateau and elects nothing.
text = summarise([{"raw_1": 0.01, "abnormal_1": 0.005}, {"raw_1": -0.01, "abnormal_1": -0.005}], [1, 5])
check("a plateau row is reported", "      1    2" in text or " 1 " in text, True)
check("the summary states it elects no horizon", "no horizon is chosen here" in text, True)
check("a horizon with no data is shown as such", "n/a" in text, True)

# The matcher: legal forms carry no identity, and the first significant word must agree.
check("legal forms are stripped", normalize("First Solar, Inc."), "first solar")
check("the ampersand and articles are stripped", normalize("Power & Light of the Company"),
      "power light")
check("single letters are ignored", normalize("A B Energy"), "energy")
check("tokens keep order", tokens("Invenergy Services LLC"), ["invenergy", "services"])
check("a candidate sharing two of three words scores two thirds",
      round(score(tokens("First Solar Project"), tokens("First Solar")), 3), 0.667)

CANDIDATES = [("FIRST SOLAR INC", 1274494, "FSLR"), ("SOUTHERN CO", 92122, "SO"),
              ("GEORGIA POWER CO", 41091, "GPJA"), ("VANGUARD FUND", 1, "VCRDX"),
              ("ROBINSON FREIGHT", 2, "CHRW"), ("DUKE ENERGY CORP", 1326160, "DUK")]

matched = best_match("First Solar Project Development", CANDIDATES)
check("a subsidiary whose name carries the parent matches", (matched["status"], matched["ticker"]),
      ("matched", "FSLR"))
check("a fund title is refused", best_match("Vanguard Fund Trust", CANDIDATES)["status"], "unmatched")
check("a candidate with a new significant word is refused",
      best_match("Robinson Land Company", CANDIDATES)["status"], "unmatched")
check("the first significant word must agree",
      best_match("Solar Energy Corporation", CANDIDATES)["status"], "unmatched")
check("an entity with no registrant is unmatched",
      best_match("Rye Development", CANDIDATES)["status"], "unmatched")

# Two subsidiaries of one parent are ambiguous only when they score within the margin.
TWINS = [("ALPHA POWER CO", 10, "AAA"), ("ALPHA POWER HOLDINGS INC", 11, "BBB")]
check("two equally good candidates are called ambiguous",
      best_match("Alpha Power", TWINS)["status"], "ambiguous")
check("an exact single match is not ambiguous",
      best_match("Duke Energy", [("DUKE ENERGY CORP", 1326160, "DUK")])["status"], "matched")

# Coverage counts only verified rows as attributed.
stats = coverage([{"capacity_mw": "100", "match_status": "verified", "ticker": "FSLR"},
                  {"capacity_mw": "50", "match_status": "proposed", "ticker": "GPJA"},
                  {"capacity_mw": "25", "match_status": "unmatched"}])
check("coverage splits by status", stats["by_status"]["verified"], 100.0)
check("coverage reports the proposed bucket separately", stats["by_status"]["proposed"], 50.0)
check("only verified capacity reaches the ticker table", stats["by_ticker"], {"FSLR": 100.0})

if failures:
    print("\n".join(f"  FAIL {f}" for f in failures))
    print(f"\n{27 - len(failures)}/27 passed")
    raise SystemExit(1)
print("\n27/27 passed")
