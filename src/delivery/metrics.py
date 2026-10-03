"""Delivery-gap metrics.

The state variable is the transport cost between two distributions over delivery
dates, in months, MW weighted. In one dimension the optimal transport cost has a
closed form: W1 is the integral of the absolute CDF difference, equivalently the
MW weighted mean absolute delay, and W2 is the MW weighted root mean square delay.
No solver is needed here, and none is used. The multi-marginal Sinkhorn work lives
in the coupling engine, where the marginals are option smiles, not schedules.

Conventions:
  delay = realized month index - promised month index
  positive delay means the unit arrived later than promised
  cancellations are reported as their own number and never folded into the delay
"""
from __future__ import annotations


def _weighted_quantile(values, weights, q):
    """MW weighted quantile, midpoint-position linear convention.

    Each unit sits at (weight before it + half its own weight) / total. The quantile
    interpolates linearly between the two units that bracket q. With equal weights
    this is the usual interpolated percentile.
    """
    if not values:
        return 0.0
    total = float(sum(weights))
    if total <= 0:
        order = sorted(values)
        pos = q * (len(order) - 1)
        lower = int(pos)
        upper = min(lower + 1, len(order) - 1)
        return float(order[lower] + (order[upper] - order[lower]) * (pos - lower))

    order = sorted(range(len(values)), key=lambda i: values[i])
    running = 0.0
    positions = []
    for i in order:
        w = float(weights[i])
        positions.append(((running + 0.5 * w) / total, float(values[i])))
        running += w

    if q <= positions[0][0]:
        return positions[0][1]
    if q >= positions[-1][0]:
        return positions[-1][1]
    for k in range(1, len(positions)):
        p0, v0 = positions[k - 1]
        p1, v1 = positions[k]
        if q <= p1:
            if p1 == p0:
                return v1
            return float(v0 + (v1 - v0) * (q - p0) / (p1 - p0))
    return positions[-1][1]


def transport_cost(pairs, canceled_mw: float = 0.0) -> dict:
    """Transport cost between promised and realized delivery dates.

    pairs: list of {"promised": int, "realized": int, "mw": float}
    canceled_mw: MW that was promised and then cancelled or postponed
    """
    delays = []
    weights = []
    mw_arrived = 0.0
    for item in pairs:
        mw = float(item.get("mw", 0.0) or 0.0)
        delays.append(int(item["realized"]) - int(item["promised"]))
        weights.append(mw)
        mw_arrived += mw

    n = len(pairs)
    if n == 0:
        w1 = w2 = median = p90 = 0.0
    else:
        total = sum(weights)
        if total <= 0:
            w1 = sum(abs(d) for d in delays) / n
            w2 = (sum(d * d for d in delays) / n) ** 0.5
        else:
            w1 = sum(abs(d) * w for d, w in zip(delays, weights)) / total
            w2 = (sum(d * d * w for d, w in zip(delays, weights)) / total) ** 0.5
        median = _weighted_quantile(delays, weights, 0.5)
        p90 = _weighted_quantile(delays, weights, 0.9)

    denom = mw_arrived + float(canceled_mw or 0.0)
    return {
        "n_units": n,
        "mw_total": mw_arrived,
        "mw_cancelled": float(canceled_mw or 0.0),
        "cancelled_share": (float(canceled_mw or 0.0) / denom) if denom > 0 else 0.0,
        "w1_months": w1,
        "w2_months": w2,
        "median_delay_months": median,
        "p90_delay_months": p90,
        "mean_delay_months": (sum(d * w for d, w in zip(delays, weights)) / sum(weights))
        if weights and sum(weights) > 0 else 0.0,
    }
