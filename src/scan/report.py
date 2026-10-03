"""Two corrections that stop a scan from reporting its own multiplicity as a discovery.

**Correction one: one series per node.** A node declared with three representations contributed three
correlated series, so it could vote three times in the same direction. The canonical pass keeps one
representation per node and reports what survives.

**Correction two: family and specificity.** A correlation between two risk assets is not news, so pairs
inside a family are counted separately from pairs across families. And if a survivor involves firm
disclosures, the same statistic is recomputed for each industry group: a relation that appears in
unrelated industries is a common factor, not the mechanism, and it must be reported that way.
"""
from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from pathlib import Path

CANONICAL = {
    "promise:power:planned-capacity-revision": "promise_next_year_revision",
    "firm:obligation:remaining-performance": "firm_share_negative_revision",
}

# The industries the mechanism is about, against the one that is measured for comparison.
MECHANISM_GROUPS = {"contractor", "equipment"}
COMPARISON_GROUP = {"datacenter"}


def canonical(rows: list[dict]) -> list[dict]:
    """One representation per node, so a node cannot vote three times."""
    return [row for row in rows
            if (row["a"] not in CANONICAL or row.get("series_a") == CANONICAL[row["a"]])
            and (row["b"] not in CANONICAL or row.get("series_b") == CANONICAL[row["b"]])]


def family_of(nodes: dict[str, dict], node_id: str) -> str:
    return nodes.get(node_id, {}).get("family", "?")


def family_counts(rows: list[dict], nodes: dict[str, dict], threshold: float = 0.95) -> dict:
    same, cross, cross_survivors, same_survivors = 0, 0, 0, 0
    for row in rows:
        percentile = row.get("placebo_percentile")
        try:
            percentile = float(percentile)
        except (TypeError, ValueError):
            continue
        inside = family_of(nodes, row["a"]) == family_of(nodes, row["b"])
        if inside:
            same += 1
            same_survivors += percentile >= threshold
        else:
            cross += 1
            cross_survivors += percentile >= threshold
    return {"same_family": same, "cross_family": cross, "same_survivors": same_survivors,
            "cross_survivors": cross_survivors,
            "expected_cross": cross * (1 - threshold), "expected_same": same * (1 - threshold)}


def firm_group_series(events_path: Path, groups: set[str]) -> dict[str, float]:
    """Share of firms in the given groups whose reported obligation fell, by month it became public."""
    by_month: dict[str, list[float]] = defaultdict(list)
    with events_path.open() as handle:
        for row in csv.DictReader(handle):
            if row.get("group") not in groups:
                continue
            if str(row.get("in_sealed_window", "")).lower() in ("true", "1"):
                continue
            if not row.get("change") or not row.get("earliest_availability_utc"):
                continue
            try:
                change, value = float(row["change"]), float(row["value"])
            except (TypeError, ValueError):
                continue
            if value == 0:
                continue
            by_month[row["earliest_availability_utc"][:7]].append(change / abs(value))
    return {month: sum(1 for v in values if v < 0) / len(values)
            for month, values in by_month.items() if values}


def specificity_text(events_path: Path, other: dict[str, float], other_label: str,
                     measure, mechanism: set[str] = MECHANISM_GROUPS,
                     comparison: set[str] = COMPARISON_GROUP) -> str:
    """The same association inside the mechanism groups and inside a comparison group."""
    lines = [f"specificity of any firm-level survivor against {other_label}:", ""]
    lines.append(f"{'group set':34s} {'n':>4s} {'change rho':>11s} {'percentile':>11s}")
    for label, groups in (("mechanism: contractor and equipment", mechanism),
                          ("comparison: datacenter", comparison),
                          ("every declared group pooled", mechanism | comparison | {"utility"})):
        series = firm_group_series(events_path, groups)
        months = sorted(set(series) & set(other))
        if len(months) < 24:
            lines.append(f"{label:34s} {len(months):>4d} {'too few months':>11s}")
            continue
        result = measure(label, [series[m] for m in months], [other[m] for m in months], draws=300)
        lines.append(f"{label:34s} {len(months):>4d} {result.change_rho:>+11.2f} "
                     f"{result.placebo_percentile:>11.2f}")
    lines.append("")
    lines.append("A relation that appears in unrelated industries is a common factor, not the mechanism.")
    return "\n".join(lines)


def summarise(rows: list[dict], nodes: dict[str, dict], threshold: float = 0.95) -> str:
    canon = canonical(rows)
    counts = family_counts(canon, nodes, threshold)
    lines = [f"series-level pairs measured: {len(rows)}",
             f"with one canonical series per node: {len(canon)}",
             f"  inside one family: {counts['same_family']} "
             f"(survivors {counts['same_survivors']}, expected {counts['expected_same']:.1f})",
             f"  across families: {counts['cross_family']} "
             f"(survivors {counts['cross_survivors']}, expected {counts['expected_cross']:.1f})",
             "",
             "The cross-family line is the one that matters. A pair inside one family is two views of the",
             "same risk, which is not a discovery."]
    return "\n".join(lines)
