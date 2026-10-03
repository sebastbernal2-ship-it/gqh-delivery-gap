"""State level drought severity, as a cooling and water factor.

Source: the US Drought Monitor's public state statistics, which report the share of each state's area in each
severity class, weekly. The factor used here is the share of area in severe drought or worse, averaged to a
month, because a site either has water or it does not.

The drought monitor uses FIPS state codes, not postal codes, so the mapping is explicit rather than guessed.
A weekly value is treated as knowable at the end of its own week, and monthly averages are stamped to the
month they summarise.
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "factors"
UA = {"User-Agent": "gqh-delivery-gap research research@example.com"}
ENDPOINT = ("https://usdmdataservices.unl.edu/api/StateStatistics/"
            "GetDroughtSeverityStatisticsByAreaPercent")

FIPS = {
    "AL": 1, "AK": 2, "AZ": 4, "AR": 5, "CA": 6, "CO": 8, "CT": 9, "DE": 10, "FL": 12, "GA": 13,
    "HI": 15, "ID": 16, "IL": 17, "IN": 18, "IA": 19, "KS": 20, "KY": 21, "LA": 22, "ME": 23, "MD": 24,
    "MA": 25, "MI": 26, "MN": 27, "MS": 28, "MO": 29, "MT": 30, "NE": 31, "NV": 32, "NH": 33, "NJ": 34,
    "NM": 35, "NY": 36, "NC": 37, "ND": 38, "OH": 39, "OK": 40, "OR": 41, "PA": 42, "RI": 44, "SC": 45,
    "SD": 46, "TN": 47, "TX": 48, "UT": 49, "VT": 50, "VA": 51, "WA": 53, "WV": 54, "WI": 55, "WY": 56,
}


def parse_csv(payload: str) -> dict[str, float]:
    """Monthly mean share of area in severe drought or worse, from the service's CSV body.

    Columns are located by name, because the column set varies between states. The classes are nested, so D2
    already means "D2 or worse" and summing D2, D3 and D4 double counts: that mistake produced values above a
    hundred percent, which a guard now refuses.
    """
    lines = [line for line in payload.splitlines() if line.strip()]
    if not lines:
        return {}
    header = lines[0].split(",")
    try:
        date_at = header.index("MapDate")
        severe_at = header.index("D2")
    except ValueError:
        return {}
    format_at = header.index("StatisticFormatID") if "StatisticFormatID" in header else None
    by_month: dict[str, list[float]] = {}
    for line in lines[1:]:
        parts = line.split(",")
        if len(parts) <= severe_at or not parts[date_at].isdigit():
            continue
        if format_at is not None and len(parts) > format_at and parts[format_at].strip() != "1":
            continue
        try:
            severe = float(parts[severe_at])
        except (TypeError, ValueError):
            continue
        if not 0.0 <= severe <= 100.0:
            continue
        stamp = parts[date_at]
        by_month.setdefault(f"{stamp[:4]}-{stamp[4:6]}", []).append(severe)
    return {month: statistics.mean(values) for month, values in by_month.items() if values}


def severity(postal: str, start: str = "1/1/2015", end: str = "12/31/2024") -> dict[str, float]:
    """Monthly mean share of state area in severe drought or worse, keyed by year-month."""
    code = FIPS.get(postal.upper())
    if code is None:
        return {}
    CACHE.mkdir(parents=True, exist_ok=True)
    target = CACHE / f"usdm-{postal.upper()}.json"
    if target.exists():
        try:
            stored = json.loads(target.read_text())
            if stored:
                return stored
        except (OSError, ValueError):
            pass
    url = f"{ENDPOINT}?aoi={code}&startdate={start}&enddate={end}&statisticsType=1"
    payload = None
    for attempt in range(3):
        try:
            response = requests.get(url, headers=UA, timeout=120)
        except requests.RequestException:
            continue
        if response.status_code == 200 and "MapDate" in response.text:
            payload = response.text
            break
    if payload is None:
        return {}
    parsed = parse_csv(payload)
    out = {month: statistics.mean(values) for month, values in by_month.items() if values}
    target.write_text(json.dumps(out, sort_keys=True))
    return out
