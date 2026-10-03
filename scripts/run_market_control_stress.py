#!/usr/bin/env python3
"""Run market controls, cost doubling, capacity, and no-trade rules on a return ledger."""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from strategy.market import stress_market_row  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", default="results/market-control-stress.csv")
    args = parser.parse_args(argv)
    with (ROOT / args.input).open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SystemExit("return ledger is empty")
    output = [stress_market_row(row) for row in rows]
    fields = list(output[0])
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(output)
    print(f"wrote {args.out} ({len(output)} rows)")
    print(f"no-trade rows: {sum(row['trade_status'] == 'no-trade' for row in output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
