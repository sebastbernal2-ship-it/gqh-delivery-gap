#!/usr/bin/env python3
"""Stage 2b: one frame per quarter for the two driver concepts, cached under the ignored cache.

Duration frames (no I suffix) carry every filer's value for that quarter with the accession that
reported it, so the same acceptance-clock join as the RPO panel applies.

    python3 scripts/fetch_driver_frames.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_rpo_universe import FRAMES, CACHE, fetch_json  # noqa: E402

CONCEPTS = ("RevenueFromContractWithCustomerExcludingAssessedTax",
            "PaymentsToAcquirePropertyPlantAndEquipment")


def quarters(start_year: int, end_year: int) -> list[str]:
    return [f"CY{year}Q{quarter}" for year in range(start_year, end_year + 1)
            for quarter in range(1, 5)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=2017)
    parser.add_argument("--end-year", type=int, default=2025)
    args = parser.parse_args()
    summary = {}
    for concept in CONCEPTS:
        rows_total = 0
        for period in quarters(args.start_year, args.end_year):
            url = FRAMES.format(concept=concept, period=period)
            payload = fetch_json(url, CACHE)
            data = payload.get("data", []) if payload else []
            rows_total += len(data)
            print(f"  {concept[:28]:28s} {period}: {len(data):5d} filers", flush=True)
        summary[concept] = rows_total
    print(json.dumps({"frame_rows_by_concept": summary}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
