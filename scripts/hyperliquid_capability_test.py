#!/usr/bin/env python3
"""Capability test for the Hyperliquid public streams, read only.

Connects to the public websocket and records what each subscription actually publishes: cadence, field
names, sample payloads. Writes results/hyperliquid-capability.json and prints the findings. No orders, no
private endpoints, no state.

    python3 scripts/hyperliquid_capability_test.py --seconds 120
"""
from __future__ import annotations

import argparse
import asyncio
import collections
import json
import statistics
import time
from pathlib import Path

import websockets

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "hyperliquid-capability.json"
URL = "wss://api.hyperliquid.xyz/ws"
COINS = ["BTC", "ETH", "GAS", "SPX"]


async def consume(ws, seconds: float, results: dict) -> None:
    started = time.time()
    while time.time() - started < seconds:
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=5)
        except asyncio.TimeoutError:
            continue
        except Exception as error:  # connection closed
            results.setdefault("errors", []).append(str(error))
            return
        try:
            message = json.loads(raw)
        except json.JSONDecodeError:
            continue
        channel = message.get("channel", "unknown")
        bucket = results["channels"].setdefault(channel, {
            "count": 0, "coins": collections.Counter(), "first": None, "last": None,
            "intervals": [], "fields": None, "sample": None, "sub": None})
        bucket["count"] += 1
        now = time.time()
        if bucket["last"] is not None:
            bucket["intervals"].append(now - bucket["last"])
        bucket["last"] = now
        if bucket["first"] is None:
            bucket["first"] = now
        data = message.get("data")
        coin = None
        if isinstance(data, dict):
            coin = data.get("coin")
        elif isinstance(data, list) and data and isinstance(data[0], dict):
            coin = data[0].get("coin")
        if coin:
            bucket["coins"][coin] += 1
        if bucket["fields"] is None:
            if isinstance(data, dict):
                bucket["fields"] = sorted(data.keys())
            elif isinstance(data, list) and data and isinstance(data[0], dict):
                bucket["fields"] = sorted(data[0].keys())
        if bucket["sample"] is None:
            bucket["sample"] = json.dumps(message)[:1200]


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=120)
    args = parser.parse_args()

    results: dict = {"url": URL, "seconds": args.seconds, "coins": COINS, "channels": {}}
    async with websockets.connect(URL, ping_interval=20, ping_timeout=20) as ws:
        for coin in COINS:
            await ws.send(json.dumps({"method": "subscribe", "subscription": {"type": "l2Book", "coin": coin}}))
            await ws.send(json.dumps({"method": "subscribe", "subscription": {"type": "trades", "coin": coin}}))
        await ws.send(json.dumps({"method": "subscribe", "subscription": {"type": "activeAssetCtx"}})) if False else None
        for coin in COINS:
            await ws.send(json.dumps({"method": "subscribe", "subscription": {"type": "activeAssetCtx", "coin": coin}}))
        await ws.send(json.dumps({"method": "subscribe", "subscription": {"type": "allMids"}}))
        # subscription acknowledgements
        for _ in range(4 * len(COINS) + 1):
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=5)
            except asyncio.TimeoutError:
                break
            message = json.loads(raw)
            if message.get("channel") == "subscriptionResponse":
                results.setdefault("acknowledged", []).append(message.get("data", {}).get("subscription"))
        await consume(ws, args.seconds, results)

    report = {"url": URL, "seconds": args.seconds, "coins": COINS, "channels": {}}
    for channel, bucket in results["channels"].items():
        intervals = [value for value in bucket["intervals"] if value > 0]
        report["channels"][channel] = {
            "messages": bucket["count"],
            "messages_per_second": round(bucket["count"] / max(1.0, args.seconds), 2),
            "median_interval_ms": round(statistics.median(intervals) * 1000) if intervals else None,
            "coins": dict(bucket["coins"]),
            "fields": bucket["fields"],
            "sample": bucket["sample"],
        }
    report["acknowledged"] = results.get("acknowledged", [])
    report["errors"] = results.get("errors", [])
    OUT.write_text(json.dumps(report, indent=1) + "\n")
    for channel, block in report["channels"].items():
        print(f"{channel}: {block['messages']} messages in {args.seconds:.0f}s "
              f"({block['messages_per_second']}/s), median interval {block['median_interval_ms']} ms")
        print(f"  fields: {block['fields']}")
        print(f"  coins: {block['coins']}")
        print(f"  sample: {block['sample'][:400]}")
    print("errors:", report["errors"])
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
