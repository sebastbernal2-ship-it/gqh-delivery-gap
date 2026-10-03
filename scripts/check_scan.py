#!/usr/bin/env python3
"""Check the scan node space before anything is measured.

Why this exists: an association scan fails in one specific way. It measures whatever pairs it happens to
have, ranks them, and reports the best one. That reports multiplicity as discovery.

So the rules here are about the space rather than the numbers:

1. **Every node declares a representation** with a clock and an availability rule, or it declares itself
   blocked with a reason. A node with neither is a label, and a label cannot be measured.
2. **Blocked nodes keep their blockers.** A missing series is a result worth recording, because it stops
   the scan from quietly measuring a smaller space than the note claims.
3. **Pairs are canonical and complete.** Every pair of declared nodes appears once, and the pair count is
   printed before any statistic, so multiplicity is stated rather than discovered later.

Run by `make check`.
"""
from __future__ import annotations

import itertools
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NODES = ROOT / "docs" / "scan" / "nodes.jsonl"
NODE_STATUS = ("populated", "thin", "blocked")
REPRESENTATION_FIELDS = ("kind", "source", "clock", "availability", "status", "blocker")
ID_PATTERN = re.compile(r"^[a-z0-9]+(?::[a-z0-9-]+){2}$")


def load(path: Path = NODES) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"{path} is missing. The scan needs a declared node space first")
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def problems(nodes: list[dict]) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for node in nodes:
        node_id = node.get("id", "")
        if not node_id:
            found.append("a node has no id")
            continue
        if node_id in seen:
            found.append(f"{node_id}: declared twice")
        seen.add(node_id)
        if not ID_PATTERN.match(node_id):
            found.append(f"{node_id}: id should read family:detail:detail")
        status = node.get("status")
        if status not in NODE_STATUS:
            found.append(f"{node_id}: status '{status}' is not one of {NODE_STATUS}")
        if not node.get("meaning"):
            found.append(f"{node_id}: no meaning, so nobody can tell what it measures")
        representations = node.get("representations") or []
        if not representations:
            found.append(f"{node_id}: no representation and no blocker, which is a label, not a node")
        for index, representation in enumerate(representations):
            for field in REPRESENTATION_FIELDS:
                if field not in representation:
                    found.append(f"{node_id} representation {index}: missing {field}")
            if representation.get("status") not in NODE_STATUS:
                found.append(f"{node_id} representation {index}: status "
                             f"'{representation.get('status')}' is not one of {NODE_STATUS}")
            if representation.get("status") in ("blocked", "thin") and not representation.get("blocker"):
                found.append(f"{node_id} representation {index}: blocked or thin with no blocker, "
                             "which hides why the series is missing")
        blocked = [r for r in representations if r.get("status") in ("blocked", "thin")]
        if status == "populated" and blocked:
            found.append(f"{node_id}: called populated but carries a blocked or thin representation")
        if status in ("blocked", "thin") and not blocked:
            found.append(f"{node_id}: called {status} with no blocked or thin representation to explain it")
    return found


def pairs(nodes: list[dict]) -> list[dict]:
    """Every declared pair once, in canonical order, with its coverage state."""
    by_id = {node["id"]: node for node in nodes}
    out = []
    for left, right in itertools.combinations(nodes, 2):
        a, b = left["id"], right["id"]
        if a > b:
            a, b = b, a
        blocked = []
        for node in (by_id[a], by_id[b]):
            if node.get("status") in ("blocked", "thin"):
                reasons = [r.get("blocker") for r in node.get("representations", [])
                           if r.get("blocker")]
                blocked.append(f"{node['id']}: {reasons[0] if reasons else 'no reason recorded'}")
        out.append({"a": a, "b": b,
                    "coverage": "blocked" if blocked else "measurable",
                    "reason": "; ".join(blocked)})
    return out


def summarise(nodes: list[dict], declared: list[dict]) -> str:
    measurable = [p for p in declared if p["coverage"] == "measurable"]
    blocked = [p for p in declared if p["coverage"] == "blocked"]
    lines = [f"nodes declared: {len(nodes)}",
             f"pairs declared: {len(declared)}   measurable: {len(measurable)}   "
             f"blocked: {len(blocked)}",
             "",
             "multiplicity is counted before any measurement: any statistic produced by the scan is one of "
             f"{len(measurable)} pairs, and that number belongs in every result line."]
    by_status: dict[str, list[str]] = {}
    for node in nodes:
        by_status.setdefault(node.get("status", "?"), []).append(node["id"])
    lines.append("")
    for status in NODE_STATUS:
        ids = by_status.get(status, [])
        lines.append(f"{status:10s} {len(ids):3d}  " + (", ".join(short(i) for i in ids) if ids else ""))
    return "\n".join(lines)


def short(node_id: str) -> str:
    return node_id.split(":", 1)[1]


def main() -> int:
    nodes = load()
    declared = pairs(nodes)
    print(summarise(nodes, declared))
    found = problems(nodes)
    if found:
        print("\nnode space problems:")
        for problem in found:
            print(f"  - {problem}")
        return 1
    print("\nnode space: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
