"""Small validated Massive client used by the shared cloud loader."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen


DISCLOSURE_FIELDS = (
    "tickers", "cik", "accession_number", "filing_date", "primary_category",
    "secondary_category", "tertiary_category", "supporting_text", "filing_url",
)


def request_json(url: str, api_key: str, attempts: int = 5) -> dict:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "api.massive.com":
        raise ValueError("Massive pagination URL is outside the API origin")
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["apiKey"] = api_key
    request_url = urlunparse(parsed._replace(query=urlencode(query)))
    for attempt in range(attempts):
        try:
            with urlopen(Request(request_url, headers={"User-Agent": "GQH-Delivery-Gap/0.1 research"}), timeout=45) as response:
                payload = json.load(response)
            if payload.get("status") not in ("OK", "DELAYED", "DELISTED"):
                raise ValueError(f"Massive returned unexpected status {payload.get('status')!r}")
            return payload
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                raise RuntimeError(f"Massive HTTP request failed ({exc.code}); body suppressed") from None
        except (URLError, TimeoutError) as exc:
            if attempt == attempts - 1:
                raise RuntimeError(f"Massive request failed ({type(exc).__name__}); details suppressed") from None
        time.sleep(min(2**attempt, 20))
    raise RuntimeError("Massive retries exhausted")


def get_bars(ticker: str, start: str, end: str, api_key: str, adjusted: bool = True) -> list[dict]:
    url = f"https://api.massive.com/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}?adjusted={str(adjusted).lower()}&sort=asc&limit=50000"
    bars: list[dict] = []
    while url:
        page = request_json(url, api_key)
        for result in page.get("results", []):
            stamp = datetime.fromtimestamp(result["t"] / 1000, tz=timezone.utc).isoformat()
            bar = {
                "ticker": ticker, "bar_time_utc": stamp,
                "open": result.get("o"), "high": result.get("h"), "low": result.get("l"),
                "close": result.get("c"), "volume": result.get("v"),
                "vwap": result.get("vw"), "transactions": result.get("n"),
            }
            if any(bar[field] is None for field in ("open", "high", "low", "close", "volume")):
                raise ValueError(f"Incomplete OHLCV row for {ticker}")
            if bar["high"] < max(bar["open"], bar["close"], bar["low"]) or bar["low"] > min(bar["open"], bar["close"], bar["high"]):
                raise ValueError(f"Invalid OHLC ordering for {ticker}")
            bars.append(bar)
        url = page.get("next_url")
    stamps = [row["bar_time_utc"] for row in bars]
    if stamps != sorted(stamps) or len(stamps) != len(set(stamps)):
        raise ValueError(f"Non-chronological or duplicate daily bars for {ticker}")
    return bars


def get_corporate_actions(action: str, ticker: str, start: str, end: str, api_key: str) -> list[dict]:
    if action not in {"splits", "dividends"}:
        raise ValueError("unsupported Massive corporate action")
    date_field = "execution_date" if action == "splits" else "ex_dividend_date"
    url = (f"https://api.massive.com/stocks/v1/{action}?ticker={ticker}"
           f"&{date_field}.gte={start}&{date_field}.lte={end}&limit=5000&sort={date_field}.asc")
    rows: list[dict] = []
    while url:
        page = request_json(url, api_key)
        for result in page.get("results", []):
            rows.append(result)
        url = page.get("next_url")
    return rows


def get_ticker_events(ticker: str, api_key: str) -> list[dict]:
    page = request_json(f"https://api.massive.com/vX/reference/tickers/{ticker}/events", api_key)
    result = page.get("results") or {}
    events = result.get("events") or []
    return [{"ticker": ticker, "issuer_name": result.get("name"), **event} for event in events]


def get_ticker_details(ticker: str, as_of_date: str, api_key: str) -> dict:
    page = request_json(f"https://api.massive.com/v3/reference/tickers/{ticker}?date={as_of_date}", api_key)
    row = page.get("results")
    if not row:
        raise ValueError(f"Massive ticker details missing for {ticker} as of {as_of_date}")
    return {"requested_ticker": ticker, "as_of_date": as_of_date,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(), **row}
