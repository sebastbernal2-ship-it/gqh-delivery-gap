"""Control the false discovery rate instead of counting threshold crossings.

Our threshold count answered "how many pairs beat their own null at 95 percent", and compared it with 5
percent of the pair count. That is a useful sanity check and a poor decision rule: with two hundred pairs,
ten threshold crossings are expected by construction, and the rule cannot tell you which.

Benjamini-Hochberg answers the question a reader actually has: **if we act on the survivors, what share of
them should we expect to be false.** It works from the same calibrated p-values the scan already produces,
so it costs nothing beyond arithmetic, and it is stricter as the pair count grows, which is the property
we want when the node space expands.
"""
from __future__ import annotations


def p_values(rows: list[dict]) -> list[tuple[str, float]]:
    """One calibrated p-value per measured pair, from the percentile of its own null."""
    out: list[tuple[str, float]] = []
    for row in rows:
        percentile = row.get("placebo_percentile")
        if row.get("coverage") != "measured" or percentile in (None, "", "None"):
            continue
        try:
            value = float(percentile)
        except (TypeError, ValueError):
            continue
        if value != value:
            continue
        # The percentile is the share of shuffled draws with a weaker association, so the calibrated
        # p-value for a two sided test is the share at least as strong, which is one minus that.
        out.append((str(row.get("pair")), max(0.0, min(1.0, 1.0 - value))))
    return out


def benjamini_hochberg(pairs: list[tuple[str, float]], rate: float = 0.10) -> dict:
    """Which pairs survive at the given false discovery rate, and the threshold that admits them."""
    if not pairs:
        return {"survivors": [], "threshold": 0.0, "tested": 0, "expected_false": 0.0}
    ordered = sorted(pairs, key=lambda item: item[1])
    total = len(ordered)
    threshold_index = 0
    for index, (_, p) in enumerate(ordered, start=1):
        if p <= rate * index / total:
            threshold_index = index
    survivors = [name for name, _ in ordered[:threshold_index]]
    threshold = ordered[threshold_index - 1][1] if threshold_index else 0.0
    return {"survivors": survivors, "threshold": threshold, "tested": total,
            "expected_false": rate * threshold_index if threshold_index else 0.0}


def report(pairs: list[tuple[str, float]], rate: float = 0.10) -> str:
    result = benjamini_hochberg(pairs, rate)
    lines = [f"calibrated p-values available for {result['tested']} pairs",
             f"surviving a false discovery rate of {rate:.0%}: {len(result['survivors'])}",
             f"p-value threshold that admits them: {result['threshold']:.3f}",
             f"expected false among them: {result['expected_false']:.2f}"]
    for name in result["survivors"][:10]:
        lines.append(f"  {name}")
    if not result["survivors"]:
        lines.append("  none. With this many pairs, a threshold count of survivors is not evidence.")
    return "\n".join(lines)
