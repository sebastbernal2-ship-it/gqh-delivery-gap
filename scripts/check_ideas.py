#!/usr/bin/env python3
"""Keep the idea graph navigable and honest.

The graph exists to hold abstract ideas, including ones with no use yet, because that is what makes it
worth keeping. So the rules are about integrity rather than usefulness:

1. Every idea is a node with a one line statement, a family and a status.
2. Every link names two declared ideas and a relation from the declared vocabulary.
3. A symmetric relation cannot be declared twice in two directions, and a directed one cannot be a
   self loop.
4. An idea that claims to attach to the study must name a node that exists in the scan node space.
5. An idea that does not attach must say why, in one line. That is what stops the graph becoming a pile
   of unexplained vocabulary.

Orphans are reported, not refused: a graph grows one idea at a time.

Run by `make check`.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRAPH = ROOT / "docs" / "ideas" / "graph.jsonl"
NODES = ROOT / "docs" / "scan" / "nodes.jsonl"

FAMILIES = ("math", "method", "theory", "system", "measure")
DIRECTION_STATUSES = ("declared", "data-blocked", "collecting", "running", "built", "falsified")
DIRECTION_FIELDS = ("name", "statement", "rationale", "capacity", "falsifier", "status", "next")
STATUSES = ("attached", "plausible", "unattached")
SYMMETRIC = ("combines_with", "analogous_to")
DIRECTED = ("specializes", "generalizes", "requires", "supplies_method_for", "inspired_by")
RELATIONS = SYMMETRIC + DIRECTED
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def load(path: Path = GRAPH) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"{path} is missing. The idea graph has no owner file")
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def scan_node_ids(path: Path = NODES) -> set[str]:
    if not path.exists():
        return set()
    return {json.loads(line)["id"] for line in path.read_text().splitlines() if line.strip()}


def problems(rows: list[dict], node_ids: set[str] | None = None) -> list[str]:
    node_ids = node_ids if node_ids is not None else scan_node_ids()
    found: list[str] = []
    declared = [row for row in rows if row.get("kind") == "idea"]
    # Duplicates are counted on the list, before the dict is built: a dict would silently keep the last
    # declaration and a doubled id would pass unnoticed, which is exactly what a test caught.
    counts: dict[str, int] = {}
    for row in declared:
        counts[row.get("id", "")] = counts.get(row.get("id", ""), 0) + 1
    for idea_id, count in counts.items():
        if count > 1:
            found.append(f"{idea_id}: declared {count} times")
    ideas = {row["id"]: row for row in declared}
    for idea_id, idea in ideas.items():
        if not ID_PATTERN.match(idea_id):
            found.append(f"{idea_id}: id should be lower case words separated by hyphens")
        if not idea.get("statement"):
            found.append(f"{idea_id}: no statement, so the name is all it has")
        if idea.get("family") not in FAMILIES:
            found.append(f"{idea_id}: family '{idea.get('family')}' is not one of {FAMILIES}")
        if idea.get("status") not in STATUSES:
            found.append(f"{idea_id}: status '{idea.get('status')}' is not one of {STATUSES}")
        if idea.get("attaches_to"):
            unknown = [n for n in idea["attaches_to"] if n not in node_ids]
            for name in unknown:
                found.append(f"{idea_id}: attaches to '{name}', which is not a declared scan node")
        if idea.get("status") == "unattached" and not idea.get("reason"):
            found.append(f"{idea_id}: unattached with no reason, which is just vocabulary")
        if idea.get("status") == "attached" and idea.get("attaches_to") and not idea.get("statement"):
            found.append(f"{idea_id}: claims attachment without a statement")

    # Directions are the programs: an idea is a tool, a direction has a rationale, a falsifier and a data
    # requirement. They must reference ideas that exist and nodes that exist, so nothing floats free.
    for row in rows:
        if row.get("kind") != "direction":
            continue
        direction = row.get("id", "")
        for field in DIRECTION_FIELDS:
            if not row.get(field):
                found.append(f"direction {direction}: missing {field}")
        if row.get("status") not in DIRECTION_STATUSES:
            found.append(f"direction {direction}: status '{row.get('status')}' is not one of "
                         f"{DIRECTION_STATUSES}")
        for idea_id in row.get("uses", []):
            if idea_id not in ideas:
                found.append(f"direction {direction}: uses '{idea_id}', which is not a declared idea")
        for node_id in row.get("measures", []):
            if node_id not in node_ids:
                found.append(f"direction {direction}: measures '{node_id}', which is not a declared node")

    seen_links: set[tuple] = set()
    for row in rows:
        if row.get("kind") != "link":
            continue
        source, target, relation = row.get("from"), row.get("to"), row.get("relation")
        for name, value in (("from", source), ("to", target)):
            if value not in ideas:
                found.append(f"link {source} -> {target}: {name} names an undeclared idea")
        if relation not in RELATIONS:
            found.append(f"link {source} -> {target}: relation '{relation}' is not declared")
        if source == target:
            found.append(f"link {source} -> {target}: a self link says nothing")
        if relation in SYMMETRIC:
            key = tuple(sorted((str(source), str(target)))) + (str(relation),)
        else:
            key = (str(source), str(target), str(relation))
        if key in seen_links:
            found.append(f"link {source} -> {target} ({relation}): declared twice")
        seen_links.add(key)
        if not row.get("note"):
            found.append(f"link {source} -> {target}: no note, so the relation is unexplained")
    return found


def orphans(rows: list[dict]) -> list[str]:
    linked = set()
    for row in rows:
        if row.get("kind") == "direction":
            linked.update(row.get("uses", []))
        if row.get("kind") == "link":
            linked.add(row.get("from"))
            linked.add(row.get("to"))
    return [row["id"] for row in rows if row.get("kind") == "idea" and row["id"] not in linked]


def summarise(rows: list[dict]) -> str:
    ideas = [row for row in rows if row.get("kind") == "idea"]
    links = [row for row in rows if row.get("kind") == "link"]
    directions = [row for row in rows if row.get("kind") == "direction"]
    attached = [i for i in ideas if i.get("attaches_to")]
    lines = [f"ideas: {len(ideas)}   links: {len(links)}",
             f"ideas that name something in the study: {len(attached)}",
             f"ideas kept without an attachment, with a stated reason: "
             f"{sum(1 for i in ideas if i.get('reason'))}"]
    by_family: dict[str, int] = {}
    for idea in ideas:
        by_family[idea.get("family", "?")] = by_family.get(idea.get("family", "?"), 0) + 1
    lines.append("families: " + ", ".join(f"{k} {v}" for k, v in sorted(by_family.items())))
    stray = orphans(rows)
    lines.append(f"ideas with no link yet: {len(stray)}" + (f" ({', '.join(stray[:6])})" if stray else ""))
    lines.append(f"directions: {len(directions)}")
    for direction in directions:
        lines.append(f"  {direction.get('status', '?'):13s} {direction.get('id', '?')}")
    return "\n".join(lines)


def main() -> int:
    rows = load()
    print(summarise(rows))
    found = problems(rows)
    if found:
        print("\nidea graph problems:")
        for problem in found:
            print(f"  - {problem}")
        return 1
    print("\nidea graph: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
