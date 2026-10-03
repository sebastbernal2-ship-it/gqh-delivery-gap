#!/usr/bin/env python3
"""Tests for the parallel-work check.

Run: python3 tests/test_claims.py

Four people work at once. The check answers two questions before a merge happens,
not after:

  1. Do two branches touch the same files? That is where a conflict will land.
  2. Is a branch far behind main? That is where a merge turns into a rewrite.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from claims import find_overlaps, staleness  # noqa: E402


def main() -> int:
    failures = []

    def check(name, got, want):
        if got != want:
            failures.append(name)
            print(f"FAIL {name}:\n  got  {got}\n  want {want}")
        else:
            print(f"ok   {name}")

    branches = {
        "feat/aidan-strategy": ["src/strategy/core.py", "src/strategy/README.md"],
        "feat/vishnu-fast": ["src/fast/core.py", "src/fast/README.md"],
        "feat/lucy-hpc": ["hpc/slurm/run.sh"],
    }
    check("disjoint branches report nothing", find_overlaps(branches), [])

    branches["feat/vishnu-fast"].append("src/strategy/core.py")
    got = find_overlaps(branches)
    check("one shared file is reported once",
          [(a, b, sorted(p)) for a, b, p in got],
          [("feat/aidan-strategy", "feat/vishnu-fast", ["src/strategy/core.py"])])

    branches["feat/lucy-hpc"].append("src/strategy/core.py")
    got = find_overlaps(branches)
    check("three branches sharing a file give three pairs", len(got), 3)

    check("a branch never overlaps itself",
          find_overlaps({"feat/only": ["a.py", "a.py"]}), [])

    check("staleness reports commits behind main",
          staleness(commits_behind=30, threshold=20), "30 commits behind main")
    check("staleness is quiet when close",
          staleness(commits_behind=3, threshold=20), "")
    check("staleness warns near the threshold",
          staleness(commits_behind=21, threshold=20), "21 commits behind main")

    print(f"\n{7 - len(failures)}/7 passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
