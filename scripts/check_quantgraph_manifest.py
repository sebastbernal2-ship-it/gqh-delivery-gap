#!/usr/bin/env python3
"""Validate the cross-layer QuantGraph declaration before data ingestion."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "docs" / "scan" / "quantgraph.jsonl"
LAYERS = {
    "source", "dataset", "raw", "feature", "entity", "event", "mechanism",
    "assumption", "outcome", "claim", "strategy", "rule", "evidence", "experiment",
    "implementation", "concept", "asset", "factor", "contract",
}
STATUSES = {"declared", "proposed", "blocked", "measured", "supported"}
ID_PATTERN = re.compile(r"^[a-z0-9]+(?::[a-z0-9-]+){2,}$")


def load(path: Path = MANIFEST) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"{path} is missing")
    rows: list[dict] = []
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise SystemExit(f"line {line_number}: invalid JSON: {error}") from error
        row["_line"] = line_number
        rows.append(row)
    return rows


def problems(rows: list[dict]) -> list[str]:
    found: list[str] = []
    nodes = [row for row in rows if row.get("kind") == "node"]
    edges = [row for row in rows if row.get("kind") == "edge"]
    if len(nodes) + len(edges) != len(rows):
        found.append("every row must have kind 'node' or 'edge'")

    node_ids: set[str] = set()
    for row in nodes:
        node_id = row.get("id", "")
        if not node_id:
            found.append(f"line {row['_line']}: node has no id")
            continue
        if node_id in node_ids:
            found.append(f"{node_id}: declared twice")
        node_ids.add(node_id)
        if not ID_PATTERN.match(node_id):
            found.append(f"{node_id}: id must contain at least three colon-separated parts")
        if row.get("layer") not in LAYERS:
            found.append(f"{node_id}: unknown layer {row.get('layer')!r}")
        if not row.get("type"):
            found.append(f"{node_id}: no type")
        if not row.get("meaning"):
            found.append(f"{node_id}: no meaning")
        if row.get("status") not in STATUSES:
            found.append(f"{node_id}: unknown status {row.get('status')!r}")
        if not row.get("unit"):
            found.append(f"{node_id}: no unit or 'not applicable' declaration")
        if not row.get("availability"):
            found.append(f"{node_id}: no availability rule")
        if not row.get("sources"):
            found.append(f"{node_id}: no source or 'none' declaration")
        if not row.get("roles"):
            found.append(f"{node_id}: no graph role")
        if not row.get("falsifier"):
            found.append(f"{node_id}: no falsifier")
        if row.get("status") == "blocked" and not row.get("blocker"):
            found.append(f"{node_id}: blocked without a blocker")

    edge_ids: set[str] = set()
    used: set[str] = set()
    for row in edges:
        edge_id = row.get("id", "")
        if not edge_id:
            found.append(f"line {row['_line']}: edge has no id")
        elif edge_id in edge_ids:
            found.append(f"{edge_id}: declared twice")
        edge_ids.add(edge_id)
        source, target = row.get("from"), row.get("to")
        if source not in node_ids:
            found.append(f"{edge_id}: unknown from node {source!r}")
        if target not in node_ids:
            found.append(f"{edge_id}: unknown to node {target!r}")
        if source == target:
            found.append(f"{edge_id}: self edge")
        used.update(value for value in (source, target) if value)
        for field in ("relation", "status", "condition", "falsifier"):
            if not row.get(field):
                found.append(f"{edge_id}: no {field}")
        if row.get("status") not in STATUSES:
            found.append(f"{edge_id}: unknown status {row.get('status')!r}")

    for node_id in sorted(node_ids - used):
        found.append(f"{node_id}: orphan node; connect it or remove it")
    return found


if __name__ == "__main__":
    rows = load()
    found = problems(rows)
    if found:
        for problem in found:
            print(f"- {problem}")
        raise SystemExit(1)
    nodes = sum(row.get("kind") == "node" for row in rows)
    edges = sum(row.get("kind") == "edge" for row in rows)
    print(f"quantgraph manifest clean: {nodes} nodes, {edges} edges")
