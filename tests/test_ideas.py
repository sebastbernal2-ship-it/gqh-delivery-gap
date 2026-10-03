#!/usr/bin/env python3
"""Offline tests for the idea graph rules and its generated view."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from check_ideas import load, orphans, problems, summarise  # noqa: E402
from render_ideas import render  # noqa: E402

failures: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        failures.append(f"{name}: got {got!r}, want {want!r}")


def idea(idea_id: str, **extra) -> dict:
    base = {"kind": "idea", "id": idea_id, "name": idea_id.title(), "statement": "a statement",
            "family": "math", "status": "unattached", "reason": "not needed here"}
    base.update(extra)
    return base


def link(source: str, target: str, relation: str = "combines_with", note: str = "because") -> dict:
    return {"kind": "link", "from": source, "to": target, "relation": relation, "note": note}


GOOD = [idea("optimal-transport"), idea("monotone-maps"), link("optimal-transport", "monotone-maps")]
check("a well formed graph has no problems", problems(GOOD, set()), [])

check("a duplicate idea is caught", len(problems([idea("x-ray"), idea("x-ray")], set())) >= 1, True)
check("a malformed id is caught",
      any("lower case words" in p for p in problems([idea("XRay")], set())), True)
check("an idea with no statement is caught",
      any("no statement" in p for p in problems([idea("x-ray", statement="")], set())), True)
check("an unknown family is caught",
      any("is not one of" in p for p in problems([idea("x-ray", family="poetry")], set())), True)
check("an unattached idea without a reason is caught",
      any("just vocabulary" in p for p in problems([idea("x-ray", reason="")], set())), True)
check("an attachment to an undeclared node is caught",
      any("not a declared scan node" in p
          for p in problems([idea("x-ray", status="attached", attaches_to=["nope:nope:nope"],
                                  reason="")], {"real:node:here"})), True)
check("an attachment to a declared node passes",
      problems([idea("x-ray", status="attached", attaches_to=["real:node:here"], reason="")],
               {"real:node:here"}), [])
check("a link to an undeclared idea is caught",
      any("undeclared idea" in p for p in problems(GOOD + [link("optimal-transport", "ghost")], set())), True)
check("an unknown relation is caught",
      any("relation" in p and "not declared" in p
          for p in problems(GOOD + [link("optimal-transport", "monotone-maps", "is_friends_with")], set())), True)
check("a self link is caught",
      any("self link" in p for p in problems([idea("x-ray"), link("x-ray", "x-ray")], set())), True)
check("a duplicate symmetric link is caught in either direction",
      any("declared twice" in p
          for p in problems(GOOD + [link("monotone-maps", "optimal-transport")], set())), True)
check("a directed link may run both ways without being a duplicate",
      problems([idea("a-theory"), idea("b-idea"),
                link("a-theory", "b-idea", "requires"), link("b-idea", "a-theory", "requires")], set()), [])
check("a link with no note is caught",
      any("unexplained" in p
          for p in problems(GOOD + [link("optimal-transport", "monotone-maps", note="")], set())), True)

check("an orphan is reported", orphans(GOOD + [idea("lonely")]), ["lonely"])
check("a linked idea is not an orphan", orphans(GOOD), [])
text = summarise(GOOD + [idea("lonely")])
check("the summary counts ideas and links", "ideas: 3" in text and "links: 1" in text, True)
check("the summary reports ideas with no link", "ideas with no link yet: 1" in text, True)

view = render(GOOD)
check("the view is generated from the graph", "optimal-transport" in view, True)
check("the view says it is generated", "generated from it" in view, True)
check("a symmetric link is shown from both sides",
      view.count("combines with"), 2)
check("the view counts what is kept without an attachment", "kept without an attachment" in view, True)

def direction(direction_id: str, **extra) -> dict:
    base = {"kind": "direction", "id": direction_id, "name": "D", "statement": "s", "rationale": "r",
            "capacity": "c", "falsifier": "f", "status": "declared", "next": "n",
            "uses": ["optimal-transport"], "measures": ["real:node:here"], "needs": ["x"]}
    base.update(extra)
    return base


nodes = {"real:node:here"}
check("a well formed direction passes", problems(GOOD + [direction("a-direction")], nodes), [])
check("a direction missing its falsifier is caught",
      any("missing falsifier" in p for p in problems(GOOD + [direction("a-direction", falsifier="")], nodes)),
      True)
check("a direction with an unknown status is caught",
      any("is not one of" in p
          for p in problems(GOOD + [direction("a-direction", status="vibes")], nodes)), True)
check("a direction using an undeclared idea is caught",
      any("not a declared idea" in p
          for p in problems(GOOD + [direction("a-direction", uses=["ghost-idea"])], nodes)), True)
check("a direction measuring an undeclared node is caught",
      any("not a declared node" in p
          for p in problems(GOOD + [direction("a-direction", measures=["ghost:node:here"])], nodes)), True)
check("a direction counts as a link for orphan purposes",
      orphans(GOOD + [direction("a-direction")]), [])

real = load()
check("the real graph loads", len(real) > 50, True)
check("the real graph is clean", problems(real), [])
check("the real graph declares directions", len([r for r in real if r.get("kind") == "direction"]) >= 5, True)
check("the real view matches the real graph", render(real), (ROOT / "docs" / "ideas" / "README.md").read_text())

if failures:
    print("\n".join(f"  FAIL {f}" for f in failures))
    print(f"\n{27 - len(failures)}/27 passed")
    raise SystemExit(1)
print("\n27/27 passed")
