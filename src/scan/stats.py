"""Association statistics with a null that is generated, not assumed.

Two decisions shape everything here.

1. **Changes, not levels.** Two trending series correlate in levels for reasons that have nothing to do
   with each other. The statistic of record is computed on period-to-period changes, with the level
   correlation reported beside it so the difference is visible.
2. **The null is empirical.** A p-value from a formula assumes independence and normality that monthly
   infrastructure data does not have. Instead each pair is measured against its own generated null: a
   **block shuffle** of one series, which keeps short-run autocorrelation and destroys alignment, and a
   **seasonal shift** of twelve months, which keeps seasonality and destroys the calendar match. A pair
   only counts as a candidate if it beats its own placebos, and the number of pairs that do is compared
   with the number expected by chance.

Nothing here decides anything. It produces a calibrated rank and the count of how many pairs were tried.
"""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class PairResult:
    pair: str
    n: int
    level_rho: float
    change_rho: float
    placebo_median: float
    placebo_percentile: float
    seasonal_rho: float
    lead_lag: int
    lead_lag_rho: float

    def beats(self, threshold: float = 0.95) -> bool:
        return self.placebo_percentile >= threshold


def ranks(values: list[float]) -> list[float]:
    """Average ranks, so ties do not distort the correlation."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        average = (i + j) / 2 + 1
        for k in range(i, j + 1):
            out[order[k]] = average
        i = j + 1
    return out


def pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 3 or len(xs) != len(ys):
        return float("nan")
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    sx = sum(d * d for d in dx) ** 0.5
    sy = sum(d * d for d in dy) ** 0.5
    if sx == 0 or sy == 0:
        return float("nan")
    return sum(a * b for a, b in zip(dx, dy)) / (sx * sy)


def spearman(xs: list[float], ys: list[float]) -> float:
    return pearson(ranks(xs), ranks(ys))


def changes(values: list[float]) -> list[float]:
    return [b - a for a, b in zip(values, values[1:])]


def block_shuffle(values: list[float], block: int = 3, rng: random.Random | None = None) -> list[float]:
    """Permute whole blocks, which keeps short-run autocorrelation and destroys alignment."""
    rng = rng or random.Random(0)
    blocks = [values[i:i + block] for i in range(0, len(values), block)]
    rng.shuffle(blocks)
    return [value for chunk in blocks for value in chunk]


def seasonal_shift(values: list[float], months: int = 12) -> list[float]:
    """Shift by a year, which keeps seasonality and destroys the calendar match."""
    if len(values) <= months:
        return list(values)
    return values[months:] + values[:months]


def lead_lag(xs: list[float], ys: list[float], max_lag: int = 3) -> tuple[int, float]:
    """The lag with the strongest association, so a lagged relation is visible rather than hidden."""
    best_lag, best_value = 0, float("nan")
    for lag in range(-max_lag, max_lag + 1):
        if lag == 0:
            a, b = xs, ys
        elif lag > 0:
            a, b = xs[:-lag], ys[lag:]
        else:
            a, b = xs[-lag:], ys[:lag]
        if len(a) < 4:
            continue
        value = spearman(changes(a), changes(b))
        if value == value and (best_value != best_value or abs(value) > abs(best_value)):
            best_lag, best_value = lag, value
    return best_lag, best_value


def measure(pair_label: str, xs: list[float], ys: list[float], draws: int = 200,
            block: int = 3, seed: int = 20261003) -> PairResult:
    """One pair, with its own generated null."""
    if len(xs) < 8 or len(xs) != len(ys):
        return PairResult(pair_label, len(xs), float("nan"), float("nan"), float("nan"),
                          float("nan"), float("nan"), 0, float("nan"))
    level = spearman(xs, ys)
    real = spearman(changes(xs), changes(ys))
    rng = random.Random(seed)
    placebo: list[float] = []
    for _ in range(draws):
        shuffled = block_shuffle(ys, block=block, rng=rng)
        value = spearman(changes(xs), changes(shuffled))
        if value == value:
            placebo.append(value)
    if not placebo:
        return PairResult(pair_label, len(xs), level, real, float("nan"), float("nan"),
                          float("nan"), 0, float("nan"))
    placebo.sort()
    below = sum(1 for value in placebo if abs(value) <= abs(real))
    percentile = below / len(placebo)
    seasonal = spearman(changes(xs), changes(seasonal_shift(ys)))
    lag, lag_rho = lead_lag(xs, ys)
    return PairResult(pair_label, len(xs), level, real, placebo[len(placebo) // 2], percentile,
                      seasonal, lag, lag_rho)


def multiplicity_report(results: list[PairResult], threshold: float = 0.95) -> str:
    """How many pairs beat their own null, against how many should by construction."""
    scored = [r for r in results if r.placebo_percentile == r.placebo_percentile]
    winners = [r for r in scored if r.beats(threshold)]
    expected = len(scored) * (1 - threshold)
    lines = [f"pairs measured: {len(results)}",
             f"pairs with a usable null: {len(scored)}",
             f"pairs beating their own null at {threshold:.0%}: {len(winners)}",
             f"expected by chance at that level: {expected:.1f}",
             ""]
    if winners:
        lines.append("survivors, with their numbers rather than their story:")
        for result in sorted(winners, key=lambda r: -abs(r.change_rho)):
            lines.append(f"  {result.pair:58s} n={result.n:3d} change rho {result.change_rho:+.2f} "
                         f"level rho {result.level_rho:+.2f} percentile {result.placebo_percentile:.2f} "
                         f"seasonal {result.seasonal_rho:+.2f} best lag {result.lead_lag:+d}")
    else:
        lines.append("no pair beat its own null. That is a result, and it belongs in the note.")
    lines.append("")
    lines.append("A survivor is a candidate for a mechanism conversation, never a strategy. Nothing here")
    lines.append("is a position, and the count above is the multiplicity that any reader must apply.")
    return "\n".join(lines)
