#!/usr/bin/env python3
"""Is another BTC capture block needed to reach the declared number of whole UTC dates?

The risk cache needs five whole UTC dates. Each recorded block covers one date, so this counts the
distinct dates already recorded and says whether a block is still due. Used by the systemd unit that
starts a daily block; self-limiting, so the schedule can be left enabled.

    python3 scripts/tape_block_due.py --root data/tape
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATTERN = re.compile(r"btc-(\d{8}T\d{4}Z)$")


def recorded_dates(root: Path) -> list[str]:
    dates = set()
    if not root.exists():
        return []
    for path in root.iterdir():
        match = PATTERN.match(path.name)
        if match and path.is_dir():
            stamp = match.group(1)
            dates.add(f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}")
    return sorted(dates)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "data" / "tape")
    parser.add_argument("--target", type=int, default=5)
    args = parser.parse_args()
    dates = recorded_dates(args.root)
    print(json.dumps({"recorded_dates": dates, "count": len(dates), "target": args.target,
                      "due": len(dates) < args.target}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
