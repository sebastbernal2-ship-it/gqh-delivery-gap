#!/usr/bin/env python3
"""Pull a small Massive daily-bars batch to a local CSV (never print the API key).

This intentionally does not write to Snowflake or TigerData. Team/database and
non-display strategy rights must be documented before using those destinations.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen


API_ROOT = "https://api.massive.com"
DEFAULT_TICKERS = ("PWR", "ETN", "EME", "DLR", "SPY")
FIELDS = ("ticker", "bar_time_utc", "open", "high", "low", "close", "volume", "vwap", "transactions")
DISCLOSURE_FIELDS = (
    "tickers", "cik", "accession_number", "filing_date", "primary_category",
    "secondary_category", "tertiary_category", "supporting_text", "filing_url",
)


class MassiveError(RuntimeError):
    pass


def _with_api_key(url: str, api_key: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "api.massive.com":
        raise MassiveError("Refusing pagination URL outside https://api.massive.com")
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["apiKey"] = api_key
    return urlunparse(parsed._replace(query=urlencode(query)))


def _request_json(url: str, api_key: str, attempts: int = 5) -> dict:
    for attempt in range(attempts):
        request = Request(_with_api_key(url, api_key), headers={"User-Agent": "GQH-Delivery-Gap/0.1 research"})
        try:
            with urlopen(request, timeout=45) as response:
                payload = json.load(response)
            if payload.get("status") not in ("OK", "DELAYED", "DELISTED"):
                raise MassiveError(f"Massive returned status {payload.get('status')!r}")
            return payload
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                raise MassiveError(f"Massive HTTP request failed ({exc.code}); response body suppressed") from None
        except (URLError, TimeoutError) as exc:
            if attempt == attempts - 1:
                raise MassiveError(f"Massive request failed ({type(exc).__name__}); details suppressed") from None
        time.sleep(min(2**attempt, 20))
    raise MassiveError("Massive request retries exhausted")


def get_bars(ticker: str, start: str, end: str, api_key: str) -> list[dict]:
    url = f"{API_ROOT}/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}?adjusted=true&sort=asc&limit=50000"
    bars: list[dict] = []
    while url:
        page = _request_json(url, api_key)
        for result in page.get("results", []):
            stamp = datetime.fromtimestamp(result["t"] / 1000, tz=timezone.utc).isoformat()
            bar = {
                "ticker": ticker,
                "bar_time_utc": stamp,
                "open": result.get("o"),
                "high": result.get("h"),
                "low": result.get("l"),
                "close": result.get("c"),
                "volume": result.get("v"),
                "vwap": result.get("vw"),
                "transactions": result.get("n"),
            }
            if any(bar[k] is None for k in ("open", "high", "low", "close", "volume")):
                raise MassiveError(f"Incomplete OHLCV row for {ticker}; refusing to write output")
            if bar["high"] < max(bar["open"], bar["close"], bar["low"]) or bar["low"] > min(bar["open"], bar["close"], bar["high"]):
                raise MassiveError(f"Invalid OHLC ordering for {ticker}; refusing to write output")
            bars.append(bar)
        url = page.get("next_url")
    if bars != sorted(bars, key=lambda row: row["bar_time_utc"]):
        raise MassiveError(f"Non-chronological results for {ticker}")
    stamps = [row["bar_time_utc"] for row in bars]
    if len(stamps) != len(set(stamps)):
        raise MassiveError(f"Duplicate daily timestamps for {ticker}")
    return bars


def get_disclosures(ticker: str, start: str, end: str, api_key: str) -> list[dict]:
    url = f"{API_ROOT}/stocks/filings/8-K/v1/disclosures?ticker={ticker}&filing_date.gte={start}&filing_date.lte={end}&limit=1000"
    rows: list[dict] = []
    while url:
        page = _request_json(url, api_key)
        for result in page.get("results", []):
            if not result.get("accession_number") or not result.get("filing_date"):
                raise MassiveError(f"Disclosure row lacks filing identity for {ticker}")
            rows.append({field: result.get(field) for field in DISCLOSURE_FIELDS})
        url = page.get("next_url")
    # A multi-ticker filing may be returned once for each per-ticker request. Merge those
    # duplicates, but preserve distinct event tags attached to the same accession.
    merged: dict[tuple, dict] = {}
    for row in rows:
        key = (row["accession_number"], row.get("tertiary_category"), row.get("supporting_text"))
        if key not in merged:
            merged[key] = row
        else:
            merged[key]["tickers"] = sorted(set(merged[key].get("tickers") or []) | set(row.get("tickers") or []))
    return sorted(merged.values(), key=lambda row: (row["filing_date"], row["accession_number"], row.get("tertiary_category") or ""))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--to", dest="end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--ticker", action="append", dest="tickers", help="Repeat for each ticker; defaults to PWR ETN EME DLR SPY")
    parser.add_argument("--dataset", choices=("bars", "8k-disclosures"), default="bars", help="Massive dataset to extract")
    parser.add_argument("--output", type=Path, required=True, help="Local CSV path; output is not uploaded")
    args = parser.parse_args()

    if os.getenv("GQH_MASSIVE_TEAM_STRATEGY_LICENSE") != "confirmed":
        print("Blocked: obtain written permission for team-shared retention and non-display strategy use; then set GQH_MASSIVE_TEAM_STRATEGY_LICENSE=confirmed.", file=sys.stderr)
        return 2
    api_key = os.getenv("MASSIVE_API_KEY")
    if not api_key:
        print("Missing MASSIVE_API_KEY in the process environment.", file=sys.stderr)
        return 2
    try:
        datetime.strptime(args.start, "%Y-%m-%d")
        datetime.strptime(args.end, "%Y-%m-%d")
        if args.start > args.end:
            raise ValueError
    except ValueError:
        print("Invalid date range; use YYYY-MM-DD with --from <= --to.", file=sys.stderr)
        return 2

    tickers = tuple(t.upper() for t in (args.tickers or DEFAULT_TICKERS))
    rows: list[dict] = []
    try:
        for ticker in tickers:
            if args.dataset == "bars":
                rows.extend(get_bars(ticker, args.start, args.end, api_key))
            else:
                rows.extend(get_disclosures(ticker, args.start, args.end, api_key))
    except (MassiveError, HTTPError, URLError, TimeoutError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = FIELDS if args.dataset == "bars" else DISCLOSURE_FIELDS
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    manifest = {
        "provider": "Massive",
        "dataset": args.dataset,
        "endpoint": ("/v2/aggs/ticker/{ticker}/range/1/day/{from}/{to}" if args.dataset == "bars" else "/stocks/filings/8-K/v1/disclosures"),
        "adjusted": True if args.dataset == "bars" else None,
        "tickers": list(tickers),
        "requested_from": args.start,
        "requested_to": args.end,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "rows": len(rows),
        "first_observation": min((r["bar_time_utc"] if args.dataset == "bars" else r["filing_date"] for r in rows), default=None),
        "last_observation": max((r["bar_time_utc"] if args.dataset == "bars" else r["filing_date"] for r in rows), default=None),
        "csv_sha256": digest,
        "data_rights": "written team-storage and strategy permission asserted by operator; verify before use",
        "destinations": "local CSV only; no Snowflake or TigerData write",
    }
    args.output.with_suffix(args.output.suffix + ".manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} bars to {args.output} (sha256={digest}); no database writes performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
