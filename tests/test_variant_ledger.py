#!/usr/bin/env python3
"""Offline tests for the variant ledger accounting. No network, no artifacts needed."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_variant_ledger import ROLES, headline, tstat  # noqa: E402

failures: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        failures.append(f"{name}: got {got!r}, want {want!r}")


check("three roles are declared", ROLES, ("search", "control", "measurement"))

rows = [
    {"family": "a search", "role": "search", "cells": "100", "expected_by_chance": "5.0",
     "survivors": "7"},
    {"family": "a control", "role": "control", "cells": "50", "expected_by_chance": "2.5",
     "survivors": "7"},
    {"family": "a measurement", "role": "measurement", "cells": "10", "expected_by_chance": "",
     "survivors": ""},
]
search = headline(rows, "search")
check("only searches are counted in the search headline", search["cells"], 100)
check("the search survivors are counted", search["survivors"], 7)
check("the search expectation is summed", search["expected"], 5.0)

control = headline(rows, "control")
check("a control is counted separately", control["cells"], 50)
mixed = rows + [{"family": "a search with nothing", "role": "search", "cells": "20",
                 "expected_by_chance": "1.0", "survivors": "0"}]
check("a control's survivors never enter the search total",
      headline(mixed, "search")["survivors"], 7)
check("the control still reports its own", headline(mixed, "control")["survivors"], 7)

check("a measurement is excluded from both, having no null",
      headline([rows[2]], "search")["cells"], 0)
check("an empty ledger is handled", headline([], "search"),
      {"families": 0, "cells": 0, "expected": 0, "survivors": 0})

# The ratio a reader should be given, and the case that matters: no better than chance.
def ratio(role_rows):
    stats = headline(role_rows, "search")
    return stats["survivors"] / stats["expected"] if stats["expected"] else None


check("a search at three times chance shows a ratio above one", round(ratio(rows), 1), 1.4)
check("a search with nothing shows a ratio of zero",
      ratio([{"role": "search", "cells": "100", "expected_by_chance": "5.0", "survivors": "0"}]), 0.0)

check("a t statistic of identical values is undefined", tstat([0.01, 0.01, 0.01]), None)
check("too few values give no statistic", tstat([0.01, 0.02]), None)

if failures:
    print("\n".join(f"  FAIL {f}" for f in failures))
    print(f"\n{12 - len(failures)}/12 passed")
    raise SystemExit(1)
print("\n12/12 passed")
