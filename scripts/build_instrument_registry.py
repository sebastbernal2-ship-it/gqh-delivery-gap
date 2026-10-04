#!/usr/bin/env python3
"""Write the instrument registry: one record per tradeable contract class, with the fields both engines read.

Fields that we do not yet know are marked `to_confirm` rather than guessed. The registry feeds the graph as
instrument nodes and is the input to the perp replay adapter and the equity portfolio engine.

    python3 scripts/build_instrument_registry.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPLEX = ROOT / "results" / "complex-capex-quarterly.csv"
PANEL = ROOT / "results" / "market-panel.json"
OUT = ROOT / "docs" / "scan" / "instruments.jsonl"


def main() -> int:
    groups = json.loads(PANEL.read_text())["groups"]
    equity_groups = {ticker: group for group, payload in groups.items() for ticker in [s["ticker"] for s in payload["series"]]}
    complex_tickers = sorted({row["ticker"] for row in csv.DictReader(COMPLEX.open())})
    records = []

    terms_path = ROOT / "results" / "hyperliquid-contract-terms.json"
    terms = json.loads(terms_path.read_text()) if terms_path.exists() else {"contracts": {}, "retrieved_at": None}
    for coin, depth in (("BTC", 3_499_318), ("ETH", 8_737_856), ("GAS", 1_169), ("SPX", 3_991)):
        venue_terms = terms.get("contracts", {}).get(coin, {})
        records.append({
            "id": f"instrument:perp:{coin}",
            "class": "perpetual_future",
            "underlying": coin,
            "venue": "hyperliquid",
            "quote": "USD",
            "margined": "linear",
            "session": "24/7",
            "funding_interval_hours": 1,
            "taker_fee_bps": 4.5,
            "maker_fee_bps": 1.5,
            "fee_source": "declared in docs/plan/cascade-protocol.md; matches the base tier range on the venue fee page",
            "fee_verified": False,
            "size_decimals": venue_terms.get("size_decimals"),
            "max_leverage": venue_terms.get("max_leverage"),
            "terms_source": "results/hyperliquid-contract-terms.json",
            "terms_retrieved_at": terms.get("retrieved_at"),
            "tick_size": "to_confirm",
            "short_borrow": "not required, shorts are native",
            "depth_10bps_usd_median": depth,
            "usable": coin in ("BTC", "ETH"),
            "notes": "depth inside 10 bps from the recorded tape; GAS and SPX are too thin for capacity",
        })

    for ticker in complex_tickers:
        records.append({
            "id": f"instrument:equity:{ticker}",
            "class": "cash_equity",
            "underlying": ticker,
            "venue": "us_primary",
            "quote": "USD",
            "group": equity_groups.get(ticker, "unlisted"),
            "session": "09:30-16:00 ET",
            "settlement": "T+1",
            "tick_size": 0.01,
            "short_borrow": "to_confirm",
            "borrow_cost_bps_annual": "to_confirm",
            "corporate_actions": "dividends, splits and mergers must be applied from a dated table",
            "cost_model": "spread plus commission plus borrow, bucketed by monthly dollar volume",
            "notes": "cost buckets declared in docs/theses/t-intensity-charge.md",
        })

    OUT.write_text("".join(json.dumps(record) + "\n" for record in records))
    perps = sum(1 for record in records if record["class"] == "perpetual_future")
    equities = len(records) - perps
    usable = sum(1 for record in records if record.get("usable"))
    print(f"wrote {OUT.relative_to(ROOT)}: {perps} perpetuals ({usable} usable), {equities} equities")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
