#!/usr/bin/env python3
"""Read explicitly selected Massive daily-bar batches from TigerData into a checksummed TSV."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[3]
PRICE_SCALE = 100_000_000
SYMBOL_RE = re.compile(r"^[A-Z][A-Z0-9.]{0,14}$")
SHA_RE = re.compile(r"^[a-f0-9]{64}$")
FIELDS = (
    "date", "sym", "source_id", "batch_sha256", "row_index",
    "open_px_e8usd", "high_px_e8usd", "low_px_e8usd", "close_px_e8usd", "volume",
    "row_sha256",
)


def read_env_file(path: Path) -> None:
    """Load only Tiger connection variables; no shell evaluation and never print values."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if sep and key.strip() in {"TIGERDATA_URL", "TIGERDATA_PASSWORD"}:
            os.environ.setdefault(key.strip(), value.strip())


def to_micro(value: Any, field: str) -> int:
    try:
        scaled = Decimal(str(value)) * PRICE_SCALE
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"invalid {field}") from exc
    if not scaled.is_finite() or scaled != scaled.to_integral_value():
        raise ValueError(f"{field} cannot be represented exactly at 1e-8 USD scale")
    result = int(scaled)
    if not -(2**63) <= result < 2**63:
        raise ValueError(f"{field} outside signed 64-bit range")
    return result


def session_date(event_time: str | datetime) -> date:
    if isinstance(event_time, str):
        value = event_time.strip().replace("Z", "+00:00")
        try:
            event_time = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("bar timestamp is not ISO-8601") from exc
    if event_time.tzinfo is None:
        raise ValueError("bar timestamp must carry a timezone")
    return event_time.astimezone(timezone.utc).date()


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    payload = record["payload_json"]
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload, dict):
        raise ValueError("bar payload must be a JSON object")
    source_id = str(record["source_id"])
    if source_id not in {"massive_bars", "massive_bars_unadjusted"}:
        raise ValueError("only the two Massive daily-bar source IDs are supported")
    batch = str(record["batch_sha256"]).strip()
    row_sha = str(record["row_sha256"]).strip()
    if not SHA_RE.fullmatch(batch) or not SHA_RE.fullmatch(row_sha):
        raise ValueError("source batch/row hash is not lowercase SHA-256")
    ticker = str(payload.get("ticker", ""))
    if not SYMBOL_RE.fullmatch(ticker):
        raise ValueError("ticker is missing or malformed")
    dt = session_date(payload.get("bar_time_utc", ""))
    prices = {name: to_micro(payload.get(name), name) for name in ("open", "high", "low", "close")}
    if prices["high"] < max(prices.values()) or prices["low"] > min(prices.values()):
        raise ValueError("OHLC invariant failed")
    volume = payload.get("volume")
    if isinstance(volume, bool) or not isinstance(volume, (int, Decimal)):
        raise ValueError("volume must be an integer count of shares")
    if int(volume) != volume or not 0 <= int(volume) < 2**63:
        raise ValueError("volume must be a nonnegative signed 64-bit integer")
    index = int(record["row_index"])
    if index < 0:
        raise ValueError("row_index must be nonnegative")
    return {
        "date": dt.isoformat(), "sym": ticker, "source_id": source_id,
        "batch_sha256": batch, "row_index": index,
        "open_px_e8usd": prices["open"], "high_px_e8usd": prices["high"],
        "low_px_e8usd": prices["low"], "close_px_e8usd": prices["close"],
        "volume": int(volume), "row_sha256": row_sha,
    }


def parse_batch(spec: str) -> tuple[str, str]:
    source_id, sep, batch = spec.partition("=")
    if not sep or source_id not in {"massive_bars", "massive_bars_unadjusted"}:
        raise argparse.ArgumentTypeError("use source_id=64-character-sha256 for a Massive bars source")
    if not SHA_RE.fullmatch(batch):
        raise argparse.ArgumentTypeError("batch SHA-256 must be 64 lowercase hex characters")
    return source_id, batch


