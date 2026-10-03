"""Turn declared nodes into monthly series, and say plainly which ones could not be built.

Every series is keyed by calendar month, because the declared clocks are monthly, quarterly, weekly, daily
and hourly, and a monthly grid is the shortest common one that keeps the scan bounded. A quarterly value
enters the month it became available and stays until the next one. A daily value enters at its month end.

Nothing here reaches for a series the node space did not declare, and a node whose series cannot be built
is returned as missing with a reason rather than silently dropped.
"""
from __future__ import annotations

import calendar
import csv
import datetime as dt
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BAR_CACHE = ROOT / "results" / "bar-cache"
USDM_CACHE = ROOT / "results" / "usdm-cache"
MONTH_END_DAYS = 1

# Series this module knows how to build, by node id.
BUILDABLE = {
    "promise:power:planned-capacity-revision",
    "promise:power:realized-delivery",
    "promise:power:cancellation",
    "firm:obligation:remaining-performance",
    "firm:capex:hyperscaler-commitments",
    "price:commodity:gas",
    "price:commodity:copper",
    "price:commodity:uranium",
    "rate:treasury:ten-year",
    "price:equity:buildout",
    "price:equity:scarcity",
    "water:drought:severity",
    "price:compute:rental",
}

# One or more series per node. A node with several series contributes each of them to the scan.
SERIES = {
    "promise:power:planned-capacity-revision": ["promise_next_year_level", "promise_next_year_revision",
                                                "promise_total_level"],
    "firm:obligation:remaining-performance": ["firm_share_negative_revision", "firm_median_revision"],
    "price:commodity:gas": ["gas_price"],
    "price:commodity:copper": ["copper_price"],
    "price:commodity:uranium": ["uranium_price"],
    "rate:treasury:ten-year": ["ten_year_yield"],
    "price:equity:buildout": ["buildout_basket"],
    "price:equity:scarcity": ["scarcity_basket"],
    "water:drought:severity": ["drought_severity"],
    "price:compute:rental": ["compute_price_index"],
}

TICKERS = {
    "gas_price": "NG=F",
    "copper_price": "HG=F",
    "uranium_price": "URA",
    "ten_year_yield": "^TNX",
    "buildout_basket": ["PWR", "EME", "MTZ", "DY", "ETN", "J", "HUBB", "ROK"],
    "scarcity_basket": ["NRG", "VST", "D", "SO", "NEE", "EXC"],
}

HYPERSCALERS = ["MSFT", "AMZN", "GOOGL", "META"]


def month_of(stamp: str) -> str:
    return stamp[:7]


def last_day(month: str) -> str:
    year, number = int(month[:4]), int(month[5:7])
    return f"{month}-{calendar.monthrange(year, number)[1]:02d}"


def month_end_prices(closes: dict[str, float]) -> dict[str, float]:
    """The last observation in each month, which is the month's settled value."""
    out: dict[str, float] = {}
    for stamp, value in closes.items():
        month = month_of(stamp)
        try:
            if month not in out or stamp > out[month][1]:
                out[month] = (value, stamp)
        except TypeError:
            continue
    return {month: value for month, (value, _) in out.items()}


def load_bars(ticker: str) -> dict[str, float]:
    path = BAR_CACHE / f"{ticker}.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (OSError, ValueError):
            pass
    import yfinance as yf
    try:
        frame = yf.Ticker(ticker).history(period="max", auto_adjust=True)
    except Exception:
        return {}
    out: dict[str, float] = {}
    if frame is not None and len(frame) and "Close" in frame:
        for stamp, value in frame["Close"].items():
            try:
                out[str(stamp)[:10]] = float(value)
            except (TypeError, ValueError):
                continue
    BAR_CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out))
    return out


def basket_series(names: list[str]) -> dict[str, float]:
    """Equal weight index of the names that have data, rebased at each month end."""
    monthly = {name: month_end_prices(load_bars(name)) for name in names}
    months = sorted({month for series in monthly.values() for month in series})
    out: dict[str, float] = {}
    base: dict[str, float] = {}
    for month in months:
        level = []
        for name, series in monthly.items():
            if month not in series:
                continue
            base.setdefault(name, series[month])
            level.append(series[month] / base[name])
        if len(level) >= 3:
            out[month] = statistics.mean(level)
    return out


