"""Small execution calculations for the daily pilot."""
from __future__ import annotations

import math


def net_return(gross_return: float, entry_cost_bps: float, exit_cost_bps: float,
               borrow_bps_per_day: float = 0.0, holding_days: int = 0) -> float:
    """Subtract entry, exit, and per-day borrow costs from a gross return."""
    values = (gross_return, entry_cost_bps, exit_cost_bps, borrow_bps_per_day)
    if any(not math.isfinite(float(value)) for value in values):
        raise ValueError("returns and costs must be finite")
    if any(float(value) < 0 for value in values[1:]) or holding_days < 0:
        raise ValueError("costs and holding days must be nonnegative")
    total_bps = entry_cost_bps + exit_cost_bps + borrow_bps_per_day * holding_days
    return gross_return - total_bps / 10_000


def capacity_shares(price: float, adv_dollars: float, max_adv_fraction: float = 0.1,
                    max_position_dollars: float | None = None) -> int:
    """Return the integer share capacity allowed by liquidity and optional position limits."""
    values = (price, adv_dollars, max_adv_fraction)
    if any(not math.isfinite(float(value)) for value in values):
        raise ValueError("capacity inputs must be finite")
    if price <= 0 or adv_dollars < 0 or not 0 <= max_adv_fraction <= 1:
        raise ValueError("invalid capacity inputs")
    dollars = adv_dollars * max_adv_fraction
    if max_position_dollars is not None:
        if not math.isfinite(float(max_position_dollars)) or max_position_dollars < 0:
            raise ValueError("invalid position limit")
        dollars = min(dollars, max_position_dollars)
    return int(dollars // price)


def no_trade_reasons(side: str, borrow_available: bool, capacity: int, quantity: float,
                     spread_bps: float, max_spread_bps: float) -> list[str]:
    """Return every mechanical reason a proposed trade must not be sent."""
    if side not in {"buy", "sell"}:
        raise ValueError("unknown trade side")
    if capacity < 0 or quantity < 0 or not all(math.isfinite(float(value))
                                                for value in (capacity, quantity, spread_bps, max_spread_bps)):
        raise ValueError("invalid no-trade inputs")
    if spread_bps < 0 or max_spread_bps < 0:
        raise ValueError("spreads must be nonnegative")
    reasons = []
    if side == "sell" and not borrow_available:
        reasons.append("borrow unavailable")
    if quantity > capacity:
        reasons.append("quantity exceeds capacity")
    if spread_bps > max_spread_bps:
        reasons.append("spread exceeds limit")
    return reasons


def cost_scenarios(gross_return: float, entry_cost_bps: float, exit_cost_bps: float,
                   borrow_bps_per_day: float = 0.0, holding_days: int = 0) -> dict[str, float]:
    """Return base and doubled explicit-cost scenarios."""
    return {
        "net": net_return(gross_return, entry_cost_bps, exit_cost_bps,
                           borrow_bps_per_day, holding_days),
        "double": net_return(gross_return, entry_cost_bps * 2, exit_cost_bps * 2,
                              borrow_bps_per_day * 2, holding_days),
    }
