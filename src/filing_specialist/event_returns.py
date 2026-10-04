#!/usr/bin/env python3
"""Forward returns around a disclosure, and the statistics that connect a forecast to them.

The bridge between a disclosure-surprise forecast and the only currency that matters: return per
event, net of declared costs. Entry is the close of the first trading day strictly after the
disclosure's availability date, matching the strategy's repaired next-session convention, and exit
is the close H trading days later. Missing data is a null, never a zero.
"""
from __future__ import annotations

import math

HORIZONS = (1, 5, 20)


def forward_return(series: dict[str, float], decision_date: str, horizon: int,
                   entry_date: bool = False):
    """Close-to-close return from the first session after the decision, held `horizon` sessions."""
    days = sorted(series)
    after = [day for day in days if day > decision_date]
    if len(after) < horizon + 1:
        return (math.nan, None) if entry_date else math.nan
    entry, exit_ = after[0], after[horizon]
    if series[entry] <= 0:
        return (math.nan, entry) if entry_date else math.nan
    value = series[exit_] / series[entry] - 1.0
    return (value, entry) if entry_date else value


def attach_returns(rows: list[dict], cache_by_ticker: dict[str, dict[str, float]],
                   horizons: tuple[int, ...] = HORIZONS) -> dict:
    """Add one forward return per horizon to each row, plus a coverage report."""
    covered = 0
    for row in rows:
        series = cache_by_ticker.get(str(row["ticker"]), {})
        decision_date = str(row["label_available"])[:10]
        entry_dates = []
        for horizon in horizons:
            value, entry = forward_return(series, decision_date, horizon, entry_date=True)
            row[f"fwd_ret_{horizon}"] = value
            entry_dates.append(entry)
        row["entry_date"] = entry_dates[0]
        if not math.isnan(row.get(f"fwd_ret_{horizons[-1]}", math.nan)):
            covered += 1
    return {"rows": len(rows), "rows_with_the_longest_horizon": covered,
            "share": round(covered / max(1, len(rows)), 4)}


def rank(values: list[float]) -> list[float]:
    """Average ranks, so ties do not create a spurious ordering."""
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    position = 0
    while position < len(order):
        end = position
        while end + 1 < len(order) and values[order[end + 1]] == values[order[position]]:
            end += 1
        average = (position + end) / 2.0 + 1.0
        for index in range(position, end + 1):
            ranks[order[index]] = average
        position = end + 1
    return ranks


def rank_ic(signal: list[float], outcome: list[float]) -> float:
    """Spearman correlation over the finite pairs."""
    pairs = [(left, right) for left, right in zip(signal, outcome)
             if not math.isnan(left) and not math.isnan(right)]
    if len(pairs) < 3:
        return math.nan
    left = rank([pair[0] for pair in pairs])
    right = rank([pair[1] for pair in pairs])
    mean_left = sum(left) / len(left)
    mean_right = sum(right) / len(right)
    covariance = sum((a - mean_left) * (b - mean_right) for a, b in zip(left, right))
    variance_left = sum((a - mean_left) ** 2 for a in left)
    variance_right = sum((b - mean_right) ** 2 for b in right)
    if variance_left <= 0 or variance_right <= 0:
        return math.nan
    return covariance / math.sqrt(variance_left * variance_right)


def group_means(rows: list[dict], key: str, value_key: str) -> list[dict]:
    """Mean and count of `value_key` by the group label in `key`, groups in ascending order."""
    buckets: dict[object, list[float]] = {}
    for row in rows:
        value = row.get(value_key, math.nan)
        if math.isnan(value):
            continue
        buckets.setdefault(row[key], []).append(value)
    return [{"group": group, "n": len(values), "mean": sum(values) / len(values)}
            for group, values in sorted(buckets.items(), key=lambda item: item[0])]


def long_short(rows: list[dict], horizon: int, top: object, bottom: object,
               cost_bps: float = 0.0, value_key: str | None = None) -> dict:
    """Mean return spread between the top and bottom predicted bins, net of a round-trip cost."""
    value_key = value_key or f"fwd_ret_{horizon}"
    longs = [row[value_key] for row in rows
             if row["predicted_bin"] == top and not math.isnan(row.get(value_key, math.nan))]
    shorts = [row[value_key] for row in rows
              if row["predicted_bin"] == bottom and not math.isnan(row.get(value_key, math.nan))]
    if not longs or not shorts:
        return {"horizon": horizon, "n_long": len(longs), "n_short": len(shorts), "spread": None}
    gross = sum(longs) / len(longs) - sum(shorts) / len(shorts)
    return {"horizon": horizon, "n_long": len(longs), "n_short": len(shorts),
            "mean_long": sum(longs) / len(longs), "mean_short": sum(shorts) / len(shorts),
            "spread": gross, "cost_bps": cost_bps, "net": gross - cost_bps / 1e4}


