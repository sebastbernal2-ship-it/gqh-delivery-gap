#!/usr/bin/env python3
"""Catch references to paths that do not exist.

Renames are normal here, and a document that points at a file nobody renamed is how a repo
starts lying to the people working in it. This checks every path-shaped token in the tracked
documents and scripts against git.

Illustrative paths are allowed on purpose: a token is only required to exist when its parent
directory exists. `src/<component>/README.md` in a design note is not a promise; `docs/writing/`
is.

Run by `make check`.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN_SUFFIXES = {".md", ".sh", ".py", ".jsonl", ".toml"}
SCAN_NAMES = {"Makefile", ".cursorrules"}
# Only these extensions count as a file reference. Anything else is prose that happens to
# contain a slash, such as "data/result contracts".
FILE_SUFFIXES = (".md", ".py", ".sh", ".json", ".jsonl", ".toml", ".cfg", ".txt", ".csv",
                 ".yml", ".yaml", ".ipynb", ".sql", ".q")
# A match must start at a real boundary, so the path part of a URL is not a reference.
TOKEN = re.compile(r"(?<![A-Za-z0-9/:@_.-])"
                   r"((?:docs|scripts|tests|src|hpc|results|memory|data)/[A-Za-z0-9._/-]+)")
SKIP_CHARS = set("<>*{}[]$|")
# Fixtures name paths on purpose. History snapshots and the memory mirror are records of what
# was true then, and renames are expected to leave them untouched.
# The orderbook engine is a nested project with its own docs root: its internal references
# resolve there, not against this repository.
SKIP_PREFIXES = ("tests/", "memory/", "docs/history/", "orderbook-engine/")
SKIP_NAMES = ("TEMPLATE",)
# Explicit output contracts may precede generation; only result artifacts qualify.
GENERATED_PATH = re.compile(r"^generated-path: (results/[A-Za-z0-9._/-]+)$", re.MULTILINE)


FOREIGN_TAG = "foreign-repo="


def strip_foreign_fences(text: str) -> str:
    """Drop fenced blocks whose info string marks them as another checkout's commands.

    A prompt written for the algoterminal session names that repo's scripts, which do not exist
    here and should not. Only tagged fences are skipped, so an ordinary block is still checked.
    """
    out, skipping = [], False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            if skipping:
                skipping = False
                continue
            if FOREIGN_TAG in stripped:
                skipping = True
                continue
        if not skipping:
            out.append(line)
    return "\n".join(out)


def clean(token: str) -> str:
    return token.rstrip(".,;:)\"'`")


def references(text: str) -> list[str]:
    """Every repo path this text refers to as a file, or as a directory with a trailing slash."""
    out = []
    for raw in TOKEN.findall(text):
        token = clean(raw)
        if any(ch in token for ch in SKIP_CHARS):
            continue
        if token.endswith("/"):
            out.append(token)
            continue
        if token.endswith(FILE_SUFFIXES):
            out.append(token)
    return out


def missing(tracked: list[str], files: dict[str, str]) -> list[str]:
    known = set(tracked)
    declared_outputs = set(GENERATED_PATH.findall(files.get("results/README.md", "")))
    known_dirs = {"/".join(path.split("/")[:i]) for path in tracked
                  for i in range(1, path.count("/") + 1)}
    known_dirs |= {"/".join(path.split("/")[:i]) + "/" for path in tracked
                   for i in range(1, path.count("/") + 1)}
    problems = []
    for name, text in sorted(files.items()):
        for token in references(text):
            if token in known or token in known_dirs or token in declared_outputs:
                continue
            parent = "/".join(token.split("/")[:-1])
            if parent and parent not in known_dirs and parent + "/" not in known_dirs:
                continue  # parent does not exist, so this is an illustrative path
            problems.append(f"{name}: references '{token}', which does not exist")
    return problems


def main() -> int:
    tracked = [line for line in subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT,
                                               capture_output=True, text=True).stdout.splitlines()
               if line.strip()]
    files = {}
    for name in tracked:
        path = ROOT / name
        if name.startswith(SKIP_PREFIXES) or "/tests/" in name or any(tag in path.name for tag in SKIP_NAMES):
            continue
        if path.suffix in SCAN_SUFFIXES or path.name in SCAN_NAMES:
            try:
                files[name] = strip_foreign_fences(path.read_text(errors="ignore"))
            except OSError:
                continue
    problems = missing(tracked, files)
    print(f"paths: checked {len(files)} files")
    if problems:
        print("stale references:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("paths: every reference resolves")
    return 0


if __name__ == "__main__":
    sys.exit(main())
