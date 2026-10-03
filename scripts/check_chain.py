#!/usr/bin/env python3
"""Validate chain logs: docs/chains/<id>.jsonl

A chain invites scope creep and quiet overfitting. This is the mechanism that stops both, because
the dangerous moves fail the gate instead of depending on anyone's discipline.

Rules:
  scope      at most MAX_EDGES edges in the pilot, at most MAX_UNMEASURED of them without a
             measurement, and at most one P&L carrying role in the pilot. An edge marked
             "pilot": false is declared and parked: it is recorded, it keeps its load bearing
             test, and it does not consume pilot budget
  load       every edge states what changes when it is false; "nothing" means delete the edge
  evidence   a status may only become "measured" with an evidence path that exists
  freeze     once a sealed_opened event exists, no edge is added, no status upgraded,
             and no exposure bound raised
  honesty    downgrades, decisions and scope changes are recorded like everything else

The escape hatch is honest: a new chain id, which is a new study with its own record.
Run by `make check`.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHAINS = ROOT / "docs" / "chains"

# Meaning, taken from the QuantGraph edge semantics: structural, derivation, evidence and
# hypothesis types. What an edge means is separate from how well we know it.
SEMANTIC_TYPES = {
    "has_field", "exposes", "contains", "observes", "located_at", "located_in", "about",
    "implements", "produces",
    "derived_from", "feeds", "measured_by", "measures",
    "supports", "contradicts", "tests", "tested_by",
    "candidate_for", "affects", "influences", "drives", "causes", "gates", "conditions",
    "indicates", "operates", "exposed_to", "changes",
}
_LAYERS = {"source", "dataset", "raw", "feature", "entity", "event", "mechanism", "assumption",
           "outcome", "claim", "strategy", "rule", "evidence", "experiment", "implementation",
           "concept", "asset", "factor", "contract"}
MAX_EDGES = 8
MAX_UNMEASURED = 3
MAX_PNL_ROLES = 1

STATUSES = {"measured", "proxied", "testable", "irreducible"}
MODES = {"core", "node_supply", "assumption_closure", "edge_identification", "state_reading",
         "expression", "hedge", "overlay", "derivative_profit"}
PNL_MODES = {"expression", "hedge", "overlay", "derivative_profit"}
UNMEASURED = {"proxied", "testable"}
TRIVIAL = {"", "nothing", "none", "n/a", "na", "-"}

EDGE_EVENTS = {"edge_added", "edge_removed", "status_changed", "bound_changed"}
DECLARATION_EVENTS = {"node_proposed", "node_resolved", "source_proposed", "source_resolved"}


def _sources_of(event: dict) -> list[str]:
    """An edge may draw on one source or several."""
    raw = event.get("representation_source")
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        return [str(item) for item in raw if item]
    return [str(raw)]
REQUIRED = {
    "node_proposed": ["node", "layer", "proposed_type", "reason"],
    "node_resolved": ["node", "reason"],
    "source_proposed": ["source", "reason"],
    "source_resolved": ["source", "reason"],
    "edge_added": ["edge", "from_node", "to_node", "edge_type", "status", "conditions",
                   "if_false", "exposure_bound", "mode"],
    "edge_removed": ["edge", "reason"],
    "status_changed": ["edge", "from", "to"],
    "bound_changed": ["edge", "from", "to", "reason"],
    "decision": ["choice", "value", "reason"],
    "sealed_opened": ["revision", "run_plan"],
}


def _phase_rank(phase: str) -> int:
    return 1 if phase == "sealed" else 0


def problems(events: list[dict], existing: list[str], max_edges: int = MAX_EDGES,
             max_unmeasured: int = MAX_UNMEASURED, max_pnl: int = MAX_PNL_ROLES) -> list[str]:
    """Return a list of problems. Empty means valid."""
    out: list[str] = []
    known = set(existing)
    state: dict[str, dict] = {}
    declared_nodes: set[str] = set()
    declared_sources: set[str] = set()
    used_nodes: set[str] = set()
    used_sources: set[str] = set()
    sealed = False

    for i, event in enumerate(events, 1):
        label = f"line {i}"
        if not isinstance(event, dict):
            out.append(f"{label}: not an object")
            continue
        for field in ("ts", "chain", "event", "phase"):
            if not event.get(field):
                out.append(f"{label}: missing '{field}'")
        kind = event.get("event")
        if kind not in REQUIRED:
            out.append(f"{label}: unknown event '{kind}'")
            continue
        for field in REQUIRED[kind]:
            if event.get(field) in (None, ""):
                out.append(f"{label} ({kind}): missing '{field}'")

        phase_sealed = _phase_rank(str(event.get("phase", ""))) == 1

        if kind == "node_proposed":
            node = str(event.get("node"))
            layer = str(event.get("layer"))
            if layer not in _LAYERS:
                out.append(f"{label}: layer '{layer}' is not one of {sorted(_LAYERS)}")
            if node in declared_nodes:
                out.append(f"{label}: node '{node}' is declared twice")
            declared_nodes.add(node)
            continue

        if kind == "node_resolved":
            node = str(event.get("node"))
            if node in declared_nodes:
                out.append(f"{label}: node '{node}' is declared twice")
            declared_nodes.add(node)
            continue

        if kind in ("source_proposed", "source_resolved"):
            source = str(event.get("source"))
            if source in declared_sources:
                out.append(f"{label}: source '{source}' is declared twice")
            declared_sources.add(source)
            continue

        if kind == "decision":
            # Chain level, not edge level: it records a choice, and the count feeds the
            # multiple testing deflation.
            continue

        if kind == "sealed_opened":
            sealed = True
            plan = event.get("run_plan")
            if plan and plan not in known:
                out.append(f"{label}: run plan '{plan}' does not exist")
            continue

        if kind == "edge_added":
            edge = str(event.get("edge"))
            if sealed:
                out.append(f"{label}: edge '{edge}' added after the sealed window opened")
            status = str(event.get("status"))
            if status not in STATUSES:
                out.append(f"{label}: status '{status}' is not one of {sorted(STATUSES)}")
            if str(event.get("mode")) not in MODES:
                out.append(f"{label}: mode '{event.get('mode')}' is not a known integration mode")
            if str(event.get("if_false", "")).strip().lower() in TRIVIAL:
                out.append(f"{label}: edge '{edge}' changes nothing when false, so it is not "
                           f"load bearing. Delete it instead of listing it")
            if status == "measured" and not event.get("evidence"):
                out.append(f"{label}: edge '{edge}' is marked measured with no evidence")
            evidence = event.get("evidence")
            if evidence and evidence not in known:
                out.append(f"{label}: evidence '{evidence}' does not exist")
            edge_type = str(event.get("edge_type"))
            if edge_type not in SEMANTIC_TYPES:
                out.append(f"{label}: edge_type '{edge_type}' is not a known semantic type")
            for referenced in ("from_node", "to_node"):
                if event.get(referenced):
                    used_nodes.add(str(event[referenced]))
            for source in _sources_of(event):
                used_sources.add(source)
            if edge in state:
                out.append(f"{label}: edge '{edge}' already exists. Use status_changed or bound_changed")
            state[edge] = {"status": status, "mode": str(event.get("mode")),
                           "bound": str(event.get("exposure_bound")),
                           "pilot": bool(event.get("pilot", True))}
            continue

        edge = str(event.get("edge"))
        if kind == "edge_removed":
            state.pop(edge, None)
            continue

        if edge not in state:
            out.append(f"{label}: edge '{edge}' was never added")
            continue

        if kind == "status_changed":
            new_status = str(event.get("to"))
            if new_status not in STATUSES:
                out.append(f"{label}: status '{new_status}' is not one of {sorted(STATUSES)}")
            upgrading = new_status == "measured" and state[edge]["status"] != "measured"
            if (sealed or phase_sealed) and upgrading:
                out.append(f"{label}: edge '{edge}' upgraded to measured after the sealed window "
                           f"opened. Open a new chain id instead")
            if upgrading and not event.get("evidence"):
                out.append(f"{label}: edge '{edge}' upgraded to measured with no evidence")
            evidence = event.get("evidence")
            if evidence and evidence not in known:
                out.append(f"{label}: evidence '{evidence}' does not exist")
            state[edge]["status"] = new_status
            continue

        if kind == "bound_changed":
            old, new = str(event.get("from")), str(event.get("to"))
            if (sealed or phase_sealed) and _looks_larger(new, old):
                out.append(f"{label}: exposure bound on '{edge}' raised after the sealed window "
                           f"opened ({old} -> {new})")
            state[edge]["bound"] = new
            continue

    # Every declared node and source must serve at least one edge, or it is decoration.
    for node in sorted(declared_nodes - used_nodes):
        out.append(f"decoration: node '{node}' is declared but no edge uses it. Delete it, or use it")
    for source in sorted(declared_sources - used_sources):
        out.append(f"decoration: source '{source}' is declared but no edge needs it")
    # An edge may only reference a node this log declares, whether resolved or proposed.
    for i, event in enumerate(events, 1):
        if not isinstance(event, dict) or event.get("event") != "edge_added":
            continue
        for field in ("from_node", "to_node"):
            node = event.get(field)
            if node and str(node) not in declared_nodes:
                out.append(f"line {i}: edge node '{node}' is not declared in this log. "
                           f"Declare it as node_resolved or node_proposed")

    active = {edge: info for edge, info in state.items() if info.get("pilot", True)}
    parked = len(state) - len(active)
    if parked:
        pass  # parked edges are recorded and are not part of the pilot budget
    if len(active) > max_edges:
        out.append(f"scope: {len(active)} active edges exceeds the pilot cap of {max_edges}. "
                   f"Shorten the chain or park edges in a new chain id")
    unmeasured = [e for e, s in active.items() if s["status"] in UNMEASURED]
    if len(unmeasured) > max_unmeasured:
        out.append(f"scope: {len(unmeasured)} unmeasured edges ({', '.join(sorted(unmeasured))}) "
                   f"exceed the cap of {max_unmeasured}")
    pnl = [e for e, s in active.items() if s["mode"] in PNL_MODES]
    if len(pnl) > max_pnl:
        out.append(f"scope: {len(pnl)} P&L carrying roles ({', '.join(sorted(pnl))}) exceed the "
                   f"pilot cap of {max_pnl}. The pilot holds one expression")
    return out


def _looks_larger(new: str, old: str) -> bool:
    """Compare bounds loosely: pull the first number out of each and compare if both parse."""
    def number(text: str):
        digits = "".join(ch if (ch.isdigit() or ch == ".") else " " for ch in str(text)).split()
        try:
            return float(digits[0])
        except (IndexError, ValueError):
            return None
    a, b = number(new), number(old)
    if a is None or b is None:
        return new != old
    return a > b


def load_log(path: Path) -> list[dict]:
    out = []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as exc:
            out.append({"_bad_line": i, "_error": str(exc)})
    return out


def tracked(existing_only: bool = False) -> list[str]:
    args = ["git", "ls-files", "--cached", "--others", "--exclude-standard"]
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    return [line for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
    if not CHAINS.exists():
        print("no chain logs yet (docs/chains/)")
        return 0
    # A template is an example, not a log: its paths are illustrative on purpose.
    logs = sorted(p for p in CHAINS.glob("*.jsonl") if "TEMPLATE" not in p.name)
    if not logs:
        print("no chain logs yet (docs/chains/)")
        return 0
    existing = tracked()
    total_problems = 0
    for log in logs:
        events = load_log(log)
        found = problems(events, existing)
        decisions = len([e for e in events if isinstance(e, dict) and e.get("event") == "decision"])
        print(f"{log.name}: {len(events)} events, {decisions} recorded choices")
        for problem in found:
            print(f"  PROBLEM: {problem}")
        total_problems += len(found)
    if total_problems:
        return 1
    print("chain logs: consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
