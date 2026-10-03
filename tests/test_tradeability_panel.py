#!/usr/bin/env python3
"""Offline check for explicit no-trade reporting."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_tradeability_panel import build_rows  # noqa: E402
rows = build_rows([{"event_id": "e1", "ticker": "PWR", "available": "2024-01-01", "source_receipt": "m"}])
assert rows[0]["trade_status"] == "no-trade"
assert "borrow unavailable" in rows[0]["no_trade_reasons"]
print("tradeability panel: 2/2 passed")