def quintile_rows(rows: list[dict], horizon: int, value_key: str | None = None) -> list[dict]:
    """Mean return and mean confidence by confidence quintile, coarsest first."""
    value_key = value_key or f"fwd_ret_{horizon}"
    def has(value) -> bool:
        return value is not None and not (isinstance(value, float) and math.isnan(value))

    usable = [row for row in rows
              if has(row.get(value_key)) and has(row.get("confidence"))]
    if len(usable) < 5:
        return []
    usable.sort(key=lambda row: row["confidence"])
    size = len(usable) // 5
    out = []
    for index in range(5):
        start = index * size
        end = len(usable) if index == 4 else (index + 1) * size
        chunk = usable[start:end]
        out.append({"quintile": index + 1, "n": len(chunk),
                    "mean_confidence": sum(row["confidence"] for row in chunk) / len(chunk),
                    "mean_return": sum(row[value_key] for row in chunk) / len(chunk)})
    return out

def blocked_spread_ci(rows: list[dict], horizon: int, top: object, bottom: object,
                      cost_bps: float = 0.0, resamples: int = 1000, seed: int = 20261004,
                      value_key: str | None = None) -> dict:
    """Issuer-blocked interval for the long-short spread, resampling whole issuers."""
    import random

    value_key = value_key or f"fwd_ret_{horizon}"
    by_issuer: dict[str, list[tuple[int, float]]] = {}
    for row in rows:
        value = row.get(value_key, math.nan)
        if math.isnan(value) or row["predicted_bin"] not in (top, bottom):
            continue
        side = 1 if row["predicted_bin"] == top else -1
        by_issuer.setdefault(str(row["ticker"]), []).append((side, value))
    issuers = sorted(by_issuer)
    if len(issuers) < 3:
        return {"point": None, "lower": None, "upper": None, "issuers": len(issuers)}

    def spread(sample: list[str]) -> float | None:
        longs = [value for issuer in sample for side, value in by_issuer[issuer] if side == 1]
        shorts = [value for issuer in sample for side, value in by_issuer[issuer] if side == -1]
        if not longs or not shorts:
            return None
        return sum(longs) / len(longs) - sum(shorts) / len(shorts) - cost_bps / 1e4

    point = spread(issuers)
    rng = random.Random(seed)
    draws = []
    for _ in range(resamples):
        sample = [issuers[rng.randrange(len(issuers))] for _ in range(len(issuers))]
        value = spread(sample)
        if value is not None:
            draws.append(value)
    if not draws:
        return {"point": point, "lower": None, "upper": None, "issuers": len(issuers)}
    draws.sort()
    return {"point": point, "lower": draws[int(0.025 * len(draws))],
            "upper": draws[int(0.975 * len(draws)) - 1], "issuers": len(issuers),
            "share_positive": sum(1 for value in draws if value > 0) / len(draws),
            "resamples": resamples}

def neutralise(rows: list[dict], horizon: int, keys: tuple[str, ...]) -> list[float]:
    """Returns demeaned inside each cell of the declared keys, removing the period and peer trend.

    The disclosure dates cluster, and the AI-capex complex moves together, so a raw spread can be
    a beta or sector trend rather than a surprise effect. Demeaning inside the entry month, and
    inside the entry month crossed with the peer group, removes both.
    """
    value_key = f"fwd_ret_{horizon}"
    buckets: dict[tuple, list[float]] = {}
    for row in rows:
        value = row.get(value_key, math.nan)
        if math.isnan(value):
            continue
        cell = tuple(row.get(key) for key in keys)
        buckets.setdefault(cell, []).append(value)
    means = {cell: sum(values) / len(values) for cell, values in buckets.items()}
    out = []
    for row in rows:
        value = row.get(value_key, math.nan)
        cell = tuple(row.get(key) for key in keys)
        out.append(math.nan if math.isnan(value) else value - means[cell])
    return out


def entry_month(row: dict) -> str | None:
    entry = row.get("entry_date")
    return entry[:7] if entry else None
