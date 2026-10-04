"""Analytical entry-cost overlay for hypothetical immediate marketable orders."""
from dataclasses import dataclass
import math

import numpy as np

from execution_dataset import HORIZONS
from synchronized_tape import MAX_BOOK_AGE_NS, NS


@dataclass(frozen=True)
class MarketableOrder:
    side: str
    size: float
    horizon_seconds: int
    taker_fee_bps: float

    def __post_init__(self):
        if self.side not in ("buy", "sell"):
            raise ValueError("order side must be buy or sell")
        if type(self.horizon_seconds) is not int or self.horizon_seconds not in HORIZONS:
            raise ValueError("unsupported risk horizon")
        if (isinstance(self.size, bool) or not math.isfinite(self.size) or self.size <= 0
                or isinstance(self.taker_fee_bps, bool) or not math.isfinite(self.taker_fee_bps)
                or self.taker_fee_bps < 0):
            raise ValueError("positive size and explicit nonnegative finite taker fee required")


def validate_book(book, decision_ns):
    if type(decision_ns) is not int or book.event_ns > book.recorded_ns or book.recorded_ns > decision_ns:
        raise ValueError("book must be known by decision time")
    if decision_ns - book.event_ns > MAX_BOOK_AGE_NS:
        raise ValueError("stale entry book")
    if len(book.bids) < 5 or len(book.asks) < 5:
        raise ValueError("five entry-book levels required")
    for levels, reverse in ((book.bids, True), (book.asks, False)):
        if any(not math.isfinite(p) or not math.isfinite(q) or p <= 0 or q <= 0 for p, q in levels):
            raise ValueError("invalid entry-book price or size")
        prices = [p for p, _ in levels]
        if len(set(prices)) != len(prices) or prices != sorted(prices, reverse=reverse):
            raise ValueError("unsorted or duplicate entry-book price")
    if book.bids[0][0] >= book.asks[0][0]:
        raise ValueError("crossed or locked entry book")


def quote_entry(book, order, decision_ns):
    """Walk only the visible top five levels; never assume a residual fill."""
    validate_book(book, decision_ns)
    levels = book.asks[:5] if order.side == "buy" else book.bids[:5]
    if order.size > math.fsum(q for _, q in levels):
        raise ValueError("order exceeds visible top-five liquidity")
    remaining, terms = order.size, []
    for price, available in levels:
        take = min(remaining, available)
        terms.append(take * price)
        remaining -= take
        if remaining <= 0:
            break
    vwap = math.fsum(terms) / order.size
    sign = 1 if order.side == "buy" else -1
    depth_cost = sign * (vwap / book.mid - 1) * 10000
    fee = order.taker_fee_bps * vwap / book.mid
    return {"snapshot_vwap": vwap, "spread_and_depth_bps": depth_cost,
            "fee_bps_on_decision_notional": fee, "entry_cost_bps": depth_cost + fee,
            "fee_rate_bps": order.taker_fee_bps,
            "basis": "hypothetical_immediate_snapshot_walk", "latency_assumption_ms": 0,
            "own_impact_modeled": False, "fill_verified": False}


def validate_sequence_book(sequence, book, decision_ns):
    validate_book(book, decision_ns)
    x = np.asarray(sequence)
    if x.shape != (16, 24) or not np.isfinite(x).all():
        raise ValueError("finite raw 16x24 sequence required")
    total = math.fsum(q for _, q in book.bids[:5] + book.asks[:5])
    expected = []
    for level in range(5):
        for side in (book.bids, book.asks):
            price, size = side[level]
            expected.extend(((price / book.mid - 1) * 10000, size / total))
    expected.append((book.asks[0][0] - book.bids[0][0]) / book.mid * 10000)
    if (not np.allclose(x[-1, :21], expected, rtol=1e-5, atol=1e-5)
            or not np.isclose(x[-1, 23], (decision_ns - book.event_ns) / NS, rtol=1e-5, atol=1e-5)):
        raise ValueError("entry book does not match the model's last sequence state")


def compose_order(risk_quantiles, book, order, decision_ns):
    risk = np.asarray(risk_quantiles, dtype=float)
    if risk.shape != (3, 2, 2, 3) or not np.isfinite(risk).all() or (np.diff(risk, axis=-1) < -1e-6).any():
        raise ValueError("ordered finite risk quantiles required")
    if ((risk[:, :, 1] < 0).any() or (np.diff(risk[:, :, 1], axis=0) < -1e-6).any()
            or (risk[:, :, 1] + 1e-5 < risk[:, :, 0]).any()
            or not np.allclose(risk[:, 0, 0], -risk[:, 1, 0, ::-1], atol=1e-6)):
        raise ValueError("risk quantile geometry mismatch")
    h = HORIZONS.index(order.horizon_seconds)
    side = 0 if order.side == "buy" else 1
    quote = quote_entry(book, order, decision_ns)
    selected = risk[h, side]
    return {"side": order.side, "size": order.size, "horizon_seconds": order.horizon_seconds,
            "quantile_levels": [0.1, 0.5, 0.9], "entry_quote": quote,
            "terminal_markout_loss_quantiles_bps": (selected[0] + quote["entry_cost_bps"]).tolist(),
            "worst_observed_markout_loss_quantiles_bps": (selected[1] + quote["entry_cost_bps"]).tolist(),
            "double_entry_cost_terminal_quantiles_bps": (selected[0] + 2 * quote["entry_cost_bps"]).tolist(),
            "double_entry_cost_worst_observed_quantiles_bps": (selected[1] + 2 * quote["entry_cost_bps"]).tolist(),
            "cost_stress_scope": "double deterministic entry costs; future path unchanged",
            "valuation": "entry-to-mid markout; no exit fees/spread, funding or fill guarantee"}