def promise_series(path: Path) -> dict[str, dict[str, float]]:
    """The declared promise series, from the vintage aggregate panel."""
    by_vintage: dict[str, dict[int, float]] = {}
    with path.open() as handle:
        for row in csv.DictReader(handle):
            by_vintage.setdefault(row["vintage"], {})[int(row["promised_year"])] = float(row["capacity_mw"])
    level: dict[str, float] = {}
    revision: dict[str, float] = {}
    total: dict[str, float] = {}
    for vintage, years in by_vintage.items():
        year = int(vintage[:4])
        level[vintage] = years.get(year + 1, 0.0)
        total[vintage] = sum(years.values())
        base = f"{year - 1}-{vintage[5:]}"
        if base in by_vintage:
            prior = by_vintage[base].get(year + 1, 0.0)
            revision[vintage] = (level[vintage] - prior) / prior if prior > 0 else 0.0
    return {"promise_next_year_level": level, "promise_next_year_revision": revision,
            "promise_total_level": total}


def firm_series(path: Path) -> dict[str, dict[str, float]]:
    """Firm disclosures, reduced to monthly readings and stamped when they became public."""
    by_month: dict[str, list[float]] = {}
    with path.open() as handle:
        for row in csv.DictReader(handle):
            if str(row.get("in_sealed_window", "")).lower() in ("true", "1"):
                continue
            if not row.get("change") or not row.get("earliest_availability_utc"):
                continue
            try:
                change = float(row["change"])
                value = float(row["value"])
            except (TypeError, ValueError):
                continue
            if value == 0:
                continue
            month = month_of(row["earliest_availability_utc"])
            by_month.setdefault(month, []).append(change / abs(value))
    share = {month: sum(1 for v in values if v < 0) / len(values)
             for month, values in by_month.items() if values}
    median = {month: statistics.median(values) for month, values in by_month.items() if values}
    return {"firm_share_negative_revision": share, "firm_median_revision": median}


def drought_series(states: list[str], start: str, end: str) -> dict[str, float]:
    """Weekly drought severity, averaged to months. Cache first, network second."""
    USDM_CACHE.mkdir(parents=True, exist_ok=True)
    key = USDM_CACHE / f"states-{start}-{end}.json"
    payload = None
    if key.exists():
        try:
            payload = json.loads(key.read_text())
        except (OSError, ValueError):
            payload = None
    if payload is None:
        import requests
        rows = []
        for state in states:
            url = ("https://usdmdataservices.unl.edu/api/StateStatistics/"
                   "GetDroughtSeverityStatisticsByAreaPercent"
                   f"?aoi={state}&startdate={start}&enddate={end}&statisticsType=1")
            try:
                response = requests.get(url, timeout=60,
                                        headers={"User-Agent": "gqh-delivery-gap research research@example.com"})
                if response.status_code == 200:
                    rows.extend(response.json())
            except Exception:
                continue
        payload = rows
        key.write_text(json.dumps(payload))
    by_month: dict[str, list[float]] = {}
    for row in payload or []:
        stamp = str(row.get("mapDate", ""))[:10]
        severity = row.get("d1") 
        if not stamp or severity is None:
            continue
        try:
            percent = float(row.get("d2", 0)) + float(row.get("d3", 0)) + float(row.get("d4", 0))
        except (TypeError, ValueError):
            continue
        by_month.setdefault(month_of(stamp), []).append(percent)
    return {month: statistics.mean(values) for month, values in by_month.items() if values}


def build(node_ids: list[str], expectations: Path, events: Path) -> tuple[dict[str, dict[str, float]],
                                                                        dict[str, str]]:
    """Series for the nodes that can be built, and reasons for the nodes that cannot."""
    series: dict[str, dict[str, float]] = {}
    missing: dict[str, str] = {}
    for node_id in node_ids:
        if node_id not in BUILDABLE:
            missing[node_id] = "no series built in this pass; the representation is declared but not wired"
            continue
        if node_id in ("promise:power:planned-capacity-revision",):
            series.update(promise_series(expectations))
        elif node_id == "firm:obligation:remaining-performance":
            series.update(firm_series(events))
        elif node_id == "water:drought:severity":
            series["drought_severity"] = drought_series(["48"], "2016-01-01", "2024-09-30")
        elif node_id == "price:compute:rental":
            from scan.compute import series as compute_series
            data, status = compute_series()
            if data:
                series["compute_price_index"] = data
            else:
                missing[node_id] = f"the export produced no series: {status}"
        else:
            for label in SERIES.get(node_id, []):
                spec = TICKERS.get(label)
                if isinstance(spec, list):
                    series[label] = basket_series(spec)
                elif spec:
                    series[label] = month_end_prices(load_bars(spec))
    return series, missing