def write_export(rows: Iterable[dict[str, Any]], output: Path, *, force: bool = False,
                 source_manifests: dict[tuple[str, str], dict[str, Any]] | None = None) -> dict[str, Any]:
    if output.exists() and not force:
        raise FileExistsError(f"refusing to overwrite {output}; use --force only for a deliberate rebuild")
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(output.suffix + ".partial")
    digest = hashlib.sha256()
    n = 0
    dates: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    batches: set[tuple[str, str]] = set()
    symbols: set[str] = set()
    with tmp.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            # Different batches for the same series can be revisions/canaries. Never blend them.
            key = (row["date"], row["sym"], row["source_id"])
            if key in seen:
                raise ValueError(f"duplicate logical bar key {key}")
            seen.add(key)
            batches.add((row["source_id"], row["batch_sha256"]))
            symbols.add(row["sym"])
            values = [str(row[field]) for field in FIELDS]
            # q's native date text syntax uses YYYY.MM.DD.
            values[0] = values[0].replace("-", ".")
            line = "\t".join(values) + "\n"
            stream.write(line)
            digest.update(line.encode("utf-8"))
            n += 1
            dates.append(row["date"])
        stream.flush()
        os.fsync(stream.fileno())
    if not n:
        tmp.unlink(missing_ok=True)
        raise ValueError("query returned no selected bars")
    os.replace(tmp, output)
    manifest = {
        "format_version": 1, "dataset": "massive_daily_bars", "rows": n,
        "first_date": min(dates), "last_date": max(dates),
        "sha256_tsv_body": digest.hexdigest(), "price_scale": PRICE_SCALE,
        "price_unit": "1e-8 USD", "volume_unit": "shares",
        "symbols": sorted(symbols),
        "batches": [{"source_id": s, "batch_sha256": b} for s, b in sorted(batches)],
        "source_manifests": [source_manifests[k] for k in sorted(source_manifests or {})],
        "columns": list(FIELDS), "source": "TigerData public.gqh_source_records",
    }
    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    if manifest_path.exists() and not force:
        output.unlink(missing_ok=True)
        raise FileExistsError(f"refusing to overwrite {manifest_path}")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", action="append", type=parse_batch, required=True,
                        help="explicit source_id=sha256; repeat for distinct batches")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--force", action="store_true", help="replace an existing output after explicit review")
    args = parser.parse_args(argv)
    if len(set(args.batch)) != len(args.batch):
        parser.error("each source/batch selection may appear only once")
    read_env_file(args.env_file)
    url = os.getenv("TIGERDATA_URL")
    password = os.getenv("TIGERDATA_PASSWORD")
    if not url:
        parser.error("TIGERDATA_URL is required; credentials are never printed")
    try:
        import psycopg
    except ImportError:
        parser.error("install psycopg[binary] in the project environment")
    records: list[dict[str, Any]] = []
    expected_counts: dict[tuple[str, str], int] = {}
    source_manifests: dict[tuple[str, str], dict[str, Any]] = {}
    try:
        with psycopg.connect(url, password=password, connect_timeout=20) as conn:
            for source_id, batch_sha in args.batch:
                with conn.cursor() as manifest_cur:
                    manifest_cur.execute("""
                        SELECT row_count, source_url, source_license, retrieved_at, manifest_json
                        FROM public.gqh_ingestion_manifests
                        WHERE source_id = %s AND batch_sha256 = %s
                    """, (source_id, batch_sha))
                    expected_row = manifest_cur.fetchone()
                if expected_row is None:
                    raise ValueError(f"no ingestion manifest for selected {source_id} batch")
                expected_counts[(source_id, batch_sha)] = int(expected_row[0])
                original_manifest = expected_row[4]
                if isinstance(original_manifest, str):
                    original_manifest = json.loads(original_manifest)
                source_manifests[(source_id, batch_sha)] = {
                    "source_id": source_id, "batch_sha256": batch_sha,
                    "row_count": int(expected_row[0]), "source_url": expected_row[1],
                    "source_license": expected_row[2],
                    "retrieved_at": expected_row[3].isoformat() if expected_row[3] else None,
                    "original_manifest": original_manifest,
                }
                with conn.cursor(name=f"kdb_export_{source_id}") as cur:
                    cur.execute("""
                        SELECT source_id, batch_sha256, row_index, payload_json, row_sha256
                        FROM public.gqh_source_records
                        WHERE source_id = %s AND batch_sha256 = %s
                        ORDER BY event_time_text, row_index
                    """, (source_id, batch_sha))
                    while batch := cur.fetchmany(2000):
                        records.extend(normalize_record({
                            "source_id": r[0], "batch_sha256": r[1], "row_index": r[2],
                            "payload_json": r[3], "row_sha256": r[4],
                        }) for r in batch)
        for batch, expected in expected_counts.items():
            actual = sum(1 for row in records if (row["source_id"], row["batch_sha256"]) == batch)
            if actual != expected:
                raise ValueError(f"selected batch row count mismatch: expected {expected}, read {actual}")
        result = write_export(records, args.output, force=args.force, source_manifests=source_manifests)
    except Exception as exc:
        # Suppress driver exception strings, which can include connection details.
        print(f"export failed: {type(exc).__name__}: credentials/connection details suppressed", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
