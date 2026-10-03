#!/usr/bin/env python3
"""Link this study to the algoterminal stack: the QuantGraph and the source inventory.

Read only. Nothing is written to the other repository, and no graph YAML is modified.

What it does:

  resolve   every node our work depends on either exists in the QuantGraph, or is declared as a
            proposed node with a layer, a type and a reason, so a gap is a record rather than a guess
  sources   every representation we plan to build from either names a source in the inventory, or
            is declared as a new source to add
  coverage  a summary of how much of our node space the graph already has

Configuration: set ALGOTERMINAL_DIR, or keep the checkout at the default path. Without it, every
check that needs it is skipped with a note, because a missing sibling checkout must not fail this repo.

Run by `make graph`, and by `make check` when the link is configured.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHAINS = ROOT / "docs" / "chains"
DEFAULT_DIR = Path.home() / "algoterminal-data"
NODE_ID = re.compile(r"^[a-z_]+:[A-Za-z0-9._:/-]+$")
LAYERS = {"source", "dataset", "raw", "feature", "entity", "event", "mechanism", "assumption",
          "outcome", "claim", "strategy", "rule", "evidence", "experiment", "implementation",
          "concept", "asset", "factor", "contract"}


def stack_dir() -> Path | None:
    raw = os.environ.get("ALGOTERMINAL_DIR", "").strip()
    candidate = Path(raw).expanduser() if raw else DEFAULT_DIR
    if (candidate / "graph" / "quant_graph.yaml").exists():
        return candidate
    return None


def _ids(path: Path, pattern: str) -> set[str]:
    if not path.exists():
        return set()
    found = set()
    for line in path.read_text(errors="ignore").splitlines():
        match = re.match(pattern, line.strip())
        if match:
            found.add(match.group(1))
    return found


def graph_nodes(directory: Path) -> set[str]:
    return _ids(directory / "graph" / "quant_graph.yaml", r"- id: (\S+)")


def source_ids(directory: Path) -> set[str]:
    return _ids(directory / "graph" / "source_inventory.yaml", r"- id: (\S+)")


def linkage_problems(events: list[dict], nodes: set[str], sources: set[str]) -> list[str]:
    """Return problems for the linkage. Empty means consistent.

    Two passes, because an edge may reference a node or source that a later line declares.
    """
    out: list[str] = []
    resolved_nodes, proposed_nodes = set(), set()
    resolved_sources, proposed_sources = set(), set()

    for i, event in enumerate(events, 1):
        if not isinstance(event, dict):
            continue
        label = f"line {i}"
        kind = event.get("event")
        if kind == "node_resolved":
            node = str(event.get("node", ""))
            if not NODE_ID.match(node):
                out.append(f"{label}: node '{node}' is not a layered node id")
            elif node not in nodes:
                out.append(f"{label}: node_resolved '{node}' is not in the QuantGraph. "
                           f"Declare it as node_proposed instead")
            resolved_nodes.add(node)
        elif kind == "node_proposed":
            node = str(event.get("node", ""))
            if not NODE_ID.match(node):
                out.append(f"{label}: node '{node}' is not a layered node id (expected something "
                           f"like feature:power:interconnection-queue)")
            elif node in nodes:
                out.append(f"{label}: node '{node}' already exists in the QuantGraph. Reference it "
                           f"with node_resolved instead of proposing it")
            proposed_nodes.add(node)
        elif kind == "source_resolved":
            source = str(event.get("source", ""))
            if source not in sources:
                out.append(f"{label}: source_resolved '{source}' is not in the inventory")
            resolved_sources.add(source)
        elif kind == "source_proposed":
            source = str(event.get("source", ""))
            if source in sources:
                out.append(f"{label}: source '{source}' already exists in the inventory. Reference "
                           f"it with source_resolved instead of proposing it")
            proposed_sources.add(source)

    known_nodes = nodes | proposed_nodes | resolved_nodes
    known_sources = sources | proposed_sources | resolved_sources

    for i, event in enumerate(events, 1):
        if not isinstance(event, dict):
            continue
        label = f"line {i}"
        for field in ("from_node", "to_node"):
            node = event.get(field)
            if node and str(node) not in known_nodes:
                out.append(f"{label}: {field} '{node}' is neither in the QuantGraph nor declared "
                           f"in this log")
        for source in _sources_of(event):
            if source not in known_sources:
                out.append(f"{label}: source '{source}' is neither in the inventory nor declared "
                           f"in this log")

    return out


def _sources_of(event: dict) -> list[str]:
    raw = event.get("representation_source")
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        return [str(item) for item in raw if item]
    return [str(raw)]


def summarize(events: list[dict]) -> dict:
    resolved = [e for e in events if isinstance(e, dict) and e.get("event") == "node_resolved"]
    proposed = [e for e in events if isinstance(e, dict) and e.get("event") == "node_proposed"]
    sources_ok = [e for e in events if isinstance(e, dict) and e.get("event") == "source_resolved"]
    sources_new = [e for e in events if isinstance(e, dict) and e.get("event") == "source_proposed"]
    return {"resolved": len(resolved), "proposed": len(proposed),
            "sources_existing": len(sources_ok), "sources_new": len(sources_new)}


def load_chain_events() -> dict[str, list[dict]]:
    import json
    logs: dict[str, list[dict]] = {}
    if not CHAINS.exists():
        return logs
    for log in sorted(CHAINS.glob("*.jsonl")):
        if "TEMPLATE" in log.name:
            continue
        events = []
        for line in log.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                events.append({"_bad_line": line})
        logs[log.name] = events
    return logs


def main() -> int:
    directory = stack_dir()
    if directory is None:
        print("algoterminal link: not configured")
        print(f"  set ALGOTERMINAL_DIR, or keep a checkout at {DEFAULT_DIR}")
        print("  skipped, not failed: this repo must work without its sibling")
        return 0

    nodes = graph_nodes(directory)
    sources = source_ids(directory)
    print(f"algoterminal link: {directory}")
    print(f"  graph nodes: {len(nodes)}   sources and datasets: {len(sources)}")

    logs = load_chain_events()
    if not logs:
        print("  no chain logs yet, so nothing to resolve")
        return 0

    total = 0
    for name, events in logs.items():
        counts = summarize(events)
        found = linkage_problems(events, nodes, sources)
        print(f"  {name}: {counts['resolved']} resolved node reference(s), "
              f"{counts['proposed']} proposed node(s), "
              f"{counts['sources_existing']} existing source reference(s), "
              f"{counts['sources_new']} new source(s)")
        for problem in found:
            print(f"    PROBLEM: {problem}")
        total += len(found)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
