#!/usr/bin/env python3
"""Split a canonical Hyperliquid fixture into one-symbol engine inputs.

`fixture_report` accepts depth and trades as separate files. This deterministic
adapter preserves their upstream canonical order, creates a combined identity
file, and records the combined hash in the manifest. The OCaml replay merges
the separate streams by receive time. It does not synthesize depth deltas, mark
liquidation events, or claim FIFO.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any


HEX64 = re.compile(r"^[0-9a-f]{64}$")
RFC3339_NS = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{9}Z$")
KINDS = {"depth_snapshot", "depth_update", "trade"}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_event(event: Any, line_number: int, expected_source_hash: str | None) -> str:
    if not isinstance(event, dict):
        raise ValueError(f"line {line_number}: event must be a JSON object")
    kind = event.get("kind")
    if kind not in KINDS:
        raise ValueError(f"line {line_number}: unsupported event kind {kind!r}")
    for field in ("venue", "symbol", "source_id", "source_path", "source_sha256", "quality"):
        if not isinstance(event.get(field), str) or not event[field]:
            raise ValueError(f"line {line_number}: missing/non-string {field}")
    if event["venue"].lower() != "hyperliquid":
        raise ValueError(f"line {line_number}: expected Hyperliquid venue")
    for field in ("event_time", "receive_time"):
        value = event.get(field)
        if not isinstance(value, str) or not RFC3339_NS.fullmatch(value):
            raise ValueError(f"line {line_number}: {field} must be RFC3339 UTC with 9 fractional digits")
    digest = event["source_sha256"].lower()
    if not HEX64.fullmatch(digest):
        raise ValueError(f"line {line_number}: malformed source_sha256")
    if expected_source_hash is not None and digest != expected_source_hash:
        raise ValueError(f"line {line_number}: source_sha256 changed within fixture")
    if kind in {"depth_snapshot", "depth_update"}:
        for side in ("bids", "asks"):
            levels = event.get(side)
            if not isinstance(levels, list) or any(
                not isinstance(level, list)
                or len(level) != 2
                or any(isinstance(x, bool) or not isinstance(x, int) for x in level)
                for level in levels
            ):
                raise ValueError(f"line {line_number}: {side} must contain integer [price, quantity] pairs")
    if kind == "trade":
        for field in ("price_ticks", "quantity_units"):
            value = event.get(field)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"line {line_number}: {field} must be an integer")
        if not isinstance(event.get("buyer_is_maker"), bool):
            raise ValueError(f"line {line_number}: buyer_is_maker must be boolean")
    return digest


def split_fixture(source: Path, out_dir: Path, symbol: str, *, created_at: str | None = None) -> dict[str, Any]:
    raw = source.read_bytes()
    source_hash = sha256(raw)
    selected: list[tuple[int, dict[str, Any]]] = []
    expected_source_hash: str | None = None
    for line_number, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {line_number}: invalid JSON") from exc
        if not isinstance(event, dict):
            raise ValueError(f"line {line_number}: event must be a JSON object")
        if event.get("symbol") != symbol or event.get("kind") not in KINDS:
            continue
        current_hash = _validate_event(event, line_number, expected_source_hash)
        expected_source_hash = current_hash
        selected.append((line_number, event))
    if not selected:
        raise ValueError(f"no supported Hyperliquid events found for {symbol}")

    # Preserve upstream canonical ordering (five-minute receive buckets with
    # snapshots first); the OCaml report merges the split streams by receive
    # time. No synthetic sequence is introduced.
    depth_rows = [event for _, event in selected if event["kind"].startswith("depth_")]
    trade_rows = [event for _, event in selected if event["kind"] == "trade"]
    if not depth_rows or not trade_rows:
        raise ValueError("selected symbol must contain both depth and trade events")

    out_dir.mkdir(parents=True, exist_ok=False)
    paths = {name: out_dir / f"{name}.jsonl" for name in ("combined", "depth", "trades")}
    payloads = {
        "combined": b"".join((json.dumps(event, separators=(",", ":"), ensure_ascii=False) + "\n").encode() for _, event in selected),
        "depth": b"".join((json.dumps(event, separators=(",", ":"), ensure_ascii=False) + "\n").encode() for event in depth_rows),
        "trades": b"".join((json.dumps(event, separators=(",", ":"), ensure_ascii=False) + "\n").encode() for event in trade_rows),
    }
    for name, path in paths.items():
        with path.open("xb") as stream:
            stream.write(payloads[name])

    def timestamp_range(field: str) -> list[str]:
        values = [event[field] for _, event in selected]
        return [min(values), max(values)]

    selected_source_hash = expected_source_hash
    assert selected_source_hash is not None
    created = created_at or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    if not created.endswith("Z"):
        raise ValueError("created_at must be UTC with Z suffix")
    manifest: dict[str, Any] = {
        "fixture": f"hyperliquid-{symbol.lower()}-ws-depth-trades",
        "fixture_sha256": sha256(payloads["combined"]),
        "format": "canonical",
        "venue": "hyperliquid",
        "symbol": symbol,
        "kind": "depth snapshots/updates and trades",
        "row_count": len(selected),
        "depth_rows": len(depth_rows),
        "trade_rows": len(trade_rows),
        "event_time_range": timestamp_range("event_time"),
        "receive_time_range": timestamp_range("receive_time"),
        "source": str(source),
        "source_file_sha256": source_hash,
        "source_sha256": selected_source_hash,
        "source_hashes": [selected_source_hash],
        "created_at": created,
        "query_version": "quanthacks-hyperliquid-engine-split-v1",
        "quality": "healthy",
        "component_sha256": {name: sha256(payload) for name, payload in payloads.items()},
        "conventions": {
            "units": "input is canonical integer units; no scaling is performed",
            "ordering": "preserve upstream canonical order; replay merges depth and trade by receive_time",
            "book": "source depth rows are retained as received; no deltas or sequence are synthesized",
            "limitations": ["no order-level IDs/FIFO", "trade prints do not identify liquidation status"],
        },
    }
    manifest_path = out_dir / "manifest.json"
    with manifest_path.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path, help="canonical JSONL from build_hyperliquid_fixture.py")
    parser.add_argument("--symbol", required=True, help="exact Hyperliquid coin, e.g. BTC")
    parser.add_argument("--out-dir", required=True, type=Path, help="new directory; existing directories are refused")
    parser.add_argument("--created-at", help="optional fixed UTC timestamp for reproducible manifests")
    args = parser.parse_args()
    manifest = split_fixture(args.fixture, args.out_dir, args.symbol, created_at=args.created_at)
    print(json.dumps({key: manifest[key] for key in ("symbol", "row_count", "depth_rows", "trade_rows", "fixture_sha256", "component_sha256")}, sort_keys=True))


if __name__ == "__main__":
    main()
