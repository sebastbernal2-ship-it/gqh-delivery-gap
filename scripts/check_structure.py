#!/usr/bin/env python3
"""Keep the repo navigable as it fills up.

Two rules only, both cheap to satisfy and expensive to lose:

1. Every area of code or compute has its own directory with a README, so a stranger can tell
   what it is for without reading the code.
2. The repo root stays a short list. New things go in a named area, not in the root.

Run by `make check`. Add a new area deliberately: add it to TOP_LEVEL and say why in
docs/decisions.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TOP_LEVEL = {
    ".cursorrules", ".githooks", ".gitignore", "AGENTS.md", "CLAUDE.md", "Makefile", "OWNERS.md",
    "README.md", "data", "docs", "hpc", "memory", "pyproject.toml", "results", "scripts", "src",
    "tests",
}
AREAS = ["src", "hpc"]
# Directories that are never part of the layout.
IGNORED = {"." "git", "." "hippo", "." "pi", "." "venv", "__pycache__"}


def visible(entry: Path) -> bool:
    return entry.name not in IGNORED


def problems(root: Path, top_level=TOP_LEVEL, areas=AREAS) -> list[str]:
    out: list[str] = []
    for entry in sorted(root.iterdir()):
        if not visible(entry) or entry.name.startswith("."):
            continue
        if entry.name not in top_level:
            out.append(f"{entry.name}: not a known area. Put it inside one, or add it to "
                       f"scripts/check_structure.py and say why in docs/decisions.md")
    for area in areas:
        base = root / area
        if not base.is_dir():
            continue
        for child in sorted(base.iterdir()):
            if not child.is_dir() or child.name == "__pycache__":
                continue
            if not (child / "README.md").exists():
                out.append(f"{area}/{child.name}/ has no README.md. One paragraph is enough: "
                           f"what it is, who owns it, how to run it")
    return out


def inventory(root: Path, areas=AREAS) -> list[str]:
    lines = []
    for area in areas:
        base = root / area
        if not base.is_dir():
            continue
        children = [c.name for c in sorted(base.iterdir())
                    if c.is_dir() and c.name != "__pycache__"]
        lines.append(f"  {area}/: {', '.join(children) if children else '(empty)'}")
    docs = root / "docs"
    if docs.is_dir():
        papers = sorted(d.name for d in docs.iterdir() if d.is_file())
        lines.append(f"  docs/: {', '.join(papers)}")
    return lines


def main() -> int:
    found = problems(ROOT)
    print("inventory:")
    for line in inventory(ROOT):
        print(line)
    if found:
        print("structure problems:")
        for problem in found:
            print(f"  - {problem}")
        return 1
    print("structure: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
