#!/usr/bin/env python3
"""Seed the gitignored price cache from the committed subset, so a fresh clone can run the tests.

The repository commits the 66 price series its results actually read, under `results/price-subset/`.
The engine and several contracts read the full cache path `results/bar-cache/`, which is ignored because
it is 62 MB of data on a developer machine. This copies the subset into that path when a series is
missing and never overwrites an existing file, so it is safe to run before anything else.

    python3 scripts/seed_price_cache.py [--quiet]
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUBSET = ROOT / "results" / "price-subset"
CACHE = ROOT / "results" / "bar-cache"


def seed(quiet: bool = False) -> int:
    if not SUBSET.exists():
        if not quiet:
            print("no committed price subset at", SUBSET)
        return 0
    CACHE.mkdir(parents=True, exist_ok=True)
    copied = 0
    for path in sorted(SUBSET.glob("*.json")):
        if path.name == "manifest.json":
            continue
        target = CACHE / path.name
        if not target.exists():
            shutil.copyfile(path, target)
            copied += 1
    if not quiet:
        total = len([path for path in CACHE.glob("*.json")])
        print(f"seeded {copied} series from the committed subset; the cache now holds {total}")
    return copied


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    seed(args.quiet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
