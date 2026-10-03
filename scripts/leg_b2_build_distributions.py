#!/usr/bin/env python3
"""Build monthly distribution and scale summaries for locally measurable graph nodes."""
from __future__ import annotations

import csv
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/leg-b-node-distributions.csv"
FIELDS = [
    "node", "representation", "months", "first", "last", "mean",
    "standard_deviation", "rolling_12m_standard_deviation_mean",
    "scale_stability_ratio", "skew", "kurtosis", "minimum", "maximum",
    "share_of_months_in_top_decile_of_scale",
]


def read_csv(path: str) -> list[dict[str, str]]:
    with (ROOT / path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def add_month(series: dict[str, list[float]], month: str, value: object) -> None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return
    if month and math.isfinite(number):
        series.setdefault(month[:7], []).append(number)


def mean_series(series: dict[str, list[float]]) -> dict[str, float]:
    return {month: statistics.mean(values) for month, values in series.items() if values}


def source_series() -> dict[tuple[str, str], dict[str, float]]:
    """Return monthly series keyed by declared node and representation."""
    raw: dict[tuple[str, str], dict[str, list[float]]] = {}

    def add(node: str, representation: str, month: str, value: object) -> None:
        add_month(raw.setdefault((node, representation), {}), month, value)

    # The canonical promise and firm representations match src/scan/report.py.
    # Apply its per-node canonical selection rather than counting alternate labels.
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    from scan import report as scan_report
    from scan import series as scan_series

    for node, mapping in scan_report.CANONICAL.items():
        if node == "promise:power:planned-capacity-revision":
            promise_data = scan_series.promise_series(ROOT / "results/capacity-expectations.csv")
            for label in (mapping, "promise_next_year_level", "promise_total_level"):
                for month, value in promise_data[label].items():
                    add(node, label, month, value)
        elif node == "firm:obligation:remaining-performance":
            values = scan_series.firm_series(ROOT / "results/obligation-panel.csv")[mapping]
            for month, value in values.items():
                add(node, mapping, month, value)

    # Delivery and cancellation use the declared outcome panels, by first public month.
    for row in read_csv("results/delivery-realizations.csv"):
        month = row.get("available_from", "")
        add("promise:power:realized-delivery", "realized_late_months", month, row.get("late_months"))
        try:
            add("promise:power:realized-delivery", "share_late", month,
                float(row["late_months"]) > 0)
        except (KeyError, TypeError, ValueError):
            pass
    # Filing panels contain distinct, node-specific facts. Keep only observations outside
    # their explicitly sealed windows, and monthly aggregate by publication month.
    for row in read_csv("results/obligation-panel.csv"):
        if str(row.get("in_sealed_window", "")).lower() in {"true", "1"}:
            continue
        concept = row.get("concept", "").lower()
        node = None
        if "unapprovedchangeorders" in concept:
            node = ("firm:obligation:unapproved-change-orders", "change_over_abs_value")
            value = row.get("change")
            base = row.get("value")
            try:
                value = float(value) / abs(float(base)) if float(base) else None
            except (TypeError, ValueError):
                value = None
        elif "capitalexpenditure" in concept or "capitalexpenditures" in concept:
            node = ("firm:capex:hyperscaler-commitments", "reported_commitments")
            value = row.get("value")
        elif "revenueremainingperformanceobligation" in concept:
            add("firm:obligation:remaining-performance", "reported_obligation_value",
                row.get("earliest_availability_utc", ""), row.get("value"))
            continue
        else:
            continue
        stamp = row.get("earliest_availability_utc", "")
        add(node[0], node[1], stamp, value)

    # Existing cached bars produce the two declared equal-weight equity baskets.
    for node, label in (("price:equity:buildout", "buildout_basket"),
                        ("price:equity:scarcity", "scarcity_basket")):
        for month, value in scan_series.basket_series(scan_series.TICKERS[label]).items():
            if month <= "2022-09":
                add(node, label, month, value)

    # Existing monthly factor panels are observational node series, not forecasts.
    for filename in ("results/delivery-model-panel.csv", "results/bottleneck-factors.csv"):
        for row in read_csv(filename):
            month = row.get("month", "")
            for col, node, rep in (
                ("drought_severity", "water:drought:severity", "monthly_drought_severity"),
                ("gas_level", "price:commodity:gas", "monthly_gas_level"),
                ("ten_year", "rate:treasury:ten-year", "monthly_ten_year_yield"),
                ("gscpi", "feature:equipment:lead-time-share", "supply_chain_pressure"),
                ("delivery_times", "feature:equipment:lead-time-share", "delivery_time_index"),
                ("lead_time_share_negative", "feature:equipment:lead-time-share", "negative_lead_time_share"),
                ("lead_time_growth", "feature:equipment:lead-time-share", "lead_time_growth"),
            ):
                if col in row and row[col] not in (None, ""):
                    add(node, rep, month, row[col])

    # Rebase each compute family to its first development observation, then average
    # available family levels so large instance prices do not dominate the index.
    family_values: dict[str, dict[str, float]] = {}
    for row in read_csv("results/compute-price-monthly.csv"):
        month = row.get("month", "")
        if not ("2022-06" <= month <= "2024-03"):
            continue
        try:
            family_values.setdefault(row["family"], {})[month] = float(row["median_usd_per_instance_hour"])
        except (KeyError, TypeError, ValueError):
            continue
    rebased: dict[str, list[float]] = {}
    for values in family_values.values():
        base_month = min(values)
        base = values[base_month]
        if base:
            for month, value in values.items():
                rebased.setdefault(month, []).append(value / base)
    for month, values in rebased.items():
        add("price:compute:rental", "monthly_median_family_rebased_index", month,
            statistics.mean(values))

    # Restrict the common mechanism-era series to development dates. The compute series
    # uses its separately declared development window above.
    for key in list(raw):
        if key[0] == "price:compute:rental":
            continue
        raw[key] = {m: v for m, v in raw[key].items() if m <= "2022-09"}

    return {key: mean_series(values) for key, values in raw.items() if values}


def rolling_scales(values: list[float], window: int = 12) -> list[float]:
    return [statistics.stdev(values[index - window + 1:index + 1])
            for index in range(window - 1, len(values))]


def distribution_row(node: str, representation: str, series: dict[str, float]) -> dict[str, object]:
    months = sorted(series)
    values = [series[month] for month in months]
    mean = statistics.mean(values)
    sd = statistics.stdev(values) if len(values) > 1 else 0.0
    rolls = rolling_scales(values)
    roll_mean = statistics.mean(rolls) if rolls else None
    ratio = statistics.stdev(rolls) / sd if len(rolls) > 1 and sd else None
    if len(values) > 2 and sd:
        skew = statistics.mean(((value - mean) / sd) ** 3 for value in values)
    else:
        skew = None
    if len(values) > 3 and sd:
        kurtosis = statistics.mean(((value - mean) / sd) ** 4 for value in values) - 3
    else:
        kurtosis = None
    cutoff = sorted(rolls)[max(0, math.ceil(0.9 * len(rolls)) - 1)] if rolls else None
    top_share = sum(value >= cutoff for value in rolls) / len(rolls) if rolls else None
    return {
        "node": node, "representation": representation, "months": len(values),
        "first": months[0], "last": months[-1], "mean": mean,
        "standard_deviation": sd, "rolling_12m_standard_deviation_mean": roll_mean,
        "scale_stability_ratio": ratio, "skew": skew, "kurtosis": kurtosis,
        "minimum": min(values), "maximum": max(values),
        "share_of_months_in_top_decile_of_scale": top_share,
    }


def fmt(value: object) -> str:
    return "" if value is None else f"{value:.10g}" if isinstance(value, float) else str(value)


def main() -> None:
    series = source_series()
    rows = [distribution_row(node, rep, values) for (node, rep), values in sorted(series.items())]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: fmt(value) for key, value in row.items()})
    judged = [row for row in rows if row["months"] >= 24 and row["scale_stability_ratio"] is not None]
    stable = sorted(judged, key=lambda row: row["scale_stability_ratio"])
    moving = []
    for row in rows:
        values = series[(row["node"], row["representation"])]
        scales = rolling_scales([values[month] for month in sorted(values)])
        if scales and min(scales) > 0 and max(scales) / min(scales) >= 10:
            moving.append((row, min(scales), max(scales), max(scales) / min(scales)))
    short = [row for row in rows if row["months"] < 24]
    lines = ["# Leg B2: node distributions and scale stability", "",
             "Monthly development-window observations only. Each row is one measurable node representation.",
             "The rolling scale uses trailing twelve observations. Stability is the sample standard deviation",
             "of rolling scales divided by the full-series standard deviation. Order-of-magnitude movement is",
             "reported when the largest rolling scale is at least ten times the smallest. A series is too short to",
             "judge when it has fewer than 24 monthly observations.", ""]
    if stable:
        lines.append(f"Most stable: `{stable[0]['node']}` ({stable[0]['representation']}); "
                     f"n={stable[0]['months']}, ratio={stable[0]['scale_stability_ratio']:.6g}.")
        lines.append(f"Least stable: `{stable[-1]['node']}` ({stable[-1]['representation']}); "
                     f"n={stable[-1]['months']}, ratio={stable[-1]['scale_stability_ratio']:.6g}.")
    else:
        lines.append("No series has 24 months and a defined scale-stability ratio, so stability cannot be ranked.")
    lines.extend(["", "## Scale moves by an order of magnitude"])
    lines.extend([f"- `{row['node']}` ({row['representation']}): minimum rolling scale {low:.6g}, "
                  f"maximum rolling scale {high:.6g}, ratio {ratio:.6g}."
                  for row, low, high, ratio in moving] or ["- None under the stated criterion."])
    lines.extend(["", "## Too short to judge"])
    lines.extend([f"- `{row['node']}` ({row['representation']}): {row['months']} monthly observations, "
                  f"{row['first']} to {row['last']}." for row in short] or ["- None."])
    lines.extend(["", "## Limits", "",
                  "Only locally present node series are measured. The graph inventory's stated row totals are source-table totals, not node-level observations. Nodes without a usable local series are omitted rather than assigned fabricated values.",
                  "Development windows exclude the declared compute holdout and the mechanism holdout. The source panels do not provide monthly grid demand or generation series, so those nodes are not represented.", ""])
    (ROOT / "docs/plan/leg-b-report-2.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {len(rows)} node series to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
