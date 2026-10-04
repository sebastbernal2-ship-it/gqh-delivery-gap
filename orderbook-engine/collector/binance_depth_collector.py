#!/usr/bin/env python3
"""Capture Binance Futures depth and trade events into immutable JSONL segments.

Each five-minute window starts with a fresh REST depth snapshot, so every
window is independently replayable. Binance sends depth updates only, so a
window without a baseline snapshot cannot be reconstructed, and
collector/normalize_capture.py rejects such a capture.
"""

import asyncio
import gzip
import hashlib
import json
import math
import os
import signal
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import websockets


DATA_DIR = Path(os.environ.get("DATA_DIR", "/data/binance"))
SYMBOLS = [value.strip().upper() for value in os.environ.get("SYMBOLS", "BTCUSDT").split(",") if value.strip()]
DEPTH_SPEED = os.environ.get("DEPTH_SPEED", "100ms")
REST_LIMIT = int(os.environ.get("REST_LIMIT", "1000"))
CAPTURE_TRADES = os.environ.get("CAPTURE_TRADES", "1").lower() in {"1", "true", "yes"}
CAPTURE_INTERVAL_SECONDS = int(os.environ.get("CAPTURE_INTERVAL_SECONDS", "300"))
if CAPTURE_INTERVAL_SECONDS <= 0:
    raise ValueError("CAPTURE_INTERVAL_SECONDS must be positive")
STREAM_BASE = "wss://fstream.binance.com/stream"
REST_BASES = [
    os.environ.get("REST_BASE", "https://fapi.binance.com/fapi/v1/depth"),
    "https://www.binance.com/fapi/v1/depth",
]
EXCHANGE_INFO_BASES = [
    os.environ.get("EXCHANGE_INFO_BASE", "https://fapi.binance.com/fapi/v1/exchangeInfo"),
    "https://www.binance.com/fapi/v1/exchangeInfo",
]


