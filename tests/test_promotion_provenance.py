#!/usr/bin/env python3
"""Offline tests for the promotion provenance helper."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from check_strategy_ledger import validate_crosswalk  # noqa: E402


GOOD = {
    "entity_name": "QUANTA SERVICES, INC.",
    "ticker": "PWR",
    "cik": "1050915",
    "direction": "neutral",
    "weight": "1.0",
    "evidence": "SEC company facts",
    "identity_vintage": "2018-03-31",
    "source_receipt": "https://data.sec.gov/api/xbrl/companyfacts/CIK0001050915.json",
    "status": "verified",
}

assert validate_crosswalk([GOOD], require_verified=True) == 1
try:
    validate_crosswalk([{**GOOD, "source_receipt": ""}], require_verified=True)
except ValueError as exc:
    assert "source_receipt" in str(exc)
else:
    raise AssertionError("missing provenance must fail")
print("promotion provenance: 2/2 passed")
