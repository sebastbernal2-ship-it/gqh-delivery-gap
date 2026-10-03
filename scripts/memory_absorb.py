#!/usr/bin/env python3
"""Load the team's shared memory into the local store.

The shared file is a list of entries. For each entry that is not already in the local
store, this writes it with `hippo remember`, one call per entry, so the store gets one
clean memory per entry with the right tags.

Why not `hippo import --file`: import parses the JSON as plain text and writes one
memory per line, which floods the store with fragment entries.

Idempotent: an entry already present by normalized content is skipped.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SHARED = Path("memory/shared.json")


def normalize(text: str) -> str:
    return " ".join(str(text).split()).strip()


def missing_entries(shared, local):
    """Return shared entries whose normalized content is not already local."""
    have = {normalize(item.get("content", "")) for item in local if isinstance(item, dict)}
    out = []
    seen = set()
    for item in shared:
        if not isinstance(item, dict):
            continue
        key = normalize(item.get("content", ""))
        if not key or key in have or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def ensure_store() -> None:
    """Create a local store on a fresh device, so the first run needs no extra step."""
    probe = subprocess.run(["hippo", "export"], capture_output=True, text=True)
    if probe.returncode == 0:
        return
    if "No hippo store" in (probe.stderr or probe.stdout or ""):
        subprocess.run(["hippo", "init", "--no-hooks", "--no-schedule"],
                       capture_output=True, text=True)


def union_entries(shared, existing):
    """Union of the incoming entries and the entries already in the shared file.

    A device only knows its own memories. Without a union, a device whose store cannot
    see another device's entry would delete it from the shared file on its next share.
    """
    out = []
    seen = set()
    for item in list(shared) + list(existing):
        if not isinstance(item, dict):
            continue
        key = normalize(item.get("content", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return sorted(out, key=lambda item: str(item.get("id", "")))


def export_local() -> list:
    result = subprocess.run(["hippo", "export"], capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        return []
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def main() -> int:
    if not SHARED.exists():
        print("no memory/shared.json. Nothing to absorb.")
        return 0
    shared = json.loads(SHARED.read_text())
    ensure_store()
    local = export_local()
    todo = missing_entries(shared, local)
    if not todo:
        print(f"already current: {len(shared)} shared entries, 0 new")
        return 0

    written = 0
    for item in todo:
        cmd = ["hippo", "remember", item["content"]]
        for tag in item.get("tags", []):
            cmd += ["--tag", str(tag)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            written += 1
        else:
            print(f"failed to write one entry: {result.stderr.strip()[:120]}")
    print(f"absorbed {written} of {len(todo)} new shared entries ({len(shared)} total shared)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
