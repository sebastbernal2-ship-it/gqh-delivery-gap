#!/usr/bin/env python3
"""Write an explicit no-trade report when execution evidence is absent."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ["event_id", "security", "signal_at", "side", "quantity", "capacity_shares",
          "trade_status", "no_trade_reasons", "borrow_status", "spread_status",
          "liquidity_status", "source_receipt"]


def build_rows(rows: list[dict]) -> list[dict]:
    return [{
        "event_id": row["event_id"], "security": row.get("ticker", "PWR"),
        "signal_at": row.get("available", ""), "side": "sell", "quantity": "1",
        "capacity_shares": "0", "trade_status": "no-trade",
        "no_trade_reasons": "borrow unavailable;spread unavailable;liquidity unavailable",
        "borrow_status": "missing", "spread_status": "missing",
        "liquidity_status": "missing",
        "source_receipt": row.get("source_receipt", ""),
    } for row in rows]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="results/market-control-panel.csv")
    parser.add_argument("--out", default="results/tradeability-panel.csv")
    args = parser.parse_args(argv)
    with (ROOT / args.input).open(newline="") as handle:
        output = build_rows(list(csv.DictReader(handle)))
    out = ROOT / args.out
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader(); writer.writerows(output)
    print(f"wrote {args.out} ({len(output)} no-trade rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
