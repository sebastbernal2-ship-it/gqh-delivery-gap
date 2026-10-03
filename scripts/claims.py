#!/usr/bin/env python3
"""Who is working on what, and where will that collide?

Read only. It fetches, then reads the branches on origin, so it sees every machine's work in
progress without anyone maintaining a claim file. A claim file goes stale; branches do not.

  make claims     the table: branch, last commit, commits ahead and behind, files touched
  make overlaps   only the collisions, which is the part that costs hours

Two rules this exists to serve:

  1. Two branches touching the same file will conflict at merge time. Find out now.
  2. A branch far behind main merges into a rewrite. Rebase early, merge same day.
"""
from __future__ import annotations

import subprocess
import sys
from itertools import combinations

MAIN = "origin/main"
STALE_AFTER = 20


def find_overlaps(branch_paths: dict[str, list[str]]) -> list[tuple[str, str, list[str]]]:
    """Return (branch_a, branch_b, shared paths) for every pair that shares a path."""
    out = []
    for a, b in combinations(sorted(branch_paths), 2):
        shared = sorted(set(branch_paths[a]) & set(branch_paths[b]))
        if shared:
            out.append((a, b, shared))
    return out


def staleness(commits_behind: int, threshold: int = STALE_AFTER) -> str:
    """A loud string when a branch has drifted, empty when it has not."""
    if commits_behind > threshold:
        return f"{commits_behind} commits behind main"
    return ""


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def collect() -> tuple[dict[str, list[str]], dict[str, dict]]:
    git("fetch", "--quiet", "origin")
    branches = [b for b in git("for-each-ref", "refs/remotes/origin", "--format=%(refname:short)")
                .splitlines() if b and b != MAIN and not b.endswith("/HEAD")]
    paths: dict[str, list[str]] = {}
    meta: dict[str, dict] = {}
    for branch in branches:
        changed = git("diff", "--name-only", f"{MAIN}...{branch}").splitlines()
        if not changed:
            continue
        ahead = git("rev-list", "--count", f"{MAIN}..{branch}") or "0"
        behind = int(git("rev-list", "--count", f"{branch}..{MAIN}") or "0")
        last = git("log", "-1", "--format=%cr", branch)
        paths[branch] = changed
        meta[branch] = {"ahead": int(ahead), "behind": behind, "last": last,
                        "files": len(changed)}
    return paths, meta


def main(argv: list[str]) -> int:
    only_overlaps = "--overlaps" in argv
    paths, meta = collect()
    if not paths:
        print("no branches in flight. Everyone is on main, or nothing is pushed yet.")
        return 0

    if not only_overlaps:
        print(f"{'branch':44s}{'last commit':16s}{'ahead':>6s}{'behind':>7s}{'files':>7s}")
        for branch in sorted(paths):
            m = meta[branch]
            print(f"{branch:44s}{m['last']:16s}{m['ahead']:6d}{m['behind']:7d}{m['files']:7d}")
        print()

    overlaps = find_overlaps(paths)
    if overlaps:
        print("COLLISIONS: two branches on the same file will conflict at merge time")
        for a, b, shared in overlaps:
            print(f"  {a}  <->  {b}")
            for path in shared[:6]:
                print(f"      {path}")
            if len(shared) > 6:
                print(f"      ... and {len(shared) - 6} more")
        print()
        print("Fix by decomposing: one writer per file. If the file must stay whole, agree on who")
        print("owns it and let the others rebase onto that change first. See docs/workflow.md.")
    elif only_overlaps:
        print("no collisions between branches in flight")
    else:
        print("no collisions between branches in flight")

    stale = [(b, staleness(meta[b]["behind"])) for b in sorted(paths)]
    stale = [(b, note) for b, note in stale if note]
    if stale:
        print()
        print("DRIFT: rebase these before they become rewrites")
        for branch, note in stale:
            print(f"  {branch}: {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
