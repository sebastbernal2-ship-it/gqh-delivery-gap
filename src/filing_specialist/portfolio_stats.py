#!/usr/bin/env python3
"""Portfolio statistics and month-blocked intervals, shared by the stage runners.

One owner for the arithmetic that turns a daily net series into annualised return, volatility,
Sharpe and drawdown, and for the interval that resamples whole calendar months so overlapping
positions cannot manufacture significance.
"""
from __future__ import annotations

import math
import random
import statistics


def portfolio_metrics(daily: list[dict], value_key: str = "net") -> dict:
    """Annualised return, volatility, Sharpe, drawdown and hit rate from one daily series."""
    values = [row[value_key] for row in daily]
    if not values:
        return {"days": 0}
    mean = statistics.mean(values)
    deviation = statistics.pstdev(values) if len(values) > 1 else 0.0
    cumulative, peak, drawdown = 1.0, 1.0, 0.0
    for value in values:
        cumulative *= 1 + value
        peak = max(peak, cumulative)
        drawdown = min(drawdown, cumulative / peak - 1)
    positives = sum(1 for value in values if value > 0)
    return {
        "days": len(values),
        "annual_return": mean * 252,
        "annual_vol": deviation * math.sqrt(252),
        "sharpe": (mean / deviation * math.sqrt(252)) if deviation else None,
        "total_return": cumulative - 1,
        "max_drawdown": drawdown,
        "hit_rate": positives / len(values),
    }


def month_blocked_interval(left: list[dict], right: list[dict], value_key: str = "net",
                           resamples: int = 1000, seed: int = 20261004) -> dict:
    """Percentile interval for the annualised difference, resampling whole calendar months."""
    def mean_by_month(rows: list[dict]) -> dict[str, float]:
        buckets: dict[str, list[float]] = {}
        for row in rows:
            buckets.setdefault(row["date"][:7], []).append(row[value_key])
        return {month: statistics.mean(values) for month, values in buckets.items()}

    left_months, right_months = mean_by_month(left), mean_by_month(right)
    months = sorted(set(left_months) & set(right_months))
    if len(months) < 6:
        return {"point": None, "lower": None, "upper": None, "months": len(months)}
    point = (statistics.mean(left_months[m] for m in months)
             - statistics.mean(right_months[m] for m in months)) * 252
    rng = random.Random(seed)
    draws = []
    for _ in range(resamples):
        sample = [months[rng.randrange(len(months))] for _ in range(len(months))]
        draws.append((statistics.mean(left_months[m] for m in sample)
                      - statistics.mean(right_months[m] for m in sample)) * 252)
    draws.sort()
    return {"point": point, "lower": draws[int(0.025 * len(draws))],
            "upper": draws[int(0.975 * len(draws)) - 1], "months": len(months),
            "share_positive": sum(1 for value in draws if value > 0) / len(draws),
            "resamples": resamples}


if __name__ == "__main__":
    raise SystemExit("import me")
