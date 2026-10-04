#!/usr/bin/env python3
"""The variant registry: a numbered tally so a multiplicity statement is possible at all."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs" / "plan" / "variant-registry.jsonl"
STATUSES = {"adopted", "rejected", "reported", "baseline", "superseded", "retired", "weak",
            "prototype", "untried", "unverified"}


def load() -> list[dict]:
    return [json.loads(line) for line in REGISTRY.read_text().splitlines() if line.strip()]


def test_every_entry_is_identifiable_and_classified():
    entries = load()
    assert entries, "the registry cannot be empty"
    ids = [entry["id"] for entry in entries]
    assert ids == sorted(ids) and len(ids) == len(set(ids))
    for entry in entries:
        for field in ("id", "axis", "question", "variant", "status", "declared_before"):
            assert entry.get(field) not in (None, ""), f"{entry.get('id')} is missing {field}"
        assert entry["status"] in STATUSES, entry["status"]
        assert isinstance(entry["declared_before"], bool)


def test_every_adopted_variant_sits_beside_its_alternative():
    """An axis where something was adopted must show what else was on the table."""
    by_axis: dict[str, list[dict]] = {}
    for entry in load():
        by_axis.setdefault(entry["axis"], []).append(entry)
    for axis, entries in by_axis.items():
        if any(entry["status"] == "adopted" for entry in entries):
            assert len(entries) >= 2, f"axis {axis} adopted a variant with no alternative recorded"


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} variant registry contract(s) held; {len(load())} variants registered")
