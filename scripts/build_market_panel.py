#!/usr/bin/env python3
"""Declare the market panel this research actually needs, then fetch it and record what arrived.

Why: the equity cache in results/bar-cache was a byproduct of the earlier scan node space, which was built for
the power delivery mechanism. It holds 242 series, and it is missing the names the current mechanism needs:
CoreWeave, Nebius, Vertiv, GE Vernova, Talen, the credit ETFs, the volatility index, and several utilities.
A cache that grew around a narrower question is not a panel.

This script declares the panel, fetches it through the same cached loader the scan uses, and writes a manifest
that states per ticker whether it arrived, how many observations, and its date range. A ticker that fails is
recorded as failed rather than dropped.

Usage:
    python3 scripts/build_market_panel.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from scan.series import load_bars  # noqa: E402

OUT = ROOT / "results" / "market-panel.json"

PANEL = {
    "data_center_reit": ["DLR", "EQIX", "IRM", "AMT", "CCI", "SBAC", "WY"],
    "compute_and_ai": ["NVDA", "AMD", "AVGO", "MRVL", "MU", "SMCI", "CRWV", "NBIS", "ARM", "AI", "APLD",
                       "IREN", "CORZ", "WULF", "BTDR", "CIFR"],
    "hyperscaler": ["MSFT", "AMZN", "GOOGL", "META", "AAPL", "ORCL"],
    "buildout": ["PWR", "EME", "MTZ", "DY", "ETN", "J", "HUBB", "ROK", "VRT", "GEV", "NVT", "FIX", "STRL",
                 "AGX", "PRIM"],
    "power": ["NRG", "VST", "D", "SO", "NEE", "EXC", "CEG", "TLN", "AEP", "DUK", "PPL", "ETR", "PCG", "SRE",
              "EIX"],
    "fuel_and_nuclear": ["URA", "CCJ", "OKLO", "SMR", "NNE", "LEU", "BWXT", "FSLR", "ENPH", "BE", "PLUG"],
    "rates_and_credit": ["TLT", "IEF", "HYG", "LQD", "JNK", "BKLN", "AGG", "EMB"],
    "market_and_vol": ["SPY", "QQQ", "^VIX", "^TNX", "^GSPC", "^NDX"],
    "commodity": ["NG=F", "HG=F", "CL=F", "GC=F", "SI=F", "URA"],
}


def main() -> int:
    manifest: dict = {"generated_by": "scripts/build_market_panel.py",
                      "route": "the cached daily loader, which fetches through yfinance on a miss",
                      "panel": {}, "groups": {}}
    total_series = 0
    total_obs = 0
    for group, tickers in PANEL.items():
        arrived, failed = [], []
        for ticker in tickers:
            bars = load_bars(ticker)
            if bars:
                days = sorted(bars)
                arrived.append({"ticker": ticker, "observations": len(bars),
                                "first": days[0], "last": days[-1]})
                total_series += 1
                total_obs += len(bars)
            else:
                failed.append(ticker)
        manifest["groups"][group] = {
            "declared": len(tickers), "arrived": len(arrived), "failed": failed,
            "series": arrived,
        }
        print(f"{group:20s} declared {len(tickers):2d} | arrived {len(arrived):2d} | failed {failed}")
    manifest["series_available"] = total_series
    manifest["observations"] = total_obs
    manifest["boundary"] = ("daily closes from a free loader. No intraday, no options, no futures term "
                            "structure, and the futures series are continuous front month rather than "
                            "back adjusted, so a roll is a jump in the series")
    OUT.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"\nseries available: {total_series} | observations: {total_obs:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
