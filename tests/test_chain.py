#!/usr/bin/env python3
"""Tests for the chain log validator.

Run: python3 tests/test_chain.py

The chain invites scope creep and quiet overfitting. The log exists so the dangerous moves are
impossible to make silently:

  scope       caps on pilot edges, unmeasured pilot edges, and P&L-carrying roles
  load        every edge must change the position when it is false, or it is deleted
  nodes       every edge endpoint is declared, and every declaration is used
  evidence    a status may only become "measured" with an evidence path that exists
  freeze      once the sealed window opens, no edge is added, no status upgraded, no bound raised
  honesty     downgrades, sources and decisions are recorded like everything else
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_chain import problems  # noqa: E402

CHAIN = "t-example"
EXISTING = ["results/e1.json", "docs/chains/t-example-plan.md"]
A = "feature:power:delivery-revision"
B = "outcome:firm:revenue"

DECLARATIONS = [
    {"ts": "2026-10-03T09:00:00Z", "chain": CHAIN, "event": "node_resolved",
     "phase": "development", "node": A, "reason": "exists in the QuantGraph"},
    {"ts": "2026-10-03T09:00:01Z", "chain": CHAIN, "event": "node_resolved",
     "phase": "development", "node": B, "reason": "exists in the QuantGraph"},
]


def edge(**over):
    base = {"ts": "2026-10-03T10:00:00Z", "chain": CHAIN, "event": "edge_added",
            "phase": "development", "edge": "e-1", "status": "testable",
            "from_node": A, "to_node": B, "edge_type": "drives",
            "conditions": "during the capex cycle", "if_false": "we do not trade",
            "exposure_bound": "2% NAV", "mode": "core", "pilot": True}
    base.update(over)
    return base


def log(*events):
    return DECLARATIONS + list(events)


def main() -> int:
    failures = []

    def check(name, got, expect_empty=True):
        if (len(got) == 0) != expect_empty:
            failures.append(name)
            print(f"FAIL {name}: {got}")
        else:
            print(f"ok   {name}")

    check("a well formed edge passes", problems(log(edge()), EXISTING))
    check("an edge with no consequence when false fails",
          problems(log(edge(if_false="nothing")), EXISTING), expect_empty=False)
    check("an edge with no conditions fails",
          problems(log(edge(conditions="")), EXISTING), expect_empty=False)
    check("an unknown semantic edge type fails",
          problems(log(edge(edge_type="sortof_affects")), EXISTING), expect_empty=False)
    check("an edge endpoint that is never declared fails",
          problems(DECLARATIONS + [edge(to_node="outcome:firm:unknown")], EXISTING),
          expect_empty=False)
    check("a declared node that no edge uses is decoration",
          problems(DECLARATIONS + [{"ts": "2026-10-03T09:00:02Z", "chain": CHAIN,
                                    "event": "node_proposed", "phase": "development",
                                    "node": "feature:power:queue", "layer": "feature",
                                    "proposed_type": "derived_feature", "reason": "new"}], EXISTING),
          expect_empty=False)

    check("a measured status without evidence fails",
          problems(log(edge(status="measured")), EXISTING), expect_empty=False)
    check("a measured status with real evidence passes",
          problems(log(edge(status="measured", evidence="results/e1.json")), EXISTING))

    change = {"ts": "2026-10-03T11:00:00Z", "chain": CHAIN, "event": "status_changed",
              "phase": "development", "edge": "e-1", "from": "testable", "to": "proxied"}
    check("a documented status change passes", problems(log(edge(), change), EXISTING))
    check("an upgrade with no evidence fails",
          problems(log(edge(), {**change, "to": "measured"}), EXISTING), expect_empty=False)
    check("an upgrade pointing at a missing file fails",
          problems(log(edge(), {**change, "to": "measured", "evidence": "results/none.json"}),
                   EXISTING), expect_empty=False)

    sealed = {"ts": "2026-10-03T23:00:00Z", "chain": CHAIN, "event": "sealed_opened",
              "phase": "sealed", "revision": "abc123", "run_plan": "docs/chains/t-example-plan.md"}
    after = {**change, "phase": "sealed", "to": "measured", "evidence": "results/e1.json"}
    check("no upgrade after the sealed window opens",
          problems(log(edge(), sealed, after), EXISTING), expect_empty=False)
    check("a downgrade after the sealed window opens is allowed",
          problems(log(edge(status="measured", evidence="results/e1.json"), sealed,
                    {**after, "from": "measured", "to": "proxied"}), EXISTING))
    check("no new edge after the sealed window opens",
          problems(log(edge(), sealed, edge(edge="e-2")), EXISTING), expect_empty=False)
    check("no bound increase after the sealed window opens",
          problems(log(edge(status="measured", evidence="results/e1.json"), sealed,
                    {"ts": "2026-10-04T11:00:00Z", "chain": CHAIN, "event": "bound_changed",
                     "phase": "sealed", "edge": "e-1", "from": "2% NAV", "to": "5% NAV",
                     "reason": "conviction"}), EXISTING), expect_empty=False)

    check("the cap on pilot edges applies",
          problems(log(*[edge(edge=f"e-{i}", status="measured", evidence="results/e1.json")
                         for i in range(9)]), EXISTING), expect_empty=False)
    check("the cap on unmeasured pilot edges applies",
          problems(log(*[edge(edge=f"e-{i}") for i in range(4)]), EXISTING), expect_empty=False)
    check("parked edges are recorded but do not consume pilot budget",
          problems(log(*[edge(edge=f"e-p{i}", pilot=False) for i in range(9)]), EXISTING))
    check("only one P&L carrying role in the pilot",
          problems(log(edge(edge="e-a", mode="expression"), edge(edge="e-b", mode="hedge")),
                   EXISTING), expect_empty=False)

    source = {"ts": "2026-10-03T09:01:00Z", "chain": CHAIN, "event": "source_proposed",
              "phase": "development", "source": "source:eia-860m", "reason": "not in the inventory"}
    check("a declared source that no edge needs is decoration", problems(log(source), EXISTING),
          expect_empty=False)
    check("a declared source used by an edge passes",
          problems(log(source, edge(representation_source="source:eia-860m")), EXISTING))

    check("decisions are accepted and counted",
          problems(log(edge(), {"ts": "2026-10-03T12:00:00Z", "chain": CHAIN, "event": "decision",
                                "phase": "development", "choice": "horizon",
                                "value": "10 sessions", "reason": "initial candidate"}), EXISTING))

    print(f"\n{22 - len(failures)}/22 passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
