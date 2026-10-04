#!/usr/bin/env python3
"""Poll the venue's book snapshot endpoint once per second, read only.

The websocket publishes book snapshots about every five seconds. One second polling closes that gap for
fill modelling, at four requests per second across the four traded coins. Writes JSONL with the receive
timestamp, the venue time and the level arrays, plus a manifest.

    python3 scripts/collect_hyperliquid_book.py --minutes 100
"""
from __future__ import annotations

import argparse
import asyncio
import collections
import json
import time
from pathlib import Path

import aiohttp

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "hyperliquid" / "book"
URL = "https://api.hyperliquid.xyz/info"
COINS = ["BTC", "ETH", "GAS", "SPX"]


async def poll(session: aiohttp.ClientSession, coin: str) -> dict | None:
    try:
        async with session.post(URL, json={"type": "l2Book", "coin": coin}) as response:
            payload = await response.json()
    except Exception:
        return None
    return payload


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=float, default=100)
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    path = OUT_DIR / f"book-{stamp}.jsonl"
    counts: collections.Counter = collections.Counter()
    deadline = time.time() + args.minutes * 60
    async with aiohttp.ClientSession(headers={"User-Agent": "gqh research"}) as session:
        with path.open("a") as handle:
            while time.time() < deadline:
                started = time.time()
                results = await asyncio.gather(*[poll(session, coin) for coin in COINS])
                for coin, payload in zip(COINS, results):
                    if not payload or "levels" not in payload:
                        counts[f"empty:{coin}"] += 1
                        continue
                    counts[coin] += 1
                    handle.write(json.dumps({"recv_ts": time.time(), "coin": coin,
                                             "time": payload.get("time"),
                                             "levels": payload.get("levels")},
                                            separators=(",", ":")) + "\n")
                handle.flush()
                elapsed = time.time() - started
                await asyncio.sleep(max(0.05, args.interval - elapsed))
    manifest = {"file": str(path.relative_to(ROOT)), "minutes": args.minutes, "interval_seconds": args.interval,
                "coins": COINS, "counts": dict(counts),
                "finished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (OUT_DIR / f"book-{stamp}.manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print("counts:", dict(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
