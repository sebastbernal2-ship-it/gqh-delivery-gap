#!/usr/bin/env python3
"""Keep OWNERS.md one roster and one claim table.

Why this exists: three teammates pushed inside twenty minutes and the file grew three ownership
blocks, a stale summary paragraph, and two names for one person. The fix is a shape that resists
growth, plus a gate that notices when the shape is lost.

Rules checked:
  one claim table, no section headings between it and the rules
  one row per path, one person per row
  every person named is in the roster
  every claimed path that is not an empty area exists in the repo

Run by `make check`.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "OWNERS.md"
TABLE_HEADER = "| Path | Person"
# A claim that is a future area, not a path yet.
FUTURE_MARKERS = ("<component>", "<approach>")


def _tables(text: str) -> list[list[str]]:
    """Rows of every markdown table whose header mentions Path and Person."""
    tables, current, in_table = [], [], False
    for line in text.splitlines():
        if line.strip().startswith(TABLE_HEADER):
            in_table, current = True, []
            continue
        if in_table:
            if line.strip().startswith("|"):
                current.append(line)
            else:
                tables.append(current)
                in_table = False
    if in_table:
        tables.append(current)
    return tables


def _split_paths(cell: str) -> list[str]:
    """Paths in one cell, comma separated, each stripped of its backticks."""
    return [part.strip().strip("`").strip() for part in cell.split(",")]


def parse_claims(text: str) -> dict[str, str]:
    claims: dict[str, str] = {}
    for rows in _tables(text):
        for row in rows[1:]:  # skip the separator row
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            if len(cells) >= 2 and cells[0] and cells[1]:
                for path in _split_paths(cells[0]):
                    if path:
                        claims[path] = cells[1].strip()
    return claims


def _section(text: str, heading: str) -> str:
    """Lines between a heading and the next heading of the same level."""
    lines, inside, out = text.splitlines(), False, []
    for line in lines:
        if line.strip().startswith("## "):
            inside = line.strip() == heading
            continue
        if inside:
            out.append(line)
    return "\n".join(out)


def roster(text: str) -> list[str]:
    """Names from the roster table only, so no other two column table is mistaken for people."""
    out = []
    for line in _section(text, "## The four of us").splitlines():
        if line.strip().startswith("|") and line.count("|") >= 3:
            cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
            if len(cells) == 2 and cells[0] and cells[1] and cells[0] not in ("GitHub", "---"):
                out.append(cells[0])
    return out


def validate(text: str, names: list[str], existing: list[str]) -> list[str]:
    problems: list[str] = []
    tables = _tables(text)
    if len(tables) > 1:
        problems.append(f"more than one claim table ({len(tables)}). Keep one table and add rows")

    seen: set[str] = set()
    for rows in tables:
        for row in rows[1:]:
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            if len(cells) < 2:
                continue
            for path in _split_paths(cells[0]):
                if not path or path.startswith("|"):
                    continue
                if path in seen:
                    problems.append(f"{path}: claimed twice")
                seen.add(path)
                person = cells[1].strip()
                if person and person != "nobody" and person not in names:
                    problems.append(f"{path}: owner '{person}' is not in the roster")
                if any(marker in path for marker in FUTURE_MARKERS):
                    continue  # a future area, not a path yet
                if path.endswith("/"):
                    if not any(p.startswith(path) for p in existing):
                        problems.append(f"{path}: claimed but does not exist")
                elif path not in existing:
                    problems.append(f"{path}: claimed but does not exist")
    return problems


def tracked_paths() -> list[str]:
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                         cwd=ROOT, capture_output=True, text=True)
    return [line for line in out.stdout.splitlines() if line.strip()]


def main() -> int:
    if not DOC.exists():
        print("no OWNERS.md")
        return 0
    text = DOC.read_text()
    names = roster(text)
    problems = validate(text, names, tracked_paths())
    print(f"ownership: {len(parse_claims(text))} claimed path(s), {len(names)} in the roster")
    if problems:
        for problem in problems:
            print(f"  PROBLEM: {problem}")
        return 1
    print("ownership: consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
