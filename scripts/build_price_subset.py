#!/usr/bin/env python3
"""Copy the price series every reproduced artifact needs into a small committed subset.

A judge's clone has no local price cache: `results/bar-cache/` is ignored because it is 62 MB of
data no result file should depend on being present by accident. The results that do need prices are
reproducible from a much smaller declared set, so this script copies exactly those tickers into
`results/price-subset/`, records the union it used, and leaves the local cache alone.

    python3 scripts/build_price_subset.py
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

# every input whose tickers must have prices for the reproduction tier to be exact
TICKER_SOURCES = ("results/revenue-vintages-pit.csv", "results/capex-vintages-pit.csv",
                  "results/margins-vintages.csv", "results/assets-vintages.csv")


def wanted_tickers() -> set[str]:
    tickers: set[str] = set()
    for name in TICKER_SOURCES:
        path = ROOT / name
        if not path.exists():
            continue
        with path.open() as handle:
            tickers |= {row["ticker"].strip() for row in csv.DictReader(handle) if row.get("ticker")}
    try:
        from run_eia_load_specialist import EXPOSURE
        tickers |= set(EXPOSURE)
    except Exception:                     # the exposure map is optional for the subset
        pass
    return tickers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, nargs="*",
                        default=[ROOT / "results" / "bar-cache"])
    parser.add_argument("--subset", type=Path, default=ROOT / "results" / "price-subset")
    args = parser.parse_args()
    tickers = sorted(wanted_tickers())
    args.subset.mkdir(parents=True, exist_ok=True)
    copied, missing, total = [], [], 0
    for ticker in tickers:
        source = None
        for candidate in args.candidates:
            for name in (f"{ticker}.json", f"{ticker}.csv"):
                path = candidate / name
                if path.exists():
                    source = path
                    break
            if source:
                break
        if source is None:
            missing.append(ticker)
            continue
        target = args.subset / source.name
        shutil.copyfile(source, target)
        copied.append(ticker)
        total += target.stat().st_size
    manifest = {"schema": "price-subset-v1", "tickers": copied, "missing": missing,
                "bytes": total, "sources": list(TICKER_SOURCES),
                "note": "copied from the local bar cache; the full cache stays ignored"}
    (args.subset / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print("subset: %d tickers, %d missing, %.1f MB written to %s" % (
        len(copied), len(missing), total / 1e6, args.subset))
    if missing:
        print("missing (no price series found):", ", ".join(missing[:12]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
