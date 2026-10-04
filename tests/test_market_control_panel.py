#!/usr/bin/env python3
"""Offline check for market-control panel construction."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_market_control_panel import build_rows  # noqa: E402

series = {name: {f"2024-01-0{i}": 100 + i for i in range(1, 10)} for name in ("PWR", "SPY", "XLI")}
events = [{"ticker": "PWR", "earliest_availability_utc": "2024-01-01T00:00:00+00:00", "change": "1", "accession": "a", "concept": "x", "period_end": "2023-12-31"}]
rows = build_rows(events, series)
assert len(rows) == 1
assert rows[0]["event_id"] == "market:a:x:2023-12-31"
print("market control panel: 2/2 passed")
