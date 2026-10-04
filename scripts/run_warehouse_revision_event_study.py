#!/usr/bin/env python3
"""Run the declared descriptive daily equity event study from pinned Snowflake batches.

This is not a strategy backtest. Event labels are derived from SEC XBRL values and
Massive adjusted daily bars; no point-in-time analyst consensus is implied.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "central_ingest"))
import sync  # noqa: E402
from research_artifacts import publish_artifacts  # noqa: E402

PRICE_BATCHES = {
    "bec91f7c380937d3d647ade8214968c13abd4bde032c9a7cf7741f0ee58306cd": "operating-equities-plus-SPY",
    "2fe0dd7ac31d8ed7b990e895a4872490f24b5418b292488a83025a64361a55b9": "sector-benchmarks-XLI-XLRE",
}
DIVIDEND_BATCHES = (
    "ac84b5535b5bb86ef32acbba49877aca87d3ccf204318d329c8fe64854322e76",
    "fca235a19b8a44d1adb43fb26ac16b69bacdbaa0d983088e2d1b555ffdaea616",
)
BENCHMARK = {"PWR": "XLI", "ETN": "XLI", "EME": "XLI", "DLR": "XLRE"}
HORIZONS = (1, 2, 5, 10, 20)


def snowflake_connection():
    import snowflake.connector

    name = os.getenv("SNOWFLAKE_CONNECTION_NAME")
    if name:
        return snowflake.connector.connect(connection_name=name)
    options = {
        "account": os.environ["SNOWFLAKE_ACCOUNT"],
        "user": os.environ["SNOWFLAKE_USER"],
        "warehouse": os.environ["SNOWFLAKE_WAREHOUSE"],
        "database": "VECTOR_RESEARCH",
        "schema": "RAW",
    }
    if os.getenv("SNOWFLAKE_ROLE"):
        options["role"] = os.environ["SNOWFLAKE_ROLE"]
    if os.getenv("SNOWFLAKE_PRIVATE_KEY_FILE"):
        options["private_key_file"] = os.environ["SNOWFLAKE_PRIVATE_KEY_FILE"]
    else:
        options["password"] = os.environ["SNOWFLAKE_PASSWORD"]
    return snowflake.connector.connect(**options)


def read_batch(connection, source_id: str, batch_sha: str) -> list[dict]:
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT PAYLOAD_JSON FROM VECTOR_RESEARCH.RAW.SOURCE_RECORDS
               WHERE SOURCE_ID=%s AND BATCH_SHA256=%s ORDER BY ROW_INDEX""",
            (source_id, batch_sha),
        )
        return [json.loads(row[0], parse_float=Decimal, parse_int=Decimal)
                for row in cursor.fetchall()]


def as_decimal(value) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def bar_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def close_return(series: dict[datetime, Decimal], after: str, horizon: int) -> Decimal | None:
    decision = bar_time(after)
    later = sorted(stamp for stamp in series if stamp > decision)
    if len(later) <= horizon:
        return None
    start, end = series[later[0]], series[later[horizon]]
    if start == 0:
        return None
    return end / start - Decimal(1)


