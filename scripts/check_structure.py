#!/usr/bin/env python3
"""Keep the repo navigable as it fills up.

Two rules only, both cheap to satisfy and expensive to lose:

1. Every area of code or compute has its own directory with a README, so a stranger can tell
   what it is for without reading the code.
2. The repo root stays a short list. New things go in a named area, not in the root.

This reads git, not the filesystem. Local junk (a virtual environment, caches, an egg-info
directory, a scratch notebook) must never fail the check for someone else's clone.

Run by `make check`.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TOP_LEVEL = {
    ".github", ".vscode", ".cursor", ".cursorrules", ".githooks", ".gitignore", "AGENTS.md", "CLAUDE.md", "Makefile", "OWNERS.md",
    "README.md", "data", "docs", "hpc", "memory", "pyproject.toml", "results", "scripts", "src",
    "tests",
}
AREAS = ["src", "hpc"]


def tracked_paths(root: Path) -> list[str]:
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=root, capture_output=True, text=True)
    return [line for line in out.stdout.splitlines() if line.strip()]


def problems(tracked: list[str], top_level=TOP_LEVEL, areas=AREAS) -> list[str]:
    found: list[str] = []
    top = {path.split("/")[0] for path in tracked}
    for name in sorted(top - top_level):
        found.append(f"{name}: not a known area. Put it inside one, or add it to "
                     f"scripts/check_structure.py and say why in docs/decisions.md")
    for area in areas:
        prefix = f"{area}/"
        components = {path.split("/")[1] for path in tracked
                      if path.startswith(prefix) and path.count("/") >= 2}
        for component in sorted(components):
            readme = f"{area}/{component}/README.md"
            if readme not in tracked:
                found.append(f"{area}/{component}/ has no README.md. One paragraph is enough: "
                             f"what it is, who owns it, how to run it")
    return found


def inventory(tracked: list[str], areas=AREAS) -> list[str]:
    lines = []
    for area in areas:
        prefix = f"{area}/"
        components = sorted({path.split("/")[1] for path in tracked
                             if path.startswith(prefix) and path.count("/") >= 2})
        lines.append(f"  {area}/: {', '.join(components) if components else '(empty)'}")
    docs = sorted({path.split("/")[1] for path in tracked
                   if path.startswith("docs/") and path.count("/") == 1})
    if docs:
        lines.append(f"  docs/: {', '.join(docs)}")
    return lines


def main() -> int:
    tracked = tracked_paths(ROOT)
    found = problems(tracked)
    print("inventory:")
    for line in inventory(tracked):
        print(line)
    if found:
        print("structure problems:")
        for problem in found:
            print(f"  - {problem}")
        return 1
    print(f"structure: clean ({len(tracked)} tracked files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
