#!/usr/bin/env python3
"""Tests for the structure check.

Run: python3 tests/test_structure.py
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_structure import problems  # noqa: E402

TOP = {"docs", "src", "hpc", "README.md"}


def build(root: Path, tree: dict) -> None:
    for name, files in tree.items():
        directory = root / name
        directory.mkdir(parents=True, exist_ok=True)
        for f in files or []:
            (directory / f).write_text("x")


def main() -> int:
    failures = []

    def check(name, got, expect_empty=True):
        if (len(got) == 0) != expect_empty:
            failures.append(name)
            print(f"FAIL {name}: {got}")
        else:
            print(f"ok   {name}")

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        build(root, {"src": [], "hpc": [], "docs": [], "README.md": []})
        check("named areas with no components pass", problems(root, TOP, ["src", "hpc"]))

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        build(root, {"src": [], "hpc": [], "docs": [], "README.md": [], "scratch": []})
        check("an unknown root entry fails", problems(root, TOP, ["src", "hpc"]), expect_empty=False)

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        build(root, {"src": [], "hpc": [], "docs": [], "README.md": []})
        build(root, {"src/strat": []})
        check("a component without its own README fails", problems(root, TOP, ["src", "hpc"]),
              expect_empty=False)

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        build(root, {"src": [], "hpc": [], "docs": [], "README.md": []})
        build(root, {"src/strat": ["README.md"], "hpc/slurm": ["README.md"]})
        check("documented components pass", problems(root, TOP, ["src", "hpc"]))

    print(f"\n{4 - len(failures)}/4 passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
