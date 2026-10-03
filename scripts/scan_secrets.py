#!/usr/bin/env python3
"""Scan tracked and untracked-but-not-ignored files for credential shapes.

This repo is public and four people push to it. Run it before a push, or just run
`make check`, which calls it.

Exit code 1 means: do not push. Fix the content or add it to .gitignore.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from memory_filter import looks_secret  # noqa: E402

MAX_BYTES = 400_000
SKIP_DIRS = {"." + "git", ".venv", "venv", "node" + "_modules", "__pycache__"}


def candidates() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard"],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    paths = []
    for name in out:
        path = Path(name)
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.stat().st_size <= MAX_BYTES:
            paths.append(path)
    return sorted(paths)


def main() -> int:
    hits = []
    files = candidates()
    for path in files:
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        if looks_secret(text):
            hits.append(str(path))
    print(f"scanned {len(files)} files")
    if hits:
        print("credential-shaped content found:")
        for hit in hits:
            print(f"  - {hit}")
        print("Do not push until this is clean. See docs/memory.md.")
        return 1
    print("clean: no credential shapes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
