"""Read the public perpetual venue tape: book, funding, open interest, oracle and mark.

Everything here is the venue's own public endpoint. No key, no account, no order. The module parses
responses into flat rows and computes the derived quantities the protocol names, so the trigger rule can be
tested offline against recorded rows rather than against a live connection.
"""
from __future__ import annotations

import datetime as dt
from statistics import median, pstdev

INFO_URL = "https://api.hyperliquid.xyz/info"
MARKETS = ("BTC", "ETH", "GAS", "SPX")
TIMEOUT = 20


def book_row(session, coin: str) -> dict | None:
    """One snapshot: best bid and ask, mid, depth within ten basis points, and the imbalance."""
    payload = {"type": "l2Book", "coin": coin}
    response = session.post(INFO_URL, json=payload, timeout=TIMEOUT)
    if response.status_code != 200:
        return None
    body = response.json()
    levels = body.get("levels") or []
    if len(levels) != 2 or not levels[0] or not levels[1]:
        return None
    bids, asks = levels[0], levels[1]
    try:
        best_bid = float(bids[0]["px"])
        best_ask = float(asks[0]["px"])
    except (KeyError, TypeError, ValueError):
        return None
    if best_bid <= 0 or best_ask <= 0:
        return None
    mid = (best_bid + best_ask) / 2.0
    bid_notional = sum(float(level["px"]) * float(level["sz"]) for level in bids
                       if float(level["px"]) >= mid * 0.999)
    ask_notional = sum(float(level["px"]) * float(level["sz"]) for level in asks
                       if float(level["px"]) <= mid * 1.001)
    bid_size = sum(float(level["sz"]) for level in bids)
    ask_size = sum(float(level["sz"]) for level in asks)
    total = bid_size + ask_size
    return {"time": body.get("time"), "coin": coin, "mid": mid, "best_bid": best_bid,
            "best_ask": best_ask, "spread_bps": (best_ask - best_bid) / mid * 1e4,
            "depth_bid_notional": bid_notional, "depth_ask_notional": ask_notional,
            "imbalance": (bid_size - ask_size) / total if total else 0.0}


def context_rows(session) -> list[dict]:
    """Funding, open interest, oracle and mark price for every market the venue lists."""
    response = session.post(INFO_URL, json={"type": "metaAndAssetCtxs"}, timeout=TIMEOUT)
    if response.status_code != 200:
        return []
    universe, contexts = response.json()
    out = []
    for meta, ctx in zip(universe.get("universe", []), contexts):
        coin = meta.get("name")
        if coin not in MARKETS:
            continue
        try:
            mark = float(ctx.get("markPx"))
            oracle = float(ctx.get("oraclePx"))
            open_interest = float(ctx.get("openInterest"))
            funding = float(ctx.get("funding"))
        except (TypeError, ValueError):
            continue
        out.append({"coin": coin, "mark": mark, "oracle": oracle, "funding": funding,
                    "open_interest": open_interest,
                    "basis_bps": (mark - oracle) / oracle * 1e4 if oracle else 0.0})
    return out


def returns(mids: list[float]) -> list[float]:
    return [(b - a) / a for a, b in zip(mids, mids[1:]) if a]


def trigger(mids: list[float], open_interest: list[float], window: int = 60,
            sigma_multiple: float = 3.0, oi_drop: float = 0.01) -> bool:
    """The declared conjunction: a large move and an open interest fall in the same sample."""
    if len(mids) < window + 1 or len(open_interest) < window + 1:
        return False
    step = mids[-1] / mids[-2] - 1.0
    history = returns(mids[-(window + 1):-1])
    if not history or len(history) < 10:
        return False
    sigma = pstdev(history)
    if sigma == 0:
        return False
    large_move = abs(step) > sigma_multiple * sigma
    recent = median(open_interest[-window - 1:-1])
    fell = recent > 0 and (open_interest[-1] - recent) / recent <= -oi_drop
    return bool(large_move and fell)


def count_overdispersion(counts: list[int]) -> dict:
    """Compare trigger counts per bucket with a Poisson null: the declared clustering test."""
    if len(counts) < 3:
        return {"buckets": len(counts), "mean": None, "variance": None, "overdispersed": None}
    mean = sum(counts) / len(counts)
    variance = sum((c - mean) ** 2 for c in counts) / (len(counts) - 1)
    return {"buckets": len(counts), "mean": mean, "variance": variance,
            "overdispersed": bool(variance > mean * 1.5)}


def refractory_excess(gaps: list[float]) -> dict | None:
    """Short intervals should be rarer than exponential if firing needs a refractory period."""
    if len(gaps) < 5:
        return None
    mean = sum(gaps) / len(gaps)
    if mean <= 0:
        return None
    expected_short = (1 - pow(2.718281828459045, -0.5)) * len(gaps)
    observed_short = sum(1 for gap in gaps if gap <= mean / 2)
    return {"gaps": len(gaps), "mean": mean, "expected_short": expected_short,
            "observed_short": observed_short}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
