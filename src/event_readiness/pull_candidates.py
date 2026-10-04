"""Fetch declared options/filings partitions; no strategy analysis or warehouse writes."""
from __future__ import annotations
import argparse
from datetime import date, datetime, time, timedelta, timezone
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
from .acquisition import Retrieval, atomic_json, canonical, records_file, sha, validate_bar

BASE = "https://api.massive.com"
ET = ZoneInfo("America/New_York")


def epoch_ms(day):
    return int(datetime.combine(day, time(), ET).timestamp()) * 1000


def record(kind, context, receipt, data, **extra):
    return {"record_type": kind, "context": context, "source_sha256": receipt["sha256"],
            "source_url": receipt["url"], "retrieved_at_utc": receipt["retrieved_at_utc"],
            "available_at_utc": None, "data": data, **extra}


def options(client, ticker, asof, expiry):
    day, exp = date.fromisoformat(asof), date.fromisoformat(expiry)
    if exp < day:
        raise ValueError("expiry precedes as-of date")
    context = {"underlying": ticker, "as_of": asof, "expiry": expiry}
    url = BASE + "/v3/reference/options/contracts?" + urlencode({"underlying_ticker": ticker,
        "as_of": asof, "expiration_date": expiry, "expired": "false", "limit": 1000,
        "sort": "ticker", "order": "asc"})
    contracts = {}
    for rows, receipt, _ in client.pages(url):
        for row in rows:
            if row.get("underlying_ticker") != ticker or row.get("expiration_date") != expiry:
                raise ValueError("unexpected contract identity")
            symbol = row["ticker"]
            if symbol in contracts:
                raise ValueError("duplicate contract")
            contracts[symbol] = row
            yield record("option_contract", context, receipt, row)
    if not contracts:
        raise ValueError("empty historical contract universe")
    start_ns = int(datetime.combine(day, time(9, 30), ET).timestamp()) * 1_000_000_000
    close_ns = int(datetime.combine(day, time(16), ET).timestamp()) * 1_000_000_000
    for i, symbol in enumerate(sorted(contracts), 1):
        context = {"underlying": ticker, "option_ticker": symbol, "as_of": asof, "expiry": expiry}
        seen = set()
        count = 0
        previous = None
        url = BASE + f"/v2/aggs/ticker/{symbol}/range/1/day/{asof}/{expiry}?adjusted=false&sort=asc&limit=50000"
        for rows, receipt, page in client.pages(url):
            if page.get("ticker") != symbol or page.get("adjusted") is not False:
                raise ValueError("bar response identity or adjustment mismatch")
            for row in rows:
                validate_bar(row, epoch_ms(day), epoch_ms(exp + timedelta(days=1)))
                if row["t"] in seen or (previous is not None and row["t"] < previous):
                    raise ValueError("duplicate or unordered bar")
                seen.add(row["t"])
                previous = row["t"]
                count += 1
                yield record("option_daily_bar", context, receipt, row,
                             usage="price_path_includes_post_asof_outcomes")
        yield record("option_bar_coverage", context, receipt, {"rows": count,
                     "status": "observed" if count else "no_eligible_trade_bars_returned"})
        url = BASE + f"/v3/quotes/{symbol}?" + urlencode({"timestamp.gte": start_ns,
            "timestamp.lte": close_ns, "sort": "timestamp", "order": "desc", "limit": 1})
        # Deliberately one last quote, not a truncated claim of a complete quote tape.
        data, receipt = client.fetch(url, massive=True)
        from .acquisition import strict_json
        page = strict_json(data)
        if page.get("status") != "OK":
            raise ValueError("quote request unsuccessful")
        rows = page.get("results", [])
        if len(rows) > 1:
            raise ValueError("quote endpoint ignored limit")
        for row in rows:
            stamp = row.get("sip_timestamp")
            if not isinstance(stamp, int) or not start_ns <= stamp <= close_ns:
                raise ValueError("quote outside session")
            flags = []
            bid, ask = row.get("bid_price"), row.get("ask_price")
            if bid is None or ask is None or bid <= 0 or ask <= 0:
                flags.append("missing_or_nonpositive_quote")
            elif ask < bid:
                flags.append("crossed_quote")
            if close_ns - stamp > 300 * 1_000_000_000:
                flags.append("older_than_five_minutes_at_close")
            yield record("option_last_regular_session_quote", context, receipt, row,
                         quote_age_ns=close_ns-stamp, quality_flags=flags)
        yield record("option_quote_coverage", context, receipt, {"rows": len(rows),
                     "selection": "last SIP quote between 09:30 and 16:00 ET", "historical_open_interest": None})
        if i % 25 == 0 or i == len(contracts):
            print(json.dumps({"options_contracts_completed": i, "contracts": len(contracts)}), flush=True)


def filings(client, start, end):
    date.fromisoformat(start); date.fromisoformat(end)
    if start > end:
        raise ValueError("invalid filing date range")
    url = BASE + "/stocks/filings/8-K/vX/disclosures?" + urlencode({
        "filing_date.gte": start, "filing_date.lte": end, "limit": 1000})
    seen, total = set(), 0
    for i, (rows, receipt, _) in enumerate(client.pages(url), 1):
        for row in rows:
            if not row.get("accession_number") or not start <= row.get("filing_date", "") <= end:
                raise ValueError("filing identity/date failure")
            digest = sha(canonical(row).encode())
            if digest in seen:
                continue  # Exact repeats only; conflicting classifications remain distinct evidence.
            seen.add(digest); total += 1
            yield record("massive_disclosure", {"start": start, "end": end, "ticker_filter": None},
                         receipt, row, usage="retrospective_tag_not_verified_historical_signal")
        if i % 10 == 0:
            print(json.dumps({"filing_pages": i, "unique_disclosures": total}), flush=True)
    if not total:
        raise ValueError("empty disclosure partition")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("kind", choices=["options", "filings"])
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--ticker", default="SPY")
    p.add_argument("--as-of", default="2022-09-01")
    p.add_argument("--expiry", default="2022-09-16")
    p.add_argument("--start", default="2022-01-01")
    p.add_argument("--end", default="2022-09-30")
    args = p.parse_args()
    client = Retrieval(args.out, os.environ.get("MASSIVE_API_KEY", ""))
    output = args.out / "records.jsonl"
    if (args.out / "complete.json").exists():
        raise ValueError("completed run exists; select a new directory for a new version")
    plan = {"kind": args.kind, "ticker": args.ticker, "as_of": args.as_of, "expiry": args.expiry,
            "start": args.start, "end": args.end, "strategy_ready": False}
    plan_path = args.out / "plan.json"
    if plan_path.exists() and json.loads(plan_path.read_text()) != plan:
        raise ValueError("cannot resume a changed request plan")
    atomic_json(plan_path, plan)
    records = options(client, args.ticker, args.as_of, args.expiry) if args.kind == "options" else filings(client,args.start,args.end)
    result = records_file(output, records)
    result.update(plan=plan, request_count=len(list((args.out / "requests").glob("*.json"))),
                  completed_at_utc=datetime.now(timezone.utc).isoformat())
    atomic_json(args.out / "complete.json", result)
    print(canonical(result), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"status": "incomplete", "error_type": type(exc).__name__}), flush=True)
        raise SystemExit(1)
