"""State level monthly weather, as a construction factor.

Source: NOAA's statewide time series, which is public, needs no key, and returns one row per month. The state
codes are not guessable, so the mapping is **probed from the source itself** and cached: each code is fetched
once and its title line names the state. Guessing would have put Wyoming's precipitation on West Virginia's
projects, and that is exactly the kind of silent assumption this build is meant to avoid.

Availability is declared, not assumed: a monthly value is treated as knowable at the **end of the following
month**, which is conservative against NOAA's own publication timing.
"""
from __future__ import annotations

import calendar
import json
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "factors"
UA = {"User-Agent": "gqh-delivery-gap research research@example.com"}
BASE = "https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/statewide/time-series"
MAP_FILE = CACHE / "ncei-state-codes.json"
PUBLICATION_LAG_MONTHS = 1

# Two letter postal code to the state name as NCEI writes it, for matching the probed titles.
POSTAL_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts",
    "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}


def state_codes(session=None, refresh: bool = False) -> dict[str, str]:
    """Postal code to NCEI code, probed from the source's own titles."""
    CACHE.mkdir(parents=True, exist_ok=True)
    if MAP_FILE.exists() and not refresh:
        try:
            stored = json.loads(MAP_FILE.read_text())
            if stored:
                return stored
        except (OSError, ValueError):
            pass
    session = session or requests.Session()
    found: dict[str, str] = {}
    names = {name.lower(): postal for postal, name in POSTAL_NAMES.items()}
    for code in range(1, 60):
        url = f"{BASE}/{code}/pcp/1/1/2015-2015.csv"
        try:
            response = session.get(url, headers=UA, timeout=30)
        except requests.RequestException:
            continue
        if response.status_code != 200 or "Date,Value" not in response.text:
            continue
        first = response.text.splitlines()[0].lower() if response.text.splitlines() else ""
        for name, postal in names.items():
            if name in first:
                found[postal] = str(code)
                break
        time.sleep(0.3)
    if found:
        MAP_FILE.write_text(json.dumps(found, sort_keys=True))
    return found


def monthly_series(postal: str, variable: str = "pcp", start: int = 2015, end: int = 2024,
                   session=None, codes: dict[str, str] | None = None) -> dict[str, float]:
    """One state's monthly value, keyed by year-month, from the source and cached per state and variable."""
    codes = codes if codes is not None else state_codes(session)
    code = codes.get(postal.upper())
    if code is None:
        return {}
    CACHE.mkdir(parents=True, exist_ok=True)
    target = CACHE / f"ncei-{variable}-{postal.upper()}-all-{start}-{end}.json"
    if target.exists():
        try:
            return json.loads(target.read_text())
        except (OSError, ValueError):
            pass
    session = session or requests.Session()
    # The path is month then scale, so asking for month 1 returns Januarys only. That mistake would have put
    # January weather on every month of every project, silently, so every month is requested and the cache
    # name carries "all".
    url = f"{BASE}/{code}/{variable}/all/1/{start}-{end}.csv"
    try:
        response = session.get(url, headers=UA, timeout=60)
    except requests.RequestException:
        return {}
    if response.status_code != 200:
        return {}
    out: dict[str, float] = {}
    for line in response.text.splitlines():
        if not line.strip() or line.startswith("#") or line.startswith("Date"):
            continue
        parts = line.split(",")
        if len(parts) != 2:
            continue
        stamp, value = parts[0].strip(), parts[1].strip()
        if len(stamp) != 6 or not stamp.isdigit():
            continue
        try:
            out[f"{stamp[:4]}-{stamp[4:6]}"] = float(value)
        except ValueError:
            continue
    target.write_text(json.dumps(out, sort_keys=True))
    return out


def known_at(month: str, series: dict[str, float], lag: int = PUBLICATION_LAG_MONTHS):
    """The most recent value knowable at the end of a month, given the declared publication lag."""
    year, number = (int(part) for part in month.split("-"))
    total = year * 12 + number - 1 - lag
    key = f"{total // 12:04d}-{total % 12 + 1:02d}"
    return series.get(key)


def state_anomaly(series: dict[str, float]) -> dict[str, float]:
    """Departure from each state's own long run mean, because a dry year in one state is another's normal."""
    values = [v for v in series.values() if v == v]
    if len(values) < 12:
        return {}
    mean = sum(values) / len(values)
    spread = (sum((v - mean) ** 2 for v in values) / (len(values) - 1)) ** 0.5
    if spread == 0:
        return {}
    return {month: (value - mean) / spread for month, value in series.items()}
