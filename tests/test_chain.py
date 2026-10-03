#!/usr/bin/env python3
"""Tests for the chain log validator.

Run: python3 tests/test_chain.py

The chain invites scope creep and quiet overfitting. The log exists so that the dangerous moves
are impossible to make silently:

  scope       a hard cap on active edges, on unmeasured edges, and on P&L-carrying roles
  load        every edge must change the position when it is false, or it is deleted
  evidence    a status may only become "measured" with an evidence path that exists
  freeze      once the sealed window opens, no edge is added, no status upgraded, no bound raised
  honesty     downgrades and decisions are recorded like everything else
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_chain import problems  # noqa: E402

CHAIN = "t-example"
EXISTING = ["results/e1.json", "docs/chains/t-example-plan.md"]


def ev(**over):
    base = {"ts": "2026-10-03T10:00:00Z", "chain": CHAIN, "event": "edge_added",
            "phase": "development", "edge": "e-1", "status": "testable",
            "conditions": "during the capex cycle", "if_false": "we do not trade",
            "exposure_bound": "2% NAV", "mode": "core"}
    base.update(over)
    return base


def main() -> int:
    failures = []

    def check(name, got, expect_empty=True):
        if (len(got) == 0) != expect_empty:
            failures.append(name)
            print(f"FAIL {name}: {got}")
        else:
            print(f"ok   {name}")

    check("a well formed edge passes", problems([ev()], EXISTING))

    check("an edge with no consequence when false fails",
          problems([ev(if_false="nothing")], EXISTING), expect_empty=False)
    check("an edge with no conditions fails",
          problems([ev(conditions="")], EXISTING), expect_empty=False)

    check("a measured status without evidence fails",
          problems([ev(status="measured")], EXISTING), expect_empty=False)
    check("a measured status with real evidence passes",
          problems([ev(status="measured", evidence="results/e1.json")], EXISTING))

    events = [ev(),
              {"ts": "2026-10-03T11:00:00Z", "chain": CHAIN, "event": "status_changed",
               "phase": "development", "edge": "e-1", "from": "testable", "to": "proxied",
               "evidence": "results/e1.json"}]
    check("a documented status change passes", problems(events, EXISTING))
    check("an upgrade with no evidence fails",
          problems(events[:1] + [{**events[1], "to": "measured", "evidence": None}], EXISTING),
          expect_empty=False)
    check("an upgrade pointing at a missing file fails",
          problems(events[:1] + [{**events[1], "to": "measured", "evidence": "results/none.json"}],
                   EXISTING), expect_empty=False)

    edge = ev(status="proxied")
    sealed = {"ts": "2026-10-03T23:00:00Z", "chain": CHAIN, "event": "sealed_opened",
              "phase": "sealed", "revision": "abc123",
              "run_plan": "docs/chains/t-example-plan.md"}
    after = {"ts": "2026-10-04T10:00:00Z", "chain": CHAIN, "event": "status_changed",
             "phase": "sealed", "edge": "e-1", "from": "proxied", "to": "measured",
             "evidence": "results/e1.json"}
    check("no upgrade after the sealed window opens",
          problems([edge, sealed, after], EXISTING), expect_empty=False)
    check("a downgrade after the sealed window opens is allowed",
          problems([ev(status="measured", evidence="results/e1.json"), sealed,
                    {**after, "from": "measured", "to": "proxied"}], EXISTING))

    bound = {"ts": "2026-10-04T11:00:00Z", "chain": CHAIN, "event": "bound_changed",
             "phase": "sealed", "edge": "e-1", "from": "2% NAV", "to": "5% NAV",
             "reason": "conviction"}
    check("no bound increase after the sealed window opens",
          problems([ev(status="measured", evidence="results/e1.json"), sealed, bound], EXISTING),
          expect_empty=False)

    many = [ev(edge=f"e-{i}", status="measured", evidence="results/e1.json") for i in range(9)]
    check("the scope budget caps the number of active edges", problems(many, EXISTING),
          expect_empty=False)

    unmeasured = [ev(edge=f"e-{i}", status="testable") for i in range(4)]
    check("the scope budget caps unmeasured edges", problems(unmeasured, EXISTING),
          expect_empty=False)

    pnl = [ev(edge="e-a", mode="expression"), ev(edge="e-b", mode="hedge")]
    check("only one P&L carrying role in the pilot", problems(pnl, EXISTING), expect_empty=False)

    decisions = [ev(), {"ts": "2026-10-03T12:00:00Z", "chain": CHAIN, "event": "decision",
                        "phase": "development", "choice": "horizon", "value": "10 sessions",
                        "reason": "initial candidate"}]
    check("decisions are accepted and counted", problems(decisions, EXISTING))

    print(f"\n{16 - len(failures)}/16 passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
