#!/usr/bin/env python3
"""Capture the Hyperliquid public streams to JSONL, read only.

Subscribes to the book snapshots, trades and asset context for the four traded coins, appends one JSON
object per message with a receive timestamp, and writes a manifest with the counts. Public endpoints only,
no orders, no private data. Bounded by --minutes so it can run in the background.

    python3 scripts/collect_hyperliquid_ws.py --minutes 240
"""
from __future__ import annotations

import argparse
import asyncio
import collections
import json
import time
from pathlib import Path

import websockets

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "hyperliquid" / "ws"
URL = "wss://api.hyperliquid.xyz/ws"
COINS = ["BTC", "ETH", "GAS", "SPX"]


async def capture(path: Path, minutes: float, counts: collections.Counter) -> None:
    deadline = time.time() + minutes * 60
    while time.time() < deadline:
        try:
            async with websockets.connect(URL, ping_interval=20, ping_timeout=20,
                                          max_size=8 * 1024 * 1024) as ws:
                for coin in COINS:
                    await ws.send(json.dumps({"method": "subscribe",
                                              "subscription": {"type": "l2Book", "coin": coin}}))
                    await ws.send(json.dumps({"method": "subscribe",
                                              "subscription": {"type": "trades", "coin": coin}}))
                    await ws.send(json.dumps({"method": "subscribe",
                                              "subscription": {"type": "activeAssetCtx", "coin": coin}}))
                with path.open("a") as handle:
                    while time.time() < deadline:
                        try:
                            raw = await asyncio.wait_for(ws.recv(), timeout=30)
                        except asyncio.TimeoutError:
                            continue
                        try:
                            message = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        channel = message.get("channel", "unknown")
                        if channel == "subscriptionResponse":
                            continue
                        counts[channel] += 1
                        handle.write(json.dumps({"recv_ts": time.time(), "channel": channel,
                                                 "data": message.get("data")},
                                                separators=(",", ":")) + "\n")
                        handle.flush()
        except Exception as error:
            counts[f"reconnect:{type(error).__name__}"] += 1
            await asyncio.sleep(3)


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=float, default=240)
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    path = OUT_DIR / f"ws-{stamp}.jsonl"
    counts: collections.Counter = collections.Counter()
    print(f"capturing to {path.relative_to(ROOT)} for {args.minutes} minutes")
    await capture(path, args.minutes, counts)
    manifest = {"file": str(path.relative_to(ROOT)), "minutes": args.minutes, "coins": COINS,
                "counts": dict(counts), "finished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (OUT_DIR / f"ws-{stamp}.manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print("counts:", dict(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
