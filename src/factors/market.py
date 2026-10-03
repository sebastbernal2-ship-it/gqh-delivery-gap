"""Fuel and rate levels, as the cost side of building.

Both come from cached daily bars, reduced to monthly means. A month's mean is knowable at the end of that
month, which is how the panel consumes it: factors for a decision in month t come from t-1.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BARS = ROOT / "results" / "bar-cache"

TICKERS = {"gas": "NG=F", "copper": "HG=F", "ten_year": "^TNX"}


def monthly_mean(ticker: str) -> dict[str, float]:
    path = BARS / f"{ticker}.json"
    if not path.exists():
        return {}
    try:
        closes = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    by_month: dict[str, list[float]] = {}
    for stamp, value in closes.items():
        try:
            by_month.setdefault(stamp[:7], []).append(float(value))
        except (TypeError, ValueError):
            continue
    return {month: sum(values) / len(values) for month, values in by_month.items() if values}


def levels() -> dict[str, dict[str, float]]:
    return {name: monthly_mean(ticker) for name, ticker in TICKERS.items()}


def known_at(month: str, series: dict[str, float]):
    """The previous month's value, which is what a decision in this month may use."""
    year, number = (int(part) for part in month.split("-"))
    total = year * 12 + number - 2
    return series.get(f"{total // 12:04d}-{total % 12 + 1:02d}")
