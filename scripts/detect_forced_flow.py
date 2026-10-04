#!/usr/bin/env python3
"""Infer forced flow candidates from a Hyperliquid websocket capture.

Protocol: docs/plan/forced-flow-inference.md. Development only. Reads the trades and the asset context from
the capture, groups aggressive prints into ten second bursts, and applies the declared rule. Writes
results/hyperliquid-forced-flow-candidates.jsonl and a summary.

    python3 scripts/detect_forced_flow.py data/hyperliquid/ws/ws-*.jsonl
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "hyperliquid-forced-flow-candidates.jsonl"
SUMMARY = ROOT / "results" / "hyperliquid-forced-flow-summary.json"
BURST_SECONDS = 10
MIN_NOTIONAL = {"BTC": 250_000.0, "ETH": 250_000.0, "GAS": 20_000.0, "SPX": 20_000.0}
SIZE_MULTIPLE = 5.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("captures", nargs="+")
    args = parser.parse_args()

    trades: dict[str, list[dict]] = collections.defaultdict(list)
    context: dict[str, list[dict]] = collections.defaultdict(list)
    for path in args.captures:
        for line in Path(path).open():
            if not line.strip():
                continue
            row = json.loads(line)
            channel, data, stamp = row.get("channel"), row.get("data"), row.get("recv_ts")
            if channel == "trades" and isinstance(data, list):
                for trade in data:
                    try:
                        trades[trade["coin"]].append({"ts": float(trade["time"]) / 1000.0,
                                                      "px": float(trade["px"]), "sz": float(trade["sz"]),
                                                      "side": str(trade.get("side", "")).upper(),
                                                      "users": trade.get("users") or [],
                                                      "tid": trade.get("tid")})
                    except (KeyError, TypeError, ValueError):
                        continue
            elif channel == "activeAssetCtx" and isinstance(data, dict):
                ctx = data.get("ctx") or {}
                try:
                    context[data.get("coin")].append({"ts": stamp, "oi": float(ctx.get("openInterest") or 0),
                                                      "mark": float(ctx.get("markPx") or 0)})
                except (TypeError, ValueError):
                    continue
    candidates = []
    summary: dict = {"captures": args.captures, "per_coin": {}}
    for coin, prints in sorted(trades.items()):
        prints.sort(key=lambda row: row["ts"])
        for row in context.get(coin, []):
            pass
        context[coin].sort(key=lambda row: row["ts"]) if context.get(coin) else None
        bursts = []
        current: list[dict] = []
        for trade in prints:
            if current and (trade["ts"] - current[-1]["ts"] > BURST_SECONDS or trade["side"] != current[-1]["side"]):
                bursts.append(current)
                current = []
            current.append(trade)
        if current:
            bursts.append(current)
        notionals = [sum(row["px"] * row["sz"] for row in burst) for burst in bursts]
        # trailing sigma of ten second mark returns over the previous thirty minutes, for the move screen
        marks = [(row["ts"], row["mark"]) for row in context.get(coin, []) if row["mark"]]
        sigma_bps = None
        if len(marks) > 30:
            returns = []
            for index in range(10, len(marks)):
                if marks[index][1] and marks[index - 10][1]:
                    returns.append(abs(marks[index][1] / marks[index - 10][1] - 1) * 1e4)
            if len(returns) > 20:
                sigma_bps = statistics.median(returns)
        repeats: set[str] = set()
        for burst in bursts:
            notional = sum(row["px"] * row["sz"] for row in burst)
            index = bursts.index(burst)
            trailing = notionals[max(0, index - 30):index]
            median = statistics.median(trailing) if trailing else 0.0
            threshold = max(SIZE_MULTIPLE * median, MIN_NOTIONAL.get(coin, 20_000.0)) if median else MIN_NOTIONAL.get(coin, 20_000.0)
            if notional < threshold or len(burst) < 3:
                continue
            move_bps_signed = (burst[-1]["px"] / burst[0]["px"] - 1) * 1e4 if burst[0]["px"] else 0.0
            if sigma_bps is not None and abs(move_bps_signed) < 2 * sigma_bps:
                continue
            taker_addresses = {row["users"][0] for row in burst if row["users"]}
            repeat = bool(taker_addresses & repeats)
            repeats |= taker_addresses
            first_px, last_px = burst[0]["px"], burst[-1]["px"]
            move_bps = move_bps_signed
            move_threshold_bps = round(2 * sigma_bps, 2) if sigma_bps is not None else None
            oi_change = None
            if context.get(coin):
                window = [row["oi"] for row in context[coin] if burst[0]["ts"] - 30 <= row["ts"] <= burst[-1]["ts"]]
                if len(window) > 1 and window[0]:
                    oi_change = (window[-1] / window[0] - 1) * 100
            candidates.append({"coin": coin, "start": burst[0]["ts"], "end": burst[-1]["ts"],
                               "side": burst[-1]["side"], "prints": len(burst),
                               "notional_usd": round(notional, 0),
                               "threshold_usd": round(threshold, 0),
                               "move_bps": round(move_bps, 2),
                               "move_threshold_bps": move_threshold_bps,
                               "open_interest_change_pct": round(oi_change, 3) if oi_change is not None else None,
                               "repeat_address": repeat,
                               "taker_addresses": sorted(taker_addresses)[:4],
                               "inference": "forced flow candidate, not a venue confirmed liquidation"})
        summary["per_coin"][coin] = {"prints": len(prints), "bursts": len(bursts),
                                     "candidates": sum(1 for row in candidates if row["coin"] == coin)}
    OUT.write_text("".join(json.dumps(row) + "\n" for row in candidates))
    summary["candidates"] = len(candidates)
    SUMMARY.write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    for row in candidates[:5]:
        print(json.dumps(row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
