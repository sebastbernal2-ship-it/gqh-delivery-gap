#!/usr/bin/env python3
"""Decompose every manifest node into its sub-nodes and split edges.

Applies the sub-node law in docs/plan/decomposition.md: six children per node along layer-specific
dimensions, then five more per child. The output is a skeleton, every row marked
`proposed_unverified`, so it can be audited and replaced by curated digs dig by dig.

Writes docs/scan/decomposition.jsonl.gz and docs/scan/decomposition-summary.json.

    python3 scripts/decompose_graph.py --manifest docs/scan/quantgraph.jsonl
"""
from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "docs" / "scan" / "decomposition.jsonl.gz"
DEFAULT_SUMMARY = ROOT / "docs" / "scan" / "decomposition-summary.json"

TEMPLATES: dict[str, list[str]] = {
    "source": ["access path", "update cadence", "revision behavior", "entity key",
               "point-in-time guarantee", "licensing"],
    "dataset": ["schema", "coverage universe", "clock", "vintage archive", "join keys",
                "missingness pattern"],
    "feature": ["construction inputs", "measurement clock", "normalization", "lookahead risk",
                "stability", "economic meaning"],
    "mechanism": ["trigger", "transmission path", "rate limiter", "observable", "lag profile",
                  "payer incidence"],
    "factor": ["measurement proxy", "horizon", "conditioning state", "transmission", "crowding",
               "payer incidence"],
    "entity": ["legal structure", "segment mapping", "identifiers", "exposure map", "counterparties",
               "disclosure clock"],
    "asset": ["instrument mechanics", "liquidity", "borrow and short constraints", "option surface",
              "credit terms", "financing"],
    "outcome": ["measurement window", "benchmark", "sign convention", "accounting bridge",
                "revision behavior", "falsifier"],
    "event": ["detection rule", "timestamp source", "confirmation lag", "agenda ambiguity",
              "clustering", "placebo design"],
    "assumption": ["test design", "failure mode", "blast radius", "owner", "monitoring cadence",
                   "kill threshold"],
    "claim": ["mechanism link", "evidence requirement", "null", "multiplicity", "horizon",
              "cost ceiling"],
    "experiment": ["design", "sample", "power", "null", "placebo", "stopping rule"],
    "evidence": ["provenance", "extraction method", "precision", "timestamp", "source agreement",
                 "decay"],
    "rule": ["statement", "scope", "override", "enforcement point", "violation handling",
             "audit trail"],
    "contract": ["obligation", "trigger", "notice", "penalty", "assignment", "term"],
    "strategy": ["signal", "sizing", "costs", "capacity", "kill switch", "funding"],
    "implementation": ["interface", "state", "failure mode", "test", "observability", "rollout"],
    "raw": ["origin", "format", "units", "entity key", "time key", "quality flags"],
}
GENERIC = ["composition", "inputs", "constraints", "observables", "substitutes", "payers"]
DIMENSION_LAYER = {
    "composition": "raw", "inputs": "raw", "substitutes": "raw",
    "constraints": "mechanism", "rate limiter": "mechanism", "transmission": "mechanism",
    "transmission path": "mechanism", "trigger": "event", "lag profile": "mechanism",
    "observable": "feature", "observables": "feature", "measurement clock": "feature",
    "measurement proxy": "feature", "detection rule": "feature", "timestamp source": "feature",
    "payer incidence": "entity", "payers": "entity", "kill threshold": "rule",
    "kill switch": "rule", "stopping rule": "rule", "null": "experiment",
}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def child_of(parent: dict, dimension: str) -> dict:
    child_id = f"sub:{parent['id']}:{slug(dimension)}"
    layer = DIMENSION_LAYER.get(dimension, parent.get("layer", "?"))
    return {
        "kind": "subnode",
        "id": child_id,
        "parent": parent["id"],
        "dimension": dimension,
        "layer": layer,
        "meaning": f"the {dimension} of {parent.get('meaning', parent['id'])[:60]}",
        "status": "proposed_unverified",
        "ask": f"verify the {dimension} of {parent['id']}",
        "tie_to": [parent["id"]],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(ROOT / "docs" / "scan" / "quantgraph.jsonl"))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    args = parser.parse_args()

    nodes = []
    for line in Path(args.manifest).open():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("kind") == "node":
            nodes.append(row)

    rows: list[dict] = []
    level1 = 0
    level2 = 0
    for node in nodes:
        dimensions = TEMPLATES.get(node.get("layer", ""), GENERIC)
        for dimension in dimensions:
            first = child_of(node, dimension)
            rows.append(first)
            level1 += 1
            rows.append({"kind": "split", "id": f"split:{first['id']}", "from": node["id"],
                         "to": first["id"], "relation": "splits_into", "status": "proposed"})
            for deeper in GENERIC[:5]:
                second = child_of(first, deeper)
                rows.append(second)
                level2 += 1
                rows.append({"kind": "split", "id": f"split:{second['id']}", "from": first["id"],
                             "to": second["id"], "relation": "splits_into", "status": "proposed"})

    curated = 0
    curated_level1 = 0
    curated_level2 = 0
    digs_path = ROOT / "docs" / "scan" / "deep-digs.jsonl"
    if digs_path.exists():
        for line in digs_path.open():
            if not line.strip():
                continue
            dig = json.loads(line)
            for node in dig.get("nodes", []):
                curated += 1
                curated_node = {"id": node["id"], "layer": node.get("layer", "raw"),
                                "meaning": node.get("meaning", node["id"])}
                for dimension in GENERIC:
                    first = child_of(curated_node, dimension)
                    first["status"] = "seeded_parent"
                    rows.append(first)
                    curated_level1 += 1
                    rows.append({"kind": "split", "id": f"split:{first['id']}", "from": node["id"],
                                 "to": first["id"], "relation": "splits_into", "status": "proposed"})
                    for deeper in GENERIC[:5]:
                        second = child_of(first, deeper)
                        second["status"] = "seeded_parent"
                        rows.append(second)
                        curated_level2 += 1
                        rows.append({"kind": "split", "id": f"split:{second['id']}", "from": first["id"],
                                     "to": second["id"], "relation": "splits_into",
                                     "status": "proposed"})

    import gzip
    out = args.out if args.out.endswith(".gz") else args.out + ".gz"
    with gzip.open(out, "wt") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":")) + "\n")

    by_layer = collections.Counter(row["layer"] for row in rows if row["kind"] == "subnode")
    by_dimension = collections.Counter(row["dimension"] for row in rows if row["kind"] == "subnode")
    summary = {
        "manifest_nodes": len(nodes),
        "level1_children": level1,
        "level2_children": level2,
        "subnodes_total": level1 + level2,
        "split_edges": level1 + level2,
        "written_graph_total": len(nodes) + level1 + level2,
        "curated_dig_nodes": curated,
        "curated_children": curated_level1 + curated_level2,
        "written_total_with_curated": len(nodes) + level1 + level2 + curated_level1 + curated_level2,
        "children_per_parent_min": min(len(TEMPLATES.get(node.get("layer", ""), GENERIC))
                                       for node in nodes),
        "by_layer": dict(by_layer.most_common()),
        "by_dimension": dict(by_dimension.most_common(20)),
        "status": "proposed_unverified skeleton; curated depth lives in deep-digs.jsonl",
    }
    Path(args.summary).write_text(json.dumps(summary, indent=1) + "\n")
    print(f"wrote {args.out} and {args.summary}")
    print(f"manifest {len(nodes)} nodes -> {level1} children -> {level2} grandchildren; "
          f"{len(nodes) + level1 + level2} nodes written in total, {level1 + level2} split edges")
    print(f"curated dig nodes {curated} -> {curated_level1} children -> {curated_level2} grandchildren; "
          f"written total with curated: {len(nodes) + level1 + level2 + curated_level1 + curated_level2}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