def median(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / Decimal(2)


def total_return_series(series: dict[datetime, Decimal], dividends: list[dict]) -> dict[datetime, Decimal]:
    """Apply Massive's cumulative dividend factor to split-adjusted closes.

    Massive daily aggregates adjust for splits, not dividends. Its dividend endpoint
    specifies the factor for a price on D as the first ex-date after D.
    """
    actions = sorted(
        (str(row.get("ex_dividend_date", "")), as_decimal(row.get("historical_adjustment_factor")))
        for row in dividends
        if row.get("ex_dividend_date") and as_decimal(row.get("historical_adjustment_factor")) is not None
    )
    out = {}
    for stamp, close in series.items():
        day = stamp.date().isoformat()
        factor = next((f for ex_date, f in actions if ex_date > day), Decimal(1))
        out[stamp] = close * factor
    return out


def event_rows(batch: list[dict]) -> list[dict]:
    rows = []
    seen: set[tuple] = set()
    for row in batch:
        if str(row.get("in_sealed_window", "")).lower() in {"true", "1"}:
            continue
        if not row.get("earliest_availability_utc") or as_decimal(row.get("change")) is None:
            continue
        ticker = str(row.get("ticker", "")).upper()
        if ticker not in BENCHMARK:
            continue
        key = (ticker, str(row.get("accession", "")), str(row.get("concept", "")),
               str(row.get("period_end", "")))
        if key in seen:
            raise ValueError(f"duplicate event identity: {key}")
        seen.add(key)
        rows.append({
            "ticker": ticker, "cik": str(row.get("cik", "")),
            "accession": str(row.get("accession", "")), "concept": str(row.get("concept", "")),
            "period_end": str(row.get("period_end", "")), "filed": str(row.get("filed", "")),
            "available_at": str(row["earliest_availability_utc"]),
            "change_usd": as_decimal(row.get("change")),
            "prior_value_usd": as_decimal(row.get("previous_value")),
            "benchmark": BENCHMARK[ticker],
        })
    return sorted(rows, key=lambda row: (row["available_at"], row["ticker"], row["accession"], row["concept"]))


def main() -> int:
    sync.load_local_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-batch-sha256", required=True)
    parser.add_argument("--out", default="results/revision-events-snowflake.csv")
    parser.add_argument("--summary", default="results/revision-events-snowflake.json")
    args = parser.parse_args()
    if args.event_batch_sha256 == "":
        parser.error("an immutable SEC obligation panel batch hash is required")

    connection = snowflake_connection()
    try:
        source_events = read_batch(connection, "sec_obligation_facts", args.event_batch_sha256)
        if not source_events:
            raise ValueError("event batch not found in Snowflake")
        events = event_rows(source_events)
        if not events:
            raise ValueError("no eligible timestamped development events in batch")
        bars: dict[str, dict[datetime, Decimal]] = {}
        for batch_sha in PRICE_BATCHES:
            payloads = read_batch(connection, "massive_bars", batch_sha)
            if not payloads:
                raise ValueError(f"pinned price batch not found: {batch_sha}")
            for row in payloads:
                ticker = str(row["ticker"]).upper()
                stamp = bar_time(str(row["bar_time_utc"]))
                close = as_decimal(row.get("close"))
                if close is None or close <= 0:
                    raise ValueError(f"invalid close for {ticker} at {stamp.isoformat()}")
                series = bars.setdefault(ticker, {})
                if stamp in series:
                    raise ValueError(f"duplicate bar for {ticker} at {stamp.isoformat()}")
                series[stamp] = close
        dividends = []
        for batch_sha in DIVIDEND_BATCHES:
            payloads = read_batch(connection, "massive_dividends", batch_sha)
            if not payloads:
                raise ValueError(f"pinned dividend batch not found: {batch_sha}")
            dividends.extend(payloads)
    finally:
        connection.close()

    missing = sorted({symbol for row in events for symbol in (row["ticker"], row["benchmark"], "SPY")
                      if symbol not in bars})
    if missing:
        raise ValueError(f"pinned Massive batches are missing required tickers: {missing}")

    dividends_by_ticker: dict[str, list[dict]] = {}
    for row in dividends:
        ticker = str(row.get("ticker", "")).upper()
        dividends_by_ticker.setdefault(ticker, []).append(row)
    required_tickers = {symbol for event in events for symbol in (event["ticker"], event["benchmark"], "SPY")}
    missing_dividend_coverage = sorted(required_tickers - set(dividends_by_ticker))
    if missing_dividend_coverage:
        raise ValueError(f"pinned dividend batches lack required ticker coverage: {missing_dividend_coverage}")
    bars = {ticker: total_return_series(series, dividends_by_ticker.get(ticker, []))
            for ticker, series in bars.items()}

    output = []
    for event in events:
        row = {key: (str(value) if isinstance(value, Decimal) else value)
               for key, value in event.items()}
        for horizon in HORIZONS:
            raw = close_return(bars[event["ticker"]], event["available_at"], horizon)
            sector = close_return(bars[event["benchmark"]], event["available_at"], horizon)
            market = close_return(bars["SPY"], event["available_at"], horizon)
            row[f"raw_{horizon}"] = str(raw) if raw is not None else ""
            row[f"abnormal_sector_{horizon}"] = str(raw - sector) if raw is not None and sector is not None else ""
            row[f"abnormal_market_{horizon}"] = str(raw - market) if raw is not None and market is not None else ""
        output.append(row)

    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(output[0])
    with out_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output)

    summary_rows = []
    for ticker in sorted({row["ticker"] for row in output}):
        for concept in sorted({row["concept"] for row in output if row["ticker"] == ticker}):
            subset = [row for row in output if row["ticker"] == ticker and row["concept"] == concept]
            result = {"ticker": ticker, "concept": concept, "events": len(subset)}
            for horizon in HORIZONS:
                for measure in (f"raw_{horizon}", f"abnormal_sector_{horizon}", f"abnormal_market_{horizon}"):
                    vals = [Decimal(row[measure]) for row in subset if row[measure] != ""]
                    result[measure + "_n"] = len(vals)
                    result[measure + "_mean"] = str(sum(vals) / len(vals)) if vals else None
                    result[measure + "_median"] = str(median(vals)) if vals else None
            summary_rows.append(result)

    receipt = {
        "study": "descriptive daily equity disclosure-revision event study",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "event_source": "sec_obligation_facts",
        "event_batch_sha256": args.event_batch_sha256,
        "price_source": "Massive split-adjusted daily aggregates, transformed to dividend-adjusted outcome prices using pinned dividend historical_adjustment_factor values",
        "price_batch_sha256": list(PRICE_BATCHES),
        "dividend_batch_sha256": list(DIVIDEND_BATCHES),
        "event_rows_in_source": len(source_events), "eligible_events": len(events),
        "unique_accessions": len({row["accession"] for row in events}),
        "tickers": sorted({row["ticker"] for row in events}),
        "horizons_sessions": list(HORIZONS),
        "entry_rule": "first daily bar timestamp strictly after conservative availability timestamp; return starts at that close",
        "benchmark_map": BENCHMARK,
        "limitations": [
            "development-only descriptive event study; no strategy simulation or causal claim",
            "SEC XBRL observations and issuer RPO/change-order changes are not analyst consensus surprises",
            "availability is the recorded conservative timestamp; earlier press releases/calls are not comprehensively resolved",
            "XBRL panel covers PWR/ETN only; the four-name market basket does not imply four-name event coverage",
            "overlapping horizons and repeated issuer/accession clusters are dependent; means/medians are not independent-event inference",
            "Massive aggregate bars are split-adjusted but not dividend-adjusted; this run multiplies by the source's cumulative dividend adjustment factor to form realized total-return outcomes, not predictive features",
            "no equities L2/L3, no perps, and no Binance data are used",
        ],
        "group_summary": summary_rows,
        "csv_sha256": __import__("hashlib").sha256(out_path.read_bytes()).hexdigest(),
    }
    summary_path = ROOT / args.summary
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    receipt["snowflake_artifacts"] = {
        "table": "VECTOR_RESEARCH.RAW.RESEARCH_ARTIFACTS",
        "csv_sha256": receipt["csv_sha256"],
        "provenance": "exact report content stored with event, price, and dividend source batch hashes",
    }
    summary_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    input_lineage = {
        "event_batch_sha256": receipt["event_batch_sha256"],
        "price_batch_sha256": receipt["price_batch_sha256"],
        "dividend_batch_sha256": receipt["dividend_batch_sha256"],
    }
    uploaded = publish_artifacts([out_path, summary_path], generated_at=receipt["generated_at_utc"],
                                 input_lineage=input_lineage)
    print(f"wrote {out_path.relative_to(ROOT)} events={len(events)} accessions={receipt['unique_accessions']}")
    print(f"wrote {summary_path.relative_to(ROOT)}; Snowflake artifacts={len(uploaded)}")
    for name, sha256 in uploaded.items():
        print(f"Snowflake artifact {name} sha256={sha256}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"event study failed ({type(exc).__name__}); details suppressed", file=sys.stderr)
        raise SystemExit(1)
