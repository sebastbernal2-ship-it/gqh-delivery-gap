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
