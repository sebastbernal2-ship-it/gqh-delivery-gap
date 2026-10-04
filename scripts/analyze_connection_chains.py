#!/usr/bin/env python3
"""Surface candidate connection chains across layers of the quantgraph.

Walks the substantive edges (feeds, measures, observes, indicates, affects, governs, gates, derives,
supports, exposes, identifies, instantiates, makes available) between the complex's anchor nodes and
everything else, and writes every short path with each edge's declared condition and falsifier attached.
Structural edges (candidate_for, conditions, part_of, contains, belongs_to, has_field) are taxonomy and
are not walked; `conditions` edges are instead used to attach the assumption nodes that guard each node.

The output is raw material for the graded pass in docs/scan/connection-chains.jsonl, never a result.

    python3 scripts/analyze_connection_chains.py --manifest docs/scan/quantgraph.jsonl
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "docs" / "scan" / "connection-chain-candidates.json"
SUBSTANTIVE = {"feeds", "measures", "observes", "indicates", "affects", "governs", "gates",
               "derived_from", "supports", "tested_by", "exposes", "makes_available", "identifies",
               "instantiates"}
DEFAULT_ANCHORS = [
    "mechanism:delivery:revision-to-cash-flow",
    "mechanism:capacity:transformer-bottleneck",
    "mechanism:capacity:interconnection-bottleneck",
    "mechanism:capacity:cooling-bottleneck",
    "mechanism:capacity:labor-bottleneck",
    "feature:power:queue-age",
    "feature:revision:delivery-surprise",
    "entity:datacenter:site",
    "outcome:firm:cash-flow-revision",
]
MAX_DEPTH = 4
MAX_CANDIDATES = 400


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(ROOT / "docs" / "scan" / "quantgraph.jsonl"))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--anchors", nargs="*", default=DEFAULT_ANCHORS)
    args = parser.parse_args()

    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    for line in Path(args.manifest).open():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("kind") == "node":
            nodes[row["id"]] = {"id": row["id"], "layer": row.get("layer", "?"),
                                "meaning": row.get("meaning", "")}
        elif row.get("kind") == "edge":
            edges.append(row)

    assumptions: dict[str, list[str]] = collections.defaultdict(list)
    for edge in edges:
        if edge.get("relation") == "conditions" and edge["from"].startswith("assumption:"):
            assumptions[edge["to"]].append(edge["from"])

    adjacency: dict[str, list[tuple[str, dict]]] = collections.defaultdict(list)
    for edge in edges:
        if edge.get("relation") not in SUBSTANTIVE:
            continue
        if edge["from"] in nodes and edge["to"] in nodes:
            adjacency[edge["from"]].append((edge["to"], edge))
            adjacency[edge["to"]].append((edge["from"], edge))

    missing_anchors = [anchor for anchor in args.anchors if anchor not in nodes]
    candidates = []
    seen: set[tuple[str, ...]] = set()
    for anchor in args.anchors:
        if anchor not in nodes:
            continue
        queue: list[tuple[str, tuple[str, ...], tuple[dict, ...]]] = [(anchor, (anchor,), ())]
        while queue:
            current, path, path_edges = queue.pop(0)
            if len(path) - 1 >= MAX_DEPTH:
                continue
            for neighbor, edge in adjacency.get(current, []):
                if neighbor in path:
                    continue
                new_path = path + (neighbor,)
                new_edges = path_edges + (edge,)
                if len(new_path) > 2:
                    canonical = tuple(sorted(new_path))
                    if canonical not in seen:
                        seen.add(canonical)
                        layers = sorted({nodes[node]["layer"] for node in new_path})
                        if len(layers) >= 3:
                            candidates.append({"anchor": anchor, "path": list(new_path),
                                               "layers": layers, "links": list(new_edges)})
                if len(new_path) - 1 < MAX_DEPTH:
                    queue.append((neighbor, new_path, new_edges))

    def score(candidate: dict) -> tuple:
        layers = candidate["layers"]
        return (len(layers), "mechanism" in layers, "feature" in layers, -len(candidate["links"]))

    candidates.sort(key=score, reverse=True)
    candidates = candidates[:MAX_CANDIDATES]
    for candidate in candidates:
        candidate["nodes"] = [nodes[node] for node in candidate["path"]]
        candidate["links"] = [{"from": link["from"], "to": link["to"],
                               "relation": link.get("relation", ""), "status": link.get("status", ""),
                               "condition": link.get("condition", ""),
                               "falsifier": link.get("falsifier", "")} for link in candidate["links"]]
        candidate["assumptions"] = {node: assumptions[node] for node in candidate["path"]
                                    if assumptions.get(node)}
    manifest = Path(args.manifest)
    report = {
        "manifest": str(manifest.relative_to(ROOT)) if manifest.is_relative_to(ROOT) else str(manifest),
        "anchors": args.anchors,
        "missing_anchors": missing_anchors,
        "nodes": len(nodes),
        "substantive_edges": sum(1 for edge in edges if edge.get("relation") in SUBSTANTIVE),
        "candidates": len(candidates),
        "chains": candidates,
    }
    Path(args.out).write_text(json.dumps(report, indent=1) + "\n")
    print(f"wrote {args.out} ({len(candidates)} candidates, {len(nodes)} nodes)")
    for candidate in candidates[:8]:
        print("  ", " -> ".join(candidate["path"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
