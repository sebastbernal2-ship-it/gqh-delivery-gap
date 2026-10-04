#!/usr/bin/env python3
"""Validate the measured crosswalk and generated decomposition counts."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "docs" / "scan" / "nodes.jsonl"
MANIFEST = ROOT / "docs" / "scan" / "quantgraph.jsonl"
CROSSWALK = ROOT / "docs" / "scan" / "node-crosswalk.jsonl"
DECOMPOSITION = ROOT / "docs" / "scan" / "decomposition.jsonl.gz"
SUMMARY = ROOT / "docs" / "scan" / "decomposition-summary.json"

CROSSWALK_STATUSES = {"mapped", "proposed_alias", "unmapped"}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def read_gzip_jsonl(path: Path) -> list[dict]:
    with gzip.open(path, "rt") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def crosswalk_problems(registry: Iterable[dict], manifest: Iterable[dict], rows: Iterable[dict]) -> list[str]:
    """Return structural errors in the measured-to-manifest crosswalk."""
    problems: list[str] = []
    registry_ids = {row.get("id", "") for row in registry}
    manifest_ids = {row.get("id", "") for row in manifest if row.get("kind") == "node"}
    seen: set[str] = set()

    for row in rows:
        node = row.get("node", "")
        label = node or "(row without a node)"
        if node not in registry_ids:
            problems.append(f"{label}: crosswalk node is not in the measured registry")
        if node in seen:
            problems.append(f"{label}: duplicate crosswalk row")
        seen.add(node)
        status = row.get("status")
        if status not in CROSSWALK_STATUSES:
            problems.append(f"{label}: status {status!r} is not one of {sorted(CROSSWALK_STATUSES)}")
        if not row.get("relation"):
            problems.append(f"{label}: crosswalk relation is empty")
        if not row.get("rationale"):
            problems.append(f"{label}: crosswalk rationale is empty")
        targets = row.get("manifest_ids", [])
        if not isinstance(targets, list):
            problems.append(f"{label}: manifest_ids must be a list")
            targets = []
        for target in targets:
            if target not in manifest_ids:
                problems.append(f"{label}: manifest id does not exist: {target}")
        if status == "unmapped" and targets:
            problems.append(f"{label}: unmapped row cannot have manifest targets")
        if status in {"mapped", "proposed_alias"} and not targets:
            problems.append(f"{label}: {status} row needs a manifest target")

    missing = sorted(registry_ids - seen)
    problems.extend(f"{node}: missing crosswalk row" for node in missing)
    extra = sorted(seen - registry_ids)
    problems.extend(f"{node}: crosswalk row is not a measured node" for node in extra)
    return problems


def decomposition_problems(manifest_nodes: int | Iterable[dict], rows: Iterable[dict], summary: dict) -> list[str]:
    """Return count mismatches between the compressed graph and its summary."""
    if isinstance(manifest_nodes, int):
        manifest_count = manifest_nodes
    else:
        manifest_count = sum(1 for row in manifest_nodes if row.get("kind") == "node")
    rows = list(rows)
    subnodes = sum(1 for row in rows if row.get("kind") == "subnode")
    split_edges = sum(1 for row in rows if row.get("kind") == "split")
    expected = {
        "manifest_nodes": manifest_count,
        "subnodes_total": subnodes,
        "split_edges": split_edges,
        "written_graph_total": manifest_count + subnodes,
    }
    problems: list[str] = []
    for key, value in expected.items():
        if summary.get(key) != value:
            problems.append(f"{key}: summary has {summary.get(key)!r}, generated graph has {value!r}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", default=str(REGISTRY))
    parser.add_argument("--manifest", default=str(MANIFEST))
    parser.add_argument("--crosswalk", default=str(CROSSWALK))
    parser.add_argument("--decomposition", default=str(DECOMPOSITION))
    parser.add_argument("--summary", default=str(SUMMARY))
    args = parser.parse_args()

    registry = read_jsonl(Path(args.registry))
    manifest = read_jsonl(Path(args.manifest))
    problems: list[str] = []
    crosswalk_path = Path(args.crosswalk)
    if not crosswalk_path.exists():
        problems.append(f"crosswalk file does not exist: {crosswalk_path}")
    else:
        problems.extend(crosswalk_problems(registry, manifest, read_jsonl(crosswalk_path)))

    decomposition_path = Path(args.decomposition)
    summary_path = Path(args.summary)
    if not decomposition_path.exists():
        problems.append(f"decomposition file does not exist: {decomposition_path}")
    elif not summary_path.exists():
        problems.append(f"decomposition summary does not exist: {summary_path}")
    else:
        problems.extend(decomposition_problems(
            manifest, read_gzip_jsonl(decomposition_path), json.loads(summary_path.read_text())))

    if problems:
        print("\n".join(f"  FAIL {problem}" for problem in problems))
        return 1
    manifest_nodes = sum(1 for row in manifest if row.get("kind") == "node")
    print(f"scan artifacts clean: {len(registry)} measured nodes, {manifest_nodes} manifest nodes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
