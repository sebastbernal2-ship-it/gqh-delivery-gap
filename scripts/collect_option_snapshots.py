#!/usr/bin/env python3
"""Start a forward option snapshot archive, because options history is a paid product and forward capture is free.

The repo's own data access note records the position honestly: live option chain snapshots are free, historical
chains are paid. So the only way to have options history later is to start recording now, at the names the
mechanism cares about, with an implied volatility and an open interest per strike.

What this writes: one file per run under results/option-snapshots/, named by the UTC timestamp, holding the
underlying price, the expiries, and per contract the strike, bid, ask, last, implied volatility, open interest
and volume. Plus an index file so a later reader can see how many snapshots exist and when they started.

Nothing is interpreted. This is a capture, and a single snapshot is not a series.

Usage:
    python3 scripts/collect_option_snapshots.py [--names 12] [--expiries 4]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "results" / "option-snapshots"
INDEX = OUT_DIR / "index.json"

NAMES = ["DLR", "EQIX", "IRM", "AMT", "PWR", "ETN", "VRT", "GEV", "CEG", "VST", "NRG", "CRWV", "NBIS",
         "ORCL", "NVDA", "TLN"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--names", type=int, default=12)
    parser.add_argument("--expiries", type=int, default=4)
    args = parser.parse_args(argv)

    import yfinance as yf

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot: dict = {"taken_utc": stamp, "source": "yfinance option chains, free, forward only", "names": {}}
    for ticker in NAMES[:args.names]:
        entry: dict = {"expiries": [], "underlying": None, "contracts": 0, "error": ""}
        try:
            handle = yf.Ticker(ticker)
            expiries = list(handle.options[:args.expiries])
            entry["expiries"] = expiries
            fast = handle.fast_info
            try:
                entry["underlying"] = float(fast.get("lastPrice") or fast.get("previousClose") or 0)
            except Exception:
                entry["underlying"] = None
            rows: list[dict] = []
            for expiry in expiries:
                try:
                    chain = handle.option_chain(expiry)
                except Exception:
                    continue
                for side, frame in (("call", chain.calls), ("put", chain.puts)):
                    for record in frame.to_dict("records"):
                        rows.append({
                            "expiry": expiry, "side": side,
                            "strike": record.get("strike"), "bid": record.get("bid"),
                            "ask": record.get("ask"), "last": record.get("lastPrice"),
                            "implied_vol": record.get("impliedVolatility"),
                            "open_interest": record.get("openInterest"),
                            "volume": record.get("volume"),
                        })
            entry["contracts"] = len(rows)
            entry["chain"] = rows
        except Exception as error:
            entry["error"] = str(error)[:120]
        snapshot["names"][ticker] = entry
        print(f"  {ticker:6s} expiries {len(entry['expiries'])} contracts {entry['contracts']:5d} "
              f"{entry['error'][:40]}")

    path = OUT_DIR / f"snapshot-{stamp}.json"
    path.write_text(json.dumps(snapshot) + "\n")
    index = {"snapshots": [], "names_declared": NAMES}
    if INDEX.exists():
        try:
            index = json.loads(INDEX.read_text())
        except Exception:
            pass
    index["snapshots"].append({"taken_utc": stamp, "file": path.name,
                               "names": sum(1 for name in snapshot["names"] if snapshot["names"][name]["contracts"]),
                               "contracts": sum(name["contracts"] for name in snapshot["names"].values())})
    index["first_snapshot_utc"] = index["snapshots"][0]["taken_utc"]
    index["boundary"] = ("forward capture only. Historical chains are a paid product, so any history this "
                         "archive has is the history that starts at the first snapshot")
    INDEX.write_text(json.dumps(index, indent=2) + "\n")
    print(f"\nsnapshot written: {path.name}")
    print(f"contracts: {index['snapshots'][-1]['contracts']} | snapshots in the archive: {len(index['snapshots'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
