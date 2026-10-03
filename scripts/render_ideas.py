#!/usr/bin/env python3
"""Render the idea graph as a readable view. Generated, never edited by hand.

The graph is the owner of the ideas; this file is a view of it, so a change here is a change to the
graph. `--check` fails when the view and the graph disagree, which is how the view stays true.

Usage:
    python scripts/render_ideas.py            # write the view
    python scripts/render_ideas.py --check    # fail if it is out of date
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRAPH = ROOT / "docs" / "ideas" / "graph.jsonl"
VIEW = ROOT / "docs" / "ideas" / "README.md"

FAMILY_TITLES = {"math": "Mathematics", "method": "Methods", "theory": "Theory",
                 "system": "Systems", "measure": "Measures"}
DIRECTION_FIELDS = ("rationale", "capacity", "falsifier", "next")
RELATION_PHRASES = {"combines_with": "combines with", "analogous_to": "is analogous to",
                    "specializes": "specialises", "generalizes": "generalises",
                    "requires": "requires", "supplies_method_for": "supplies a method for",
                    "inspired_by": "is inspired by"}
STATUS_NOTES = {"attached": "attached", "plausible": "plausible, gated",
                "unattached": "kept without an attachment"}


def load() -> list[dict]:
    return [json.loads(line) for line in GRAPH.read_text().splitlines() if line.strip()]


def render(rows: list[dict]) -> str:
    ideas = {row["id"]: row for row in rows if row.get("kind") == "idea"}
    links: dict[str, list[str]] = {}
    for row in rows:
        if row.get("kind") != "link":
            continue
        phrase = RELATION_PHRASES.get(row["relation"], row["relation"])
        links.setdefault(row["from"], []).append(f"{phrase} `{row['to']}`")
        if row["relation"] == "combines_with":
            links.setdefault(row["to"], []).append(f"{phrase} `{row['from']}`")

    out = ["# The idea graph",
           "",
           "Abstract ideas, kept because they are worth keeping, with the connections between them and an",
           "honest label on whether each one touches anything we measure. The graph is",
           "`graph.jsonl`; this file is generated from it by `make ideas`, so do not edit it by hand.",
           "",
           f"**{len(ideas)} ideas, "
           f"{sum(1 for r in rows if r.get('kind') == 'link')} links.** "
           f"{sum(1 for i in ideas.values() if i.get('attaches_to'))} name something in the study. "
           f"{sum(1 for i in ideas.values() if i.get('reason'))} are kept without an attachment, each with a "
           "stated reason, because a graph of only useful things is not a graph of ideas.",
           ""]
    directions = [row for row in rows if row.get("kind") == "direction"]
    if directions:
        out.append("## Directions: where an edge could actually live")
        out.append("")
        out.append("An idea is a tool. A direction is a program, so each one carries who pays, why it "
                   "persists, what it would run on, and what would kill it.")
        out.append("")
        for direction in sorted(directions, key=lambda d: d["name"]):
            out.append(f"### {direction['name']}")
            out.append("")
            out.append(f"{direction['statement']}.")
            out.append("")
            out.append(f"- **status**: {direction['status']}")
            out.append(f"- **rationale**: {direction['rationale']}")
            if direction.get("needs"):
                out.append(f"- **needs**: {'; '.join(direction['needs'])}")
            out.append(f"- **capacity**: {direction['capacity']}")
            out.append(f"- **falsifier**: {direction['falsifier']}")
            out.append(f"- **next**: {direction['next']}")
            out.append(f"- **uses**: {', '.join(f'`{u}`' for u in direction.get('uses', []))}")
            out.append(f"- **measures**: {', '.join(f'`{m.split(chr(58), 1)[1]}`' for m in direction.get('measures', []))}")
            out.append("")
    by_family: dict[str, list[dict]] = {}
    for idea in ideas.values():
        by_family.setdefault(idea.get("family", "?"), []).append(idea)
    for family in sorted(by_family, key=lambda f: FAMILY_TITLES.get(f, f)):
        out.append(f"## {FAMILY_TITLES.get(family, family)}")
        out.append("")
        for idea in sorted(by_family[family], key=lambda i: i["name"]):
            status = STATUS_NOTES.get(idea.get("status"), idea.get("status", ""))
            out.append(f"### {idea['name']}")
            out.append("")
            out.append(f"{idea['statement']}. *{status}.*")
            out.append("")
            if idea.get("attaches_to"):
                targets = ", ".join(f"`{name.split(':', 1)[1]}`" for name in idea["attaches_to"])
                out.append(f"- touches: {targets}")
            if idea.get("reason"):
                out.append(f"- kept without an attachment: {idea['reason']}")
            for line in sorted(set(links.get(idea["id"], []))):
                out.append(f"- {line}")
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    text = render(load())
    if args.check:
        current = VIEW.read_text() if VIEW.exists() else ""
        if current != text:
            print("docs/ideas/README.md is out of date. Run: python scripts/render_ideas.py")
            return 1
        print("the idea view matches the graph")
        return 0
    VIEW.write_text(text)
    print(f"wrote {VIEW.relative_to(ROOT)} ({len(text.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
