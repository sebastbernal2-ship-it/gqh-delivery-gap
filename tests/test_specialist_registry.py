#!/usr/bin/env python3
"""The specialist registry is the gate for council membership: data bundles, not architectures."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs" / "specialists" / "registry.jsonl"
REQUIRED = ("id", "data_bundle", "modality", "information_cutoff", "horizon", "target",
            "features_ref", "recipe", "calibration", "decision_type", "owner", "status", "evidence")
STATUSES = {"evaluated", "implemented", "data_gated", "retired"}


def load() -> list[dict]:
    return [json.loads(line) for line in REGISTRY.read_text().splitlines() if line.strip()]


def test_every_entry_names_its_bundle_and_its_evidence():
    entries = load()
    assert entries, "the registry cannot be empty"
    for entry in entries:
        for field in REQUIRED:
            assert entry.get(field), f"{entry.get('id')} is missing {field}"
        assert entry["status"] in STATUSES, entry["status"]
        assert (ROOT / entry["evidence"]).exists(), f"{entry['id']}: {entry['evidence']} is missing"


def test_ids_and_bundles_are_unique():
    entries = load()
    ids = [entry["id"] for entry in entries]
    assert len(ids) == len(set(ids)), ids
    bundles = [entry["data_bundle"].lower() for entry in entries]
    assert len(bundles) == len(set(bundles)), "two specialists claim the same bundle"


def test_the_council_members_are_registered():
    entries = {entry["id"] for entry in load()}
    for name in ("issuer_facts", "market_state", "filing_text", "filing_metadata"):
        assert name in entries, name


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} specialist registry contract(s) held")
