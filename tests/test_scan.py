#!/usr/bin/env python3
"""Offline tests for the scan node space rules. No network."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from check_scan import load, pairs, problems  # noqa: E402

failures: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        failures.append(f"{name}: got {got!r}, want {want!r}")


def node(node_id: str, status: str = "populated", blocker: str = "",
         representation_status: str | None = None) -> dict:
    return {
        "id": node_id, "family": node_id.split(":")[0], "layer": "feature", "meaning": "test node",
        "status": status,
        "representations": [{
            "kind": "series", "source": "source:test", "clock": "daily",
            "availability": "the close", "status": representation_status or status, "blocker": blocker,
        }],
    }


GOOD = [node("price:commodity:gas"), node("price:commodity:copper"), node("water:drought:severity")]
check("a well formed node space has no problems", problems(GOOD), [])

check("a duplicate id is caught", len(problems([node("price:commodity:gas"),
                                                node("price:commodity:gas")])), 1)
check("a malformed id is caught",
      any("id should read" in p for p in problems([node("gas")])), True)
check("an unknown status is caught",
      any("is not one of" in p for p in problems([node("price:commodity:gas", status="maybe")])), True)
check("a node with no meaning is caught",
      any("no meaning" in p for p in problems([{"id": "price:commodity:gas", "status": "populated",
                                                "representations": [{}]}])), True)
check("a node with no representation is a label, not a node",
      any("not a node" in p for p in problems([{"id": "price:commodity:gas", "status": "populated",
                                                "meaning": "x", "representations": []}])), True)
check("a blocked representation without a blocker is caught",
      any("hides why" in p for p in problems([node("price:compute:rental", status="blocked",
                                                  representation_status="blocked")])), True)
check("a node called populated while carrying a blocked series is caught",
      any("called populated but carries" in p
          for p in problems([node("price:compute:rental", status="populated", blocker="paid tier",
                                  representation_status="blocked")])), True)
check("a node called blocked with no blocked series is caught",
      any("no blocked or thin representation" in p
          for p in problems([node("price:compute:rental", status="blocked",
                                  representation_status="populated")])), True)

COMPLETE = [node("price:commodity:gas"),
            node("price:compute:rental", status="blocked", blocker="paid tier",
                 representation_status="blocked"),
            node("water:drought:severity")]
declared = pairs(COMPLETE)
check("every pair is declared once", len(declared), 3)
check("pairs are canonical, so a pair cannot appear twice in two orders",
      [(p["a"] <= p["b"]) for p in declared], [True, True, True])
check("a pair between two measurable nodes is measurable",
      sum(1 for p in declared if p["coverage"] == "measurable"), 1)
check("a pair touching a blocked node is blocked and says why",
      all(p["reason"] for p in declared if p["coverage"] == "blocked"), True)
check("the blocked pair count is the remainder",
      sum(1 for p in declared if p["coverage"] == "blocked"), 2)

declared_ids = {p["a"] for p in declared} | {p["b"] for p in declared}
check("every declared node appears in the pair list", declared_ids,
      {n["id"] for n in COMPLETE})
check("the declared node space loads", len(load()) > 5, True)
check("the real node space has no problems", problems(load()), [])
check("the real node space declares every pair",
      len(pairs(load())), len(load()) * (len(load()) - 1) // 2)

if failures:
    print("\n".join(f"  FAIL {f}" for f in failures))
    print(f"\n{19 - len(failures)}/19 passed")
    raise SystemExit(1)
print("\n19/19 passed")
