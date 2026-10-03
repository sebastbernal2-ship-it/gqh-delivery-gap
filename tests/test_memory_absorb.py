#!/usr/bin/env python3
"""Tests for the absorb diff: which shared entries are missing locally.

Run: python3 tests/test_memory_absorb.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from memory_absorb import missing_entries, union_entries  # noqa: E402


def shared(content, tags=("gqh",)):
    return {"id": "x", "content": content, "tags": list(tags)}


def local(content):
    return {"id": "y", "content": content, "tags": ["quanthacks"]}


def main() -> int:
    failures = []

    def check(name, got, want):
        if got != want:
            failures.append(name)
            print(f"FAIL {name}: got {got!r} want {want!r}")
        else:
            print(f"ok   {name}")

    check("all new", [s["content"] for s in missing_entries([shared("a"), shared("b")], [])], ["a", "b"])
    check("none new", missing_entries([shared("a")], [local("a")]), [])
    check("partial", [s["content"] for s in missing_entries([shared("a"), shared("b")], [local("a")])], ["b"])
    check("whitespace is normalized",
          missing_entries([shared("  a  \n")], [local("a")]), [])
    check("case is not ignored",
          [s["content"] for s in missing_entries([shared("A")], [local("a")])], ["A"])
    check("duplicate shared entries collapse",
          [s["content"] for s in missing_entries([shared("a"), shared("a")], [])], ["a"])

    # The shared file is a union across devices. A device that cannot see an entry
    # locally must not delete it from the file when it shares.
    check("union keeps what the local store lacks",
          len(union_entries([shared("from another device")], [shared("mine")])), 2)
    check("union does not duplicate the same content",
          len(union_entries([shared("same")], [shared("same")])), 1)
    check("union normalises whitespace when comparing",
          len(union_entries([shared("  same  ")], [shared("same")])), 1)

    print(f"\n{9 - len(failures)}/9 passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
