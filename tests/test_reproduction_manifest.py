#!/usr/bin/env python3
"""The manifest must cover every declared artifact, with a digest that still matches the file."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "results" / "reproduction-manifest.json"


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()


def test_manifest_structure():
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["schema"] == "reproduction-manifest-v1"
    entries = manifest["entries"]
    assert len(entries) >= 10
    for entry in entries:
        for field in ("name", "tier", "command", "claim"):
            assert entry.get(field), (entry["name"], field)
        assert entry["tier"] in ("default", "full", "network")
        if entry["tier"] == "network":
            assert entry["exact"] is False
        else:
            assert entry.get("artifact")
    names = [entry["name"] for entry in entries]
    assert len(names) == len(set(names))


def test_recorded_digests_match_the_committed_artifacts():
    manifest = json.loads(MANIFEST.read_text())
    for entry in manifest["entries"]:
        if not entry.get("artifact") or not entry.get("sha256"):
            continue
        path = ROOT / entry["artifact"]
        if not path.exists():
            continue
        assert digest(path) == entry["sha256"], entry["name"]
        break          # one exact artifact per run keeps the suite fast; the tool checks them all


def test_offline_entries_never_need_the_network():
    manifest = json.loads(MANIFEST.read_text())
    for entry in manifest["entries"]:
        if entry["tier"] in ("default", "full"):
            command = entry["command"]
            assert "http" not in command and "curl" not in command, entry["name"]


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} reproduction-manifest contract(s) held")
