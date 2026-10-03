"""The compute price series, from the AWS spot archive, by two routes and one rule.

Route one is an export: a small monthly aggregate CSV under `results/`, produced from the TigerData table by
whoever holds the connection. Route two is a direct read-only query, used only when `TIGERDATA_URL` is
present in the environment. The connection string is never printed, never logged and never written to a
file, and code that would echo it is not written here.

The rule is about what this series is: a provider list-derived spot price per instance-hour for a named
family, in two regions, with a documented gap. It is **not** a GPU-hour figure, not an executed-rental
index, and not continuous. A monthly median by family is the honest reduction: it keeps the scarcity signal
and refuses to assert a price that was never quoted.
"""
from __future__ import annotations

import csv
import os
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPORT = ROOT / "results" / "compute-price-monthly.csv"
ENV_VARIABLE = "TIGERDATA_URL"

# One query, one row per month and family. Written for the person who holds the connection.
AGGREGATE_SQL = """
SELECT date_trunc('month', price_time)::date AS month,
       lower(split_part(instance_type, '.', 1)) AS family,
       count(*) AS quotes,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY usd_per_instance_hour) AS median_usd_per_instance_hour,
       count(DISTINCT zone_id) AS zones
FROM public.aws_gpu_spot_prices
GROUP BY 1, 2
ORDER BY 1, 2
"""

FAMILIES = ("g3", "g4", "g5", "g6", "p3", "p4", "p5", "p6")


def load_export(path: Path | None = None) -> dict[str, dict[str, float]]:
    """Monthly median price per family from the aggregate export, if it exists."""
    path = path or EXPORT
    if not path.exists():
        return {}
    by_family: dict[str, dict[str, float]] = {}
    with path.open() as handle:
        for row in csv.DictReader(handle):
            month = (row.get("month") or "")[:7]
            family = (row.get("family") or "").lower()
            try:
                value = float(row.get("median_usd_per_instance_hour", ""))
            except ValueError:
                continue
            if not month or not family:
                continue
            by_family.setdefault(family, {})[month] = value
    return by_family


def family_index(by_family: dict[str, dict[str, float]]) -> dict[str, float]:
    """One scarcity series: the mean of family medians, each rebased to its first observation.

    Families differ by an order of magnitude in absolute price, so averaging raw prices would let the most
    expensive family decide everything. Rebasing makes the series about movement, which is what a scarcity
    reading is for.
    """
    months = sorted({month for series in by_family.values() for month in series})
    out: dict[str, float] = {}
    for month in months:
        levels = []
        for series in by_family.values():
            if month in series and series[month] > 0:
                base = next(value for key, value in sorted(series.items()) if value > 0)
                levels.append(series[month] / base)
        if len(levels) >= 2:
            out[month] = statistics.mean(levels)
    return out


def load_direct() -> tuple[dict[str, dict[str, float]], str]:
    """Read the table directly when a connection is available. Returns the data and a status line."""
    url = os.environ.get(ENV_VARIABLE)
    if not url:
        return {}, f"{ENV_VARIABLE} is not set, so the direct route is unavailable"
    try:
        import psycopg  # type: ignore
    except ImportError:
        return {}, ("psycopg is not installed in this interpreter, so the direct route is unavailable. "
                    "Install it into the project environment, not the system one")
    try:
        with psycopg.connect(url, connect_timeout=15) as connection:
            with connection.cursor() as cursor:
                cursor.execute(AGGREGATE_SQL)
                rows = cursor.fetchall()
    except Exception as exc:
        # The message is type only: a driver error can quote the connection string.
        return {}, f"the direct read failed with {type(exc).__name__}"
    by_family: dict[str, dict[str, float]] = {}
    for month, family, _quotes, median, _zones in rows:
        if month is None or family is None or median is None:
            continue
        by_family.setdefault(str(family).lower(), {})[str(month)[:7]] = float(median)
    return by_family, f"read {len(rows)} monthly rows from the table"


def series() -> tuple[dict[str, float], str]:
    """The compute scarcity series and a status line that never contains a credential."""
    exported = load_export()
    if exported:
        return family_index(exported), f"export route: {len(exported)} families from {EXPORT.name}"
    direct, status = load_direct()
    if direct:
        return family_index(direct), status
    return {}, status
