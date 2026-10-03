#!/usr/bin/env python3
"""Checks the cross-layer QuantGraph manifest before data ingestion."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from check_quantgraph_manifest import load, problems  # noqa: E402


rows = load()
found = problems(rows)
if found:
    raise SystemExit("\n".join(f"  FAIL {problem}" for problem in found))

nodes = [row for row in rows if row.get("kind") == "node"]
edges = [row for row in rows if row.get("kind") == "edge"]
expected_layers = {
    "source", "dataset", "raw", "feature", "entity", "event", "mechanism",
    "assumption", "outcome", "claim", "strategy", "rule", "evidence", "experiment",
    "implementation", "concept", "asset", "factor", "contract",
}
actual_layers = {row["layer"] for row in nodes}
if not expected_layers <= actual_layers:
    raise SystemExit(f"missing graph layers: {sorted(expected_layers - actual_layers)}")
if len(nodes) < 40:
    raise SystemExit(f"manifest is too small: {len(nodes)} nodes")
if len(edges) < 40:
    raise SystemExit(f"manifest is too small: {len(edges)} edges")
print(f"quantgraph manifest clean: {len(nodes)} nodes, {len(edges)} edges")
