#!/usr/bin/env python3
"""The market-state specialist: what the market already says before a disclosure.

A different information bundle from the filing family. The filings bundle reads what the issuer
said; this bundle reads what the tape did into the decision, in absolute terms, in volatility
terms, and relative to the issuer's own peer group. It answers one declared question: does the
pre-disclosure market state carry information about the next disclosure surprise?

Point-in-time rule: every feature uses bars dated strictly before the decision date, so the
decision-day close, the disclosure reaction and everything after it are excluded by construction.
Insufficient history is a null, never a zero.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

CACHE = Path(__file__).resolve().parents[2] / "results" / "bar-cache"
MARKET_FEATURES = (
    "market_return_60",
    "market_return_252",
    "market_vol_60",
    "market_drift_5",
    "market_distance_high_252",
    "market_peer_relative_60",
    "market_peer_relative_5",
)


def load_series(ticker: str, cache: Path = CACHE) -> dict[str, float]:
    path = cache / f"{ticker}.json"
    if not path.exists():
        return {}
    series = json.loads(path.read_text())
    if not isinstance(series, dict):
        return {}
    return {str(day): float(value) for day, value in series.items() if value is not None}


def window(series: dict[str, float], decision_date: str) -> tuple[list[str], list[float]]:
    """Closes strictly before the decision date, in date order."""
    days = sorted(day for day in series if day < decision_date)
    return days, [series[day] for day in days]


def trailing_return(closes: list[float], days: int) -> float:
    if len(closes) < days + 1 or closes[-days - 1] <= 0:
        return math.nan
    return closes[-1] / closes[-days - 1] - 1.0


def realized_vol(closes: list[float], days: int) -> float:
    if len(closes) < days + 1:
        return math.nan
    window_closes = closes[-days - 1:]
    returns = [window_closes[index + 1] / window_closes[index] - 1.0
               for index in range(len(window_closes) - 1) if window_closes[index] > 0]
    if len(returns) < 2:
        return math.nan
    mean = sum(returns) / len(returns)
    variance = sum((value - mean) ** 2 for value in returns) / (len(returns) - 1)
    return math.sqrt(variance) * math.sqrt(252.0)


def distance_from_high(closes: list[float], days: int) -> float:
    if not closes:
        return math.nan
    peak = max(closes[-days:])
    if peak <= 0:
        return math.nan
    return closes[-1] / peak - 1.0


def group_of(row: dict, groups: tuple[str, ...]) -> str | None:
    for group in groups:
        if float(row.get(f"group_{group}") or 0.0) >= 0.5:
            return group
    return None


def feature_row(row: dict, series: dict[str, float], peer_returns: dict[str, float]) -> dict:
    decision_date = str(row["label_available"])[:10]
    _, closes = window(series, decision_date)
    own60 = trailing_return(closes, 60)
    own5 = trailing_return(closes, 5)
    peer60 = peer_returns.get("return_60", math.nan)
    peer5 = peer_returns.get("return_5", math.nan)
    return {
        "market_return_60": own60,
        "market_return_252": trailing_return(closes, 252),
        "market_vol_60": realized_vol(closes, 60),
        "market_drift_5": own5,
        "market_distance_high_252": distance_from_high(closes, 252),
        "market_peer_relative_60": own60 - peer60 if not math.isnan(peer60) else math.nan,
        "market_peer_relative_5": own5 - peer5 if not math.isnan(peer5) else math.nan,
    }


def build(rows: list[dict], cache: Path = CACHE, groups: tuple[str, ...] =
          ("datacenter", "equipment", "utility", "contractor")) -> tuple[list[dict], dict]:
    """One feature row per panel row, aligned by position, plus a coverage report."""
    by_ticker: dict[str, list[int]] = {}
    for index, row in enumerate(rows):
        by_ticker.setdefault(str(row["ticker"]), []).append(index)

    series = {ticker: load_series(ticker, cache) for ticker in by_ticker}
    group_of_ticker = {ticker: group_of(rows[indexes[0]], groups)
                       for ticker, indexes in by_ticker.items()}

    def peer_medians(index: int) -> dict[str, float]:
        ticker = str(rows[index]["ticker"])
        group = group_of_ticker.get(ticker)
        if group is None:
            return {}
        decision_date = str(rows[index]["label_available"])[:10]
        values: dict[str, list[float]] = {"return_60": [], "return_5": []}
        for peer, peer_indexes in by_ticker.items():
            if peer == ticker or group_of_ticker.get(peer) != group:
                continue
            _, closes = window(series[peer], decision_date)
            for key, days in (("return_60", 60), ("return_5", 5)):
                value = trailing_return(closes, days)
                if not math.isnan(value):
                    values[key].append(value)
        medians = {}
        for key, pool in values.items():
            if pool:
                pool = sorted(pool)
                middle = len(pool) // 2
                medians[key] = pool[middle] if len(pool) % 2 else 0.5 * (pool[middle - 1] + pool[middle])
        return medians

    features = [feature_row(row, series[str(row["ticker"])], peer_medians(index))
                for index, row in enumerate(rows)]
    coverage = {}
    for name in MARKET_FEATURES:
        finite = sum(1 for row in features if not math.isnan(row[name]))
        coverage[name] = {"finite": finite, "rows": len(rows), "share": round(finite / max(1, len(rows)), 4)}
    return features, coverage
