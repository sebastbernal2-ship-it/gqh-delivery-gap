#!/usr/bin/env python3
"""Report whether strategy promotion is open without opening any sealed window."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from check_strategy_ledger import validate_package  # noqa: E402
from strategy.gates import promotion_gate  # noqa: E402


def rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crosswalk-review", default="results/crosswalk-review.csv")
    parser.add_argument("--crosswalk", default="docs/entity-crosswalk.csv")
    parser.add_argument("--events", default="results/capacity-event-ledger.csv")
    parser.add_argument("--exposures", default="results/issuer-exposure-ledger.csv")
    parser.add_argument("--market-panel", default="results/market-control-panel.csv")
    parser.add_argument("--market-execution", default="results/tradeability-panel.csv")
    parser.add_argument("--physical", default="results/physical-observation-ledger.csv")
    args = parser.parse_args(argv)
    try:
        validate_package(
            {"events": ROOT / args.events,
             "exposures": ROOT / args.exposures,
             "physical": ROOT / args.physical},
            ROOT / args.crosswalk,
            require_verified=True,
        )
    except (OSError, ValueError) as exc:
        print("promotion: CLOSED")
        print(f"  closed: provenance package failed validation: {exc}")
        return 0
    crosswalk = rows(ROOT / args.crosswalk_review)
    verified = sum(int(row.get("pnl_eligible", 0) or 0) for row in crosswalk)
    events = [row for row in rows(ROOT / args.events)
              if row.get("expectation_status") == "measured" and row.get("entity_key") == "issuer:PWR"]
    result = promotion_gate(verified_exposures=verified, measured_expectations=len(events),
                            market_control_rows=len(rows(ROOT / args.market_panel)),
                            tradeability_rows=sum(row.get("trade_status") == "tradeable"
                                                  for row in rows(ROOT / args.market_execution)),
                            physical_rows=len(rows(ROOT / args.physical)))
    print(f"promotion: {result['status']}")
    for reason in result["reasons"]:
        print(f"  closed: {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
