#!/usr/bin/env python3
"""Offline checks for crosswalk review reporting."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from review_crosswalk import review  # noqa: E402

assert review([])[0]["status"] == "empty"
row = {"entity_name": "A", "ticker": "PWR", "cik": "1", "direction": "negative",
       "weight": "0.5", "evidence": "filing:1", "identity_vintage": "2024Q1",
       "source_receipt": "sec:1", "status": "verified"}
assert review([row])[0]["pnl_eligible"] == 1
assert review([{**row, "evidence": "", "status": "verified"}])[0]["missing_required"] == 1
print("crosswalk review: 3/3 passed")
