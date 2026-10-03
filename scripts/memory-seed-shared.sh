#!/usr/bin/env bash
# One time: rebuild the shared file from every local memory in this project store.
# This is what makes the team's existing memory available to every session.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
SHARE_TAG="${SHARE_TAG:-gqh}"

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
hippo export "$TMP" >/dev/null
python3 - "$TMP" <<'PY'
import json, sys
from pathlib import Path
sys.path.insert(0, "scripts")
from memory_filter import filter_entries, render_markdown

raw = json.loads(Path(sys.argv[1]).read_text())
# Seeding ignores the share tag: for a one time seed, every entry in this project
# store is project scope by construction. Redaction still applies.
for item in raw:
    if isinstance(item, dict):
        tags = set(item.get("tags", []) or [])
        tags.add("quanthacks")
        item["tags"] = sorted(tags)
shared = filter_entries(raw)
Path("memory").mkdir(exist_ok=True)
Path("memory/shared.json").write_text(json.dumps(shared, indent=2) + "\n")
Path("memory/SHARED.md").write_text(render_markdown(shared))
print(f"seeded {len(shared)} shared entries")
PY
