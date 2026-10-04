"""Market controls and explicit execution stress calculations."""
from __future__ import annotations

from typing import Mapping

from strategy.tradeability import capacity_shares, cost_scenarios, no_trade_reasons


def controlled_returns(firm_return: float, market_return: float, sector_return: float) -> dict[str, float]:
    """Report market and sector abnormal returns without selecting a winner."""
    return {
        "market_abnormal": round(firm_return - market_return, 12),
        "sector_abnormal": round(firm_return - sector_return, 12),
    }


def stress_market_row(row: Mapping[str, object]) -> dict[str, object]:
    """Apply controls, doubled costs, liquidity capacity, and no-trade rules to one row."""
    firm = float(row["firm_return"])
    market = float(row["market_return"])
    sector = float(row["sector_return"])
    price = float(row["price"])
    adv = float(row["adv_dollars"])
    max_fraction = float(row.get("max_adv_fraction", 0.1))
    capacity = capacity_shares(price, adv, max_fraction,
                               float(row["max_position_dollars"]) if row.get("max_position_dollars") else None)
    quantity = float(row["quantity"])
    reasons = no_trade_reasons(
        str(row["side"]), str(row.get("borrow_available", "false")).lower() in {"true", "1", "yes"},
        capacity, quantity, float(row["spread_bps"]), float(row["max_spread_bps"])
    )
    costs = cost_scenarios(float(row["gross_return"]), float(row["entry_cost_bps"]),
                           float(row["exit_cost_bps"]), float(row.get("borrow_bps_per_day", 0)),
                           int(row.get("holding_days", 0)))
    out = dict(row)
    out.update(controlled_returns(firm, market, sector))
    out.update({"capacity_shares": capacity, "trade_status": "no-trade" if reasons else "tradeable",
                "no_trade_reasons": ";".join(reasons), "net_return": costs["net"],
                "double_cost_return": costs["double"]})
    return out
