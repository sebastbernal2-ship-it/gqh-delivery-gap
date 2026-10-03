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
generated = [row for row in nodes if row.get("active_in_scan") is False]
if len(generated) < 200:
    raise SystemExit(f"registry expansion is too small: {len(generated)} generated nodes")
if len(edges) < 500:
    raise SystemExit(f"registry expansion is too small: {len(edges)} edges")
if any(row.get("active_in_scan") is not False for row in generated):
    raise SystemExit("generated nodes must remain inactive in the association scan")
print(f"quantgraph manifest clean: {len(nodes)} nodes, {len(edges)} edges; "
      f"{len(generated)} inactive expansion nodes")
