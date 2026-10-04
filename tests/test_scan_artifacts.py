#!/usr/bin/env python3
"""Offline tests for scan crosswalk and decomposition reconciliation."""
from __future__ import annotations

import sys

ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from check_scan_artifacts import crosswalk_problems, decomposition_problems  # noqa: E402

failures: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        failures.append(f"{name}: got {got!r}, want {want!r}")


registry = [{"id": "measured:a"}, {"id": "measured:b"}]
manifest = [{"kind": "node", "id": "feature:a"}, {"kind": "node", "id": "feature:b"}]
good_crosswalk = [
    {"node": "measured:a", "manifest_ids": ["feature:a"], "status": "mapped",
     "relation": "same_measurement", "rationale": "same observable"},
    {"node": "measured:b", "manifest_ids": [], "status": "unmapped",
     "relation": "none", "rationale": "no safe counterpart"},
]
check("a complete crosswalk passes", crosswalk_problems(registry, manifest, good_crosswalk), [])
check("a missing crosswalk row is caught",
      any("missing crosswalk row" in problem for problem in crosswalk_problems(
          registry, manifest, good_crosswalk[:1])), True)
check("an unknown target is caught",
      any("manifest id does not exist" in problem for problem in crosswalk_problems(
          registry, manifest, [{**good_crosswalk[0], "manifest_ids": ["feature:nope"]}, good_crosswalk[1]])), True)

rows = [
    {"kind": "subnode", "layer": "feature"},
    {"kind": "split", "layer": ""},
    {"kind": "subnode", "layer": "entity"},
]
summary = {
    "manifest_nodes": 2,
    "subnodes_total": 2,
    "split_edges": 1,
    "written_graph_total": 4,
}
check("matching decomposition counts pass",
      decomposition_problems(2, rows, summary), [])
check("a stale decomposition count is caught",
      any("subnodes_total" in problem for problem in decomposition_problems(
          2, rows, {**summary, "subnodes_total": 1})), True)

if failures:
    print("\n".join(f"  FAIL {failure}" for failure in failures))
    raise SystemExit(1)
print("6/6 passed")
