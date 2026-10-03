#!/usr/bin/env python3
"""Tests for the algoterminal linkage.

Run: python3 tests/test_link_algoterminal.py

The linkage does one job: make every node, representation and source our work depends on either
resolve to something real in the algoterminal stack, or be declared as a gap with a reason. Silent
assumptions about what the graph contains are how a study ends up claiming a feature nobody built.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from link_algoterminal import linkage_problems  # noqa: E402

GRAPH = {"feature:weather:heat-exposure", "entity:refinery:facility:1", "outcome:gasoline-crack"}
SOURCES = {"source:sec", "source:eia-930"}


def main() -> int:
    failures = []

    def check(name, got, expect_empty=True):
        if (len(got) == 0) != expect_empty:
            failures.append(name)
            print(f"FAIL {name}: {got}")
        else:
            print(f"ok   {name}")

    resolved = {"event": "node_resolved", "node": "outcome:gasoline-crack", "reason": "exists"}
    check("a resolved node that exists passes", linkage_problems([resolved], GRAPH, SOURCES))
    check("a resolved node that does not exist fails",
          linkage_problems([{**resolved, "node": "feature:power:queue"}], GRAPH, SOURCES),
          expect_empty=False)
    declare = {"event": "node_proposed", "node": "feature:power:interconnection-queue",
               "layer": "feature", "proposed_type": "derived_feature", "reason": "not in the graph"}
    check("a proposed node that does not exist yet passes",
          linkage_problems([declare], GRAPH, SOURCES))
    check("proposing a node the graph already has fails",
          linkage_problems([{**declare, "node": "outcome:gasoline-crack"}], GRAPH, SOURCES),
          expect_empty=False)
    check("a malformed proposed node id fails",
          linkage_problems([{**declare, "node": "interconnection-queue"}], GRAPH, SOURCES),
          expect_empty=False)
    check("proposing a source the inventory already has fails",
          linkage_problems([{"event": "source_proposed", "source": "source:sec",
                             "reason": "x"}], GRAPH, SOURCES), expect_empty=False)
    check("proposing a new source passes",
          linkage_problems([{"event": "source_proposed", "source": "source:ornn-ocpi",
                             "reason": "no compute index in the inventory"}], GRAPH, SOURCES))
    check("a known source passes",
          linkage_problems([{"representation_source": "source:sec"}], GRAPH, SOURCES))
    check("an unknown source with no declaration fails",
          linkage_problems([{"representation_source": "source:ornn"}], GRAPH, SOURCES),
          expect_empty=False)
    check("events with no linkage fields are ignored",
          linkage_problems([{"event": "decision", "choice": "x"}], GRAPH, SOURCES))

    print(f"\n{10 - len(failures)}/10 passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