class CaptureWriter:
    def __init__(self, symbol: str, kind: str):
        self.symbol = symbol
        self.kind = kind
        self.handle = None
        self.rejected_handle = None
        self.segment = None
        self.path = None
        self.started = None
        self.ended = None
        self.records = 0
        self.capture_id = f"{os.getpid()}-{time.time_ns()}"

    def write(self, stream: str, data: dict, raw: dict, captured_at=None):
        now = captured_at or datetime.now(timezone.utc)
        segment = int(now.timestamp()) // CAPTURE_INTERVAL_SECONDS
        if self.segment != segment:
            self.close()
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            self.segment = segment
            segment_start = datetime.fromtimestamp(
                segment * CAPTURE_INTERVAL_SECONDS, timezone.utc
            )
            label = segment_start.strftime("%Y%m%dT%H%M")
            prefix = self.symbol.lower() if self.kind == "depth" else f"{self.symbol.lower()}-trades"
            self.path = DATA_DIR / f"{prefix}-{label}-{self.capture_id}.jsonl.gz"
            self.handle = gzip.open(self.path, "at", encoding="utf-8")
            self.started = now.isoformat()
            self.records = 0
        captured = now.isoformat()
        payload = {"stream": stream, "data": data, "raw": raw}
        self.handle.write(f"{captured} {json.dumps(payload, separators=(',', ':'))}\n")
        self.handle.flush()
        self.ended = captured
        self.records += 1

    def write_rejected(self, reason: str, stream: str, data: dict, raw: dict, captured_at=None):
        if self.rejected_handle is None:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            self.rejected_handle = gzip.open(
                DATA_DIR / f"rejected-{self.kind}.jsonl.gz", "at", encoding="utf-8"
            )
        captured = (captured_at or datetime.now(timezone.utc)).isoformat()
        payload = {"reason": reason, "stream": stream, "data": data, "raw": raw}
        serialized = json.dumps(payload, separators=(",", ":"))
        self.rejected_handle.write(f"{captured} {serialized}\n")
        self.rejected_handle.flush()

    def close(self):
        if self.handle is None:
            if self.rejected_handle is not None:
                self.rejected_handle.close()
                self.rejected_handle = None
            return
        self.handle.close()
        if self.rejected_handle is not None:
            self.rejected_handle.close()
            self.rejected_handle = None
        digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        manifest = {
            "symbol": self.symbol,
            "kind": self.kind,
            "capture_id": self.capture_id,
            "path": str(self.path),
            "started": self.started,
            "ended": self.ended,
            "records": self.records,
            "bytes": self.path.stat().st_size,
            "sha256": digest,
        }
        with (DATA_DIR / "manifest.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(manifest, separators=(",", ":")) + "\n")
        self.handle = None
        self.segment = None


def exchange_info(symbol: str) -> dict:
    query = urllib.parse.urlencode({"symbol": symbol})
    last_error = None
    for base in EXCHANGE_INFO_BASES:
        request = urllib.request.Request(
            f"{base}?{query}",
            headers={"User-Agent": "market-simulator-depth-capture/1"},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                value = json.load(response)
            symbol_info = next(
                item for item in value["symbols"] if item["symbol"] == symbol
            )
            filters = {item["filterType"]: item for item in symbol_info["filters"]}
            return {
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "symbol": symbol,
                "status": symbol_info["status"],
                "contract_type": symbol_info["contractType"],
                "price_tick": filters["PRICE_FILTER"]["tickSize"],
                "quantity_step": filters["LOT_SIZE"]["stepSize"],
                "base_asset": symbol_info["baseAsset"],
                "quote_asset": symbol_info["quoteAsset"],
            }
        except (KeyError, StopIteration, urllib.error.HTTPError, urllib.error.URLError) as error:
            last_error = error
    raise RuntimeError(f"all Binance exchange-info endpoints failed: {last_error}")


def write_exchange_info(value: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / "instruments.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def snapshot(symbol: str) -> dict:
    query = urllib.parse.urlencode({"symbol": symbol, "limit": REST_LIMIT})
    last_error = None
    for base in REST_BASES:
        request = urllib.request.Request(
            f"{base}?{query}",
            headers={"User-Agent": "market-simulator-depth-capture/1"},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                value = json.load(response)
            value["E"] = int(time.time() * 1000)
            value["s"] = symbol
            return value
        except (urllib.error.HTTPError, urllib.error.URLError) as error:
            last_error = error
    raise RuntimeError(f"all Binance snapshot endpoints failed: {last_error}")


def window_segment(moment: datetime) -> int:
    return int(moment.timestamp()) // CAPTURE_INTERVAL_SECONDS


class DepthBridge:
    """Decide the fate of one depth update against the trailing update id.

    Decisions:

    - accept: the update continues the chain and advances the trailing id.
    - before: the update predates the current snapshot and is superseded.
    - gap: the chain has a hole, so book state is no longer trustworthy.
    """

    def __init__(self):
        self.current = None
        self.bootstrapped = False

    def reset(self, last_update_id: int):
        self.current = int(last_update_id)
        self.bootstrapped = False

    def apply(self, first_id: int, final_id: int, previous_id: int) -> str:
        if self.current is None:
            return "gap"
        if final_id <= self.current:
            return "before"
        if not self.bootstrapped:
            # Mirror collector/normalize_capture.py: an update bridges the
            # snapshot either by continuing the chain or by spanning its id.
            if previous_id != self.current and not (
                first_id <= self.current + 1 <= final_id
            ):
                return "gap"
            self.bootstrapped = True
        elif previous_id != self.current:
            return "gap"
        self.current = final_id
        return "accept"


async def capture_symbol(symbol: str, stop: asyncio.Event):
    depth_stream = f"{symbol.lower()}@depth@{DEPTH_SPEED}"
    trade_stream = f"{symbol.lower()}@trade"
    streams = [depth_stream] + ([trade_stream] if CAPTURE_TRADES else [])
    url = f"{STREAM_BASE}?streams={'/'.join(streams)}"
    depth_writer = CaptureWriter(symbol, "depth")
    trade_writer = CaptureWriter(symbol, "trades")
    bridge = DepthBridge()
    instrument_written = False
    backoff = 1
    pending = None
    try:
        while not stop.is_set():
            try:
                async with websockets.connect(url, ping_interval=20, ping_timeout=20, close_timeout=5, max_size=None) as socket:
                    backoff = 1
                    if not instrument_written:
                        write_exchange_info(await asyncio.to_thread(exchange_info, symbol))
                        instrument_written = True
                    while not stop.is_set():
                        # One epoch: a fresh snapshot, then the update stream until
                        # the window turns over, so every window file starts with
                        # a snapshot and can be replayed on its own.
                        snapshot_task = asyncio.create_task(asyncio.to_thread(snapshot, symbol))
                        buffered = []
                        if pending is not None:
                            buffered.append(pending)
                            pending = None
                        while not snapshot_task.done() and not stop.is_set():
                            message = json.loads(await asyncio.wait_for(socket.recv(), timeout=60))
                            buffered.append((datetime.now(timezone.utc), message))
                        book = await snapshot_task
                        bridge.reset(int(book["lastUpdateId"]))
                        snapshot_segment = window_segment(datetime.now(timezone.utc))

                        def accept(captured_at, message):
                            data = message.get("data", message)
                            if data.get("e") in {"aggTrade", "trade"}:
                                try:
                                    price = float(data.get("p"))
                                    quantity = float(data.get("q"))
                                except (TypeError, ValueError):
                                    price = quantity = float("nan")
                                if (
                                    not math.isfinite(price)
                                    or price <= 0
                                    or not math.isfinite(quantity)
                                    or quantity <= 0
                                ):
                                    trade_writer.write_rejected(
                                        "invalid_trade", trade_stream, data, message, captured_at
                                    )
                                    return
                                trade_writer.write(trade_stream, data, message, captured_at)
                                return
                            first_id = int(data["U"])
                            final_id = int(data["u"])
                            previous_id = int(data["pu"])
                            decision = bridge.apply(first_id, final_id, previous_id)
                            if decision == "before":
                                depth_writer.write_rejected(
                                    "before_snapshot", depth_stream, data, message, captured_at
                                )
                                return
                            if decision == "gap":
                                depth_writer.write_rejected(
                                    "snapshot_gap" if not bridge.bootstrapped else "update_gap",
                                    depth_stream,
                                    data,
                                    message,
                                    captured_at,
                                )
                                raise RuntimeError(
                                    f"depth chain gap: expected {bridge.current + 1}, got {first_id}"
                                )
                            depth_writer.write(depth_stream, data, message, captured_at)

                        for captured_at, message in buffered:
                            accept(captured_at, message)
                        depth_writer.write(f"{symbol.lower()}@depthSnapshot", book, book)
                        while not stop.is_set():
                            message = json.loads(await asyncio.wait_for(socket.recv(), timeout=60))
                            captured_at = datetime.now(timezone.utc)
                            if window_segment(datetime.now(timezone.utc)) != snapshot_segment:
                                pending = (captured_at, message)
                                break
                            accept(captured_at, message)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                print(f"{symbol}: connection error: {error}", flush=True)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)
    finally:
        depth_writer.close()
        trade_writer.close()


async def main():
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signum, stop.set)
    await asyncio.gather(*(capture_symbol(symbol, stop) for symbol in SYMBOLS))


if __name__ == "__main__":
    asyncio.run(main())
