#!/usr/bin/env python3
"""Land the credit and equity panel the credit gauntlet measures against.

Two sources, both read only, both already reachable from this environment:

- **Credit, FRED CSV export.** Keyless. The ICE BofA series are capped at 795 daily rows by the export
  endpoint, which fixes the study window at 2023-10-03 to 2026-10-01. The cap is recorded in the manifest
  rather than worked around, because a window chosen from the data is the specific error the window file
  warns about.
- **Equity, the shared landing table.** Daily adjusted bars for the four names the mechanism implicates and
  SPY, all inside the credit window.

Nothing here measures a relation. This script only lands data and states its provenance.

Usage:
    python scripts/build_credit_panel.py
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_CSV = ROOT / "results" / "credit-panel.csv"
OUT_JSON = ROOT / "results" / "credit-panel.json"

FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
FRED_API = ("https://api.stlouisfed.org/fred/series/observations?series_id={series}"
            "&api_key={key}&file_type=json&observation_start=1950-01-01")
CREDIT_SERIES = {
    "credit:hy:oas": ("BAMLH0A0HYM2", "ICE BofA US High Yield Index option adjusted spread, percent"),
    "credit:ig:oas": ("BAMLC0A0CM", "ICE BofA US Corporate Index option adjusted spread, percent"),
    "credit:bbb:oas": ("BAMLC0A4CBBB", "ICE BofA BBB US Corporate Index option adjusted spread, percent"),
    "credit:ccc:oas": ("BAMLH0A3HYC", "ICE BofA CCC and lower US High Yield Index option adjusted spread, percent"),
    "credit:hy:yield": ("BAMLH0A0HYM2EY", "ICE BofA US High Yield Index effective yield, percent"),
}
# The long history family. The ICE BofA series are capped at three years by ICE licensing even through
# the official API, so the long window uses the Moody's yields, which FRED serves in full.
LONG_SERIES = {
    "credit:baa:10y": ("BAA10Y", "Moody's Baa corporate yield minus 10 year Treasury, percent"),
    "credit:aaa:10y": ("AAA10Y", "Moody's Aaa corporate yield minus 10 year Treasury, percent"),
    "credit:baa:level": ("DBAA", "Moody's Baa corporate bond yield, percent"),
    "credit:aaa:level": ("DAAA", "Moody's Aaa corporate bond yield, percent"),
}
LONG_TIER_GAP = ("credit:quality-gap", "credit:baa:level", "credit:aaa:level",
                 "Baa yield minus Aaa yield, the quality and tier gap, the long history analogue of the "
                 "BBB minus CCC reading")

# The tier gap is derived here from two landed series, so it carries no extra source risk.
TIER_GAP = ("credit:tier-gap", "credit:bbb:oas", "credit:ccc:oas",
            "BBB spread minus CCC spread, the weakest link reading, percent")
EQUITY_TICKERS = ["DLR", "EME", "ETN", "PWR", "SPY"]


def fetch_fred(series: str) -> dict[str, float]:
    """Fetch through curl, which is the client this environment actually lets through."""
    command = ["curl", "-sS", "--max-time", "90", "--retry", "3", "--retry-delay", "2",
               FRED.format(series=series)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        raise SystemExit(f"{series}: fetch failed: {result.stderr.strip()[:200]}")
    body = result.stdout
    out: dict[str, float] = {}
    for number, line in enumerate(body.splitlines()):
        if number == 0 or not line.strip():
            continue
        parts = line.split(",")
        if len(parts) < 2:
            continue
        stamp, value = parts[0].strip(), parts[1].strip()
        if not stamp or value in ("", ".", "NaN"):
            continue
        try:
            out[stamp[:10]] = float(value)
        except ValueError:
            continue
    return out


def fetch_fred_api(series: str, key: str) -> dict[str, float]:
    """Fetch full history through the official API. The key is used in process and never printed."""
    command = ["curl", "-sS", "--max-time", "120", "--retry", "3", "--retry-delay", "2",
               FRED_API.format(series=series, key=key)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        raise SystemExit(f"{series}: API fetch failed: {result.stderr.strip()[:200]}")
    payload = json.loads(result.stdout)
    if "observations" not in payload:
        raise SystemExit(f"{series}: API refused: {json.dumps(payload)[:200]}")
    out: dict[str, float] = {}
    for row in payload["observations"]:
        value = str(row.get("value", "")).strip()
        if not value or value == ".":
            continue
        try:
            out[str(row["date"])[:10]] = float(value)
        except (TypeError, ValueError):
            continue
    return out


def query(sql: str) -> list[dict]:
    """One read only query through the Tiger CLI, which holds the connection and the read only setting."""
    result = subprocess.run(["tiger", "db", "query", "-o", "json", "--command", sql],
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"query failed: {result.stderr.strip()[:200]}")
    payload = json.loads(result.stdout)
    rows: list[dict] = []
    for result_set in payload.get("result_sets", []):
        columns = [c["name"] for c in result_set["columns"]]
        for row in result_set["rows"]:
            rows.append(dict(zip(columns, row)))
    return rows


def fetch_equity(tickers: list[str]) -> dict[str, dict[str, float]]:
    names = ",".join(f"'{ticker}'" for ticker in tickers)
    rows = query("SELECT payload_json->>'ticker' AS ticker, payload_json->>'bar_time_utc' AS stamp, "
                 "payload_json->>'close' AS close FROM public.gqh_source_records "
                 f"WHERE source_id='massive_bars' AND payload_json->>'ticker' IN ({names}) "
                 "ORDER BY stamp")
    out: dict[str, dict[str, float]] = {ticker: {} for ticker in tickers}
    for row in rows:
        try:
            out[row["ticker"]][str(row["stamp"])[:10]] = float(row["close"])
        except (TypeError, ValueError):
            continue
    return out


def main() -> int:
    rows: list[dict] = []
    manifest: dict = {
        "generated_by": "scripts/build_credit_panel.py",
        "credit_route": "FRED CSV export, keyless",
        "credit_route_limit": "the ICE BofA series return 795 daily rows and ignore cosd, so the window is "
                              "set by the vendor and not by us",
        "credit_series": {},
        "equity_route": "public.gqh_source_records, source_id = 'massive_bars', adjusted bars",
        "equity_series": {},
    }

    key = os.environ.get("FRED_API_KEY", "").strip()
    manifest["fred_api_key_present"] = bool(key)
    manifest["fred_api_note"] = ("the official API returns 786 observations for every ICE BofA series even "
                                 "with a valid key, so the three year window is ICE licensing on FRED and "
                                 "not a limit of the keyless export")

    landed: dict[str, dict[str, float]] = {}
    for label, (series, meaning) in CREDIT_SERIES.items():
        values = fetch_fred(series)
        if not values:
            raise SystemExit(f"{series}: returned no usable observations")
        landed[label] = values
        manifest["credit_series"][label] = {
            "fred_id": series, "meaning": meaning, "rows": len(values),
            "first": min(values), "last": max(values),
        }

    label, left, right, meaning = TIER_GAP
    shared = sorted(set(landed[left]) & set(landed[right]))
    landed[label] = {stamp: landed[left][stamp] - landed[right][stamp] for stamp in shared}
    manifest["credit_series"][label] = {
        "derived_from": [left, right], "meaning": meaning, "rows": len(shared),
        "first": shared[0] if shared else None, "last": shared[-1] if shared else None,
    }

    if key:
        for label, (series, meaning) in LONG_SERIES.items():
            values = fetch_fred_api(series, key)
            if not values:
                raise SystemExit(f"{series}: the API route returned no usable observations")
            landed[label] = values
            manifest["credit_series"][label] = {
                "fred_id": series, "route": "api.stlouisfed.org with FRED_API_KEY",
                "meaning": meaning, "rows": len(values),
                "first": min(values), "last": max(values),
            }
        label, left, right, meaning = LONG_TIER_GAP
        shared = sorted(set(landed[left]) & set(landed[right]))
        landed[label] = {stamp: landed[left][stamp] - landed[right][stamp] for stamp in shared}
        manifest["credit_series"][label] = {
            "derived_from": [left, right], "meaning": meaning, "rows": len(shared),
            "first": shared[0] if shared else None, "last": shared[-1] if shared else None,
        }
    else:
        manifest["long_series_skipped"] = "no FRED_API_KEY in the environment, so the Moody's long history family was not landed"

    equity = fetch_equity(EQUITY_TICKERS)

    credit_dates = sorted({stamp for values in landed.values() for stamp in values})
    if not credit_dates:
        raise SystemExit("no credit observations landed")
    window_start, window_end = credit_dates[0], credit_dates[-1]
    equity_dates = sorted({stamp for values in equity.values() for stamp in values})
    overlap_start = max(window_start, equity_dates[0] if equity_dates else window_start)
    manifest["study_window"] = {
        "start": window_start, "end": window_end,
        "source": "the ICE BofA series carry only three years on FRED by ICE licence; the Moody's family "
                  "carries full history, so the panel start is the earlier of the two",
        "equity_join_start": overlap_start,
        "equity_note": "the landed adjusted equity bars begin 2016-01-04, which is the binding constraint "
                       "on the long window",
    }
    manifest["development_end"] = "2026-02-24"
    manifest["holdout_start"] = "2026-02-25"
    manifest["holdout_opened"] = False

    for ticker, values in equity.items():
        inside = {stamp: value for stamp, value in values.items()
                  if window_start <= stamp <= window_end}
        manifest["equity_series"][ticker] = {
            "rows_in_window": len(inside), "rows_landed_total": len(values),
            "first_in_window": min(inside) if inside else None,
            "last_in_window": max(inside) if inside else None,
        }

    for stamp in sorted({s for values in landed.values() for s in values}):
        for label, values in landed.items():
            if stamp in values:
                rows.append({"date": stamp, "series": label, "value": f"{values[stamp]:.6f}"})
    for ticker in EQUITY_TICKERS:
        for stamp in sorted(equity.get(ticker, {})):
            if window_start <= stamp <= window_end:
                rows.append({"date": stamp, "series": f"equity:{ticker}",
                             "value": f"{equity[ticker][stamp]:.6f}"})

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["date", "series", "value"])
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: (row["date"], row["series"])))

    manifest["rows_written"] = len(rows)
    manifest["inside_window_equity_rows"] = sum(1 for row in rows if row["series"].startswith("equity:"))
    OUT_JSON.write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"credit-panel.csv written: {len(rows)} rows")
    print(f"window: {window_start} to {window_end}")
    for label, block in manifest["credit_series"].items():
        print(f"  {label:20s} rows={block['rows']:5d} {block['first']} to {block['last']}")
    for ticker, block in manifest["equity_series"].items():
        print(f"  equity:{ticker:4s} rows_in_window={block['rows_in_window']:4d} "
              f"of {block['rows_landed_total']} {block['first_in_window']} to {block['last_in_window']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
