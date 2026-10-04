#!/usr/bin/env python3
"""Fetch the venue's contract and fee terms, and record them with their sources.

Reads the public information endpoint for contract terms (size decimals, maximum leverage per coin) and
the venue's published fee schedule page for the fee tiers. Everything is written with the URL and the
retrieval time, so the registry no longer carries hardcoded numbers.

    python3 scripts/build_hyperliquid_contract_terms.py
"""
from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "hyperliquid-contract-terms.json"
INFO_URL = "https://api.hyperliquid.xyz/info"
FEES_URL = "https://hyperliquid.gitbook.io/hyperliquid-docs/trading/fees"
COINS = ["BTC", "ETH", "GAS", "SPX"]


def post(payload: dict) -> dict:
    request = urllib.request.Request(INFO_URL, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json",
                                              "User-Agent": "gqh research"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def get_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "gqh research"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read().decode("utf-8", errors="ignore")


def main() -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report: dict = {"retrieved_at": now, "sources": {"contracts": INFO_URL, "fees": FEES_URL}}

    meta = post({"type": "meta"})
    universe = {item["name"]: item for item in meta.get("universe", [])}
    report["contracts"] = {}
    for coin in COINS:
        item = universe.get(coin)
        report["contracts"][coin] = {
            "listed": item is not None,
            "size_decimals": item.get("szDecimals") if item else None,
            "max_leverage": item.get("maxLeverage") if item else None,
            "only_isolated": item.get("onlyIsolated") if item else None,
        }
    report["universe_size"] = len(universe)

    fees: dict = {"page": FEES_URL}
    try:
        text = get_text(FEES_URL)
        stripped = re.sub(r"<[^>]+>", " ", text)
        stripped = re.sub(r"\s+", " ", stripped)
        fees["fetched"] = True
        fees["bytes"] = len(text)
        # the page states taker and maker rates in prose and tables; capture the neighbourhoods verbatim
        for label, pattern in (("taker", r"taker[^.]{0,120}"), ("maker", r"maker[^.]{0,120}")):
            match = re.search(pattern, stripped, flags=re.IGNORECASE)
            fees[f"{label}_snippet"] = match.group(0).strip()[:200] if match else None
        numbers = re.findall(r"([0-9]+\.[0-9]{2,4})\s?%", stripped)
        fees["percentages_seen"] = sorted(set(numbers))[:12]
        fees["note"] = ("percentages are captured verbatim from the page; the registry keeps the declared "
                        "taker and maker rates used by the studies until a human confirms the tier")
    except Exception as error:
        fees["fetched"] = False
        fees["error"] = str(error)
    report["fees"] = fees

    OUT.write_text(json.dumps(report, indent=1) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print("contracts:", json.dumps(report["contracts"]))
    print("fee page fetched:", fees.get("fetched"), "| taker snippet:", (fees.get("taker_snippet") or "")[:120])
    print("percentages seen:", fees.get("percentages_seen"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
