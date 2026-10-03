#!/usr/bin/env python3
"""Tests for the structure check.

Run: python3 tests/test_structure.py

The check reads git's tracked files, so local junk never fails it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_structure import problems  # noqa: E402

TOP = {"docs", "src", "hpc", "README.md"}


def main() -> int:
    failures = []

    def check(name, got, expect_empty=True):
        if (len(got) == 0) != expect_empty:
            failures.append(name)
            print(f"FAIL {name}: {got}")
        else:
            print(f"ok   {name}")

    check("known areas with no components pass", problems(["docs/README.md", "src/README.md"], TOP))
    check("an unknown root entry fails",
          problems(["docs/README.md", "scratch/x.py"], TOP), expect_empty=False)
    check("a component without its own README fails",
          problems(["src/README.md", "src/strat/core.py"], TOP), expect_empty=False)
    check("a documented component passes",
          problems(["src/README.md", "src/strat/README.md", "hpc/slurm/README.md"], TOP))
    check("a stray local file that git ignores never appears here",
          problems(["src/README.md"], TOP))

    print(f"\n{5 - len(failures)}/5 passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
