#!/usr/bin/env python3
"""Tests for the ownership check.

Run: python3 tests/test_owners.py

Three teammates pushed inside twenty minutes and OWNERS.md grew three ownership blocks and two
names for one person. The check exists so that drift fails the gate instead of needing a review.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_owners import parse_claims, roster, validate  # noqa: E402

DOC = """# Ownership

## The four of us

| GitHub | Role |
|---|---|
| owner | repo owner |
| alice | invited |

## Claimed paths

| Path | Person | What it is |
|---|---|---|
| `src/a/` | alice | first component |
| `docs/x.md` | owner | a doc |

## Rules
"""


def main() -> int:
    failures = []

    def check(name, got, want):
        if got != want:
            failures.append(name)
            print(f"FAIL {name}:\n  got  {got}\n  want {want}")
        else:
            print(f"ok   {name}")

    claims = parse_claims(DOC)
    check("claims are parsed", sorted(claims), ["docs/x.md", "src/a/"])
    check("roster is parsed", sorted(roster(DOC)), ["alice", "owner"])
    # A clean file passes only when its claimed paths exist, so the happy case supplies them.
    check("a well formed file with existing paths passes",
          validate(DOC, ["alice", "owner"], existing=["docs/x.md", "src/a/README.md"]), [])

    check("a second claim table is reported",
          any("more than one" in p for p in
              validate(DOC + "\n## Another\n\n| Path | Person |\n|---|---|\n| `src/b/` | alice |\n",
                       ["alice", "owner"], existing=[])),
          True)
    check("a duplicate path claim is reported",
          any("claimed twice" in p for p in
              validate(DOC.replace("| `docs/x.md` | owner | a doc |",
                                   "| `docs/x.md` | owner | a doc |\n| `docs/x.md` | alice | again |"),
                       ["alice", "owner"], existing=[])),
          True)
    check("a person outside the roster is reported",
          any("not in the roster" in p for p in
              validate(DOC.replace("| `docs/x.md` | owner |", "| `docs/x.md` | stranger |"),
                       ["alice", "owner"], existing=[])),
          True)
    check("a claimed path that does not exist is reported",
          any("does not exist" in p for p in validate(DOC, ["alice", "owner"], existing=[])),
          True)
    check("a claimed path that exists is fine",
          validate(DOC, ["alice", "owner"], existing=["docs/x.md", "src/a/README.md"]), [])

    print(f"\n{8 - len(failures)}/8 passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
