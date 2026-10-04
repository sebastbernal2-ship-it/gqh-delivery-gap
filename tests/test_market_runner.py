#!/usr/bin/env python3
"""Offline check for the market-control and execution-stress runner."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from strategy.market import stress_market_row  # noqa: E402

row = stress_market_row({
    "event_id": "e1", "firm_return": "0.10", "market_return": "0.02", "sector_return": "0.04",
    "gross_return": "0.10", "price": "100", "adv_dollars": "1000000",
    "max_adv_fraction": "0.1", "quantity": "1001", "side": "sell",
    "borrow_available": "false", "spread_bps": "25", "max_spread_bps": "20",
    "entry_cost_bps": "10", "exit_cost_bps": "10", "borrow_bps_per_day": "4",
    "holding_days": "5",
})
assert row["market_abnormal"] == 0.08
assert row["sector_abnormal"] == 0.06
assert row["trade_status"] == "no-trade"
assert "borrow unavailable" in row["no_trade_reasons"]
assert row["double_cost_return"] < row["net_return"]
print("market runner: 4/4 passed")
