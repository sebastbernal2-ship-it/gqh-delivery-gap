#!/usr/bin/env python3
"""Validate the market map: participants, their constraints, the flows, the instruments, and the mappings.

The rules are stated in docs/market/SCHEMA.md. The point of the check is that a claim of a forced flow cannot be
written without naming the participant, the constraint, the instrument and the falsifier, and that an instrument
cannot be written without pointing at a node we actually measure, or saying why there is none.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP = ROOT / "docs" / "market" / "map.jsonl"
NODES = ROOT / "docs" / "scan" / "nodes.jsonl"

KINDS = {"fund", "dealer", "operator", "contractor", "lender", "provider", "index", "issuer",
         "household", "venue", "supplier", "utility"}
CONSTRAINTS = {"rule", "mandate", "contract", "capital", "procedure", "attention", "latency", "none"}
RELATIONS = {"expresses", "indicates", "conditions", "measures"}
CONCENTRATION = {"concentrated", "diluted", "unknown"}


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main() -> int:
    problems: list[str] = []
    records = load(MAP)
    node_ids = {row["id"] for row in load(NODES)}

    by_type: dict[str, list[dict]] = {}
    for record in records:
        by_type.setdefault(record.get("type", ""), []).append(record)

    for name, expected in (("participant", 6), ("flow", 6), ("instrument", 6), ("mapping", 4)):
        if not by_type.get(name):
            problems.append(f"no {name} records at all")

    ids = [record["id"] for record in records]
    for identifier in set(ids):
        if ids.count(identifier) > 1:
            problems.append(f"duplicate id {identifier}")

    participants = {record["id"]: record for record in by_type.get("participant", [])}
    flows = {record["id"]: record for record in by_type.get("flow", [])}
    instruments = {record["id"]: record for record in by_type.get("instrument", [])}

    for record in by_type.get("participant", []):
        if record["kind"] not in KINDS:
            problems.append(f"{record['id']}: unknown kind {record['kind']}")
        if record["constraint"] not in CONSTRAINTS:
            problems.append(f"{record['id']}: unknown constraint {record['constraint']}")
        for field in ("evidence", "falsifier", "constraint_note"):
            if not record.get(field):
                problems.append(f"{record['id']}: missing {field}")

    for record in by_type.get("flow", []):
        if record["participant"] not in participants:
            problems.append(f"{record['id']}: unknown participant {record['participant']}")
        if record["instrument"] not in instruments:
            problems.append(f"{record['id']}: unknown instrument {record['instrument']}")
        if record["observable"] not in ("public", "private"):
            problems.append(f"{record['id']}: observable must be public or private")
        for field in ("evidence", "falsifier", "calendar", "data_note", "size_note"):
            if not record.get(field):
                problems.append(f"{record['id']}: missing {field}")

    for record in by_type.get("instrument", []):
        if record["concentration"] not in CONCENTRATION:
            problems.append(f"{record['id']}: unknown concentration {record['concentration']}")
        if "node" in record:
            if record["node"] not in node_ids:
                problems.append(f"{record['id']}: node {record['node']} is not in the declared node space")
        elif not record.get("no_node_reason"):
            problems.append(f"{record['id']}: needs a node or a reason there is none")

    for record in by_type.get("mapping", []):
        if record["node"] not in node_ids:
            problems.append(f"{record['id']}: node {record['node']} is not in the declared node space")
        if record["flow"] not in flows:
            problems.append(f"{record['id']}: unknown flow {record['flow']}")
        if record["relation"] not in RELATIONS:
            problems.append(f"{record['id']}: unknown relation {record['relation']}")
        for field in ("evidence", "falsifier"):
            if not record.get(field):
                problems.append(f"{record['id']}: missing {field}")

    # every flow should carry at least one mapping, or it is not connected to anything we measure
    mapped = {record["flow"] for record in by_type.get("mapping", [])}
    for identifier in flows:
        if identifier not in mapped:
            problems.append(f"{identifier}: no mapping, so nothing we measure connects to it")

    print(f"market map: {len(records)} records, "
          f"{len(participants)} participants, {len(flows)} flows, {len(instruments)} instruments, "
          f"{len(by_type.get('mapping', []))} mappings")
    if problems:
        print(f"{len(problems)} problems:")
        for problem in problems:
            print("  ", problem)
        return 1
    print("clean: every flow names a participant and an instrument, every instrument names a node or a reason, "
          "every record carries evidence and a falsifier")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
