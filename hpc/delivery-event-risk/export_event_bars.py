#!/usr/bin/env python3
"""Export one explicitly selected TigerData bar batch for event-risk analysis."""
from __future__ import annotations

import argparse
import json
import os
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
KDB_SCRIPTS = ROOT / "hpc" / "kdb-timeseries" / "scripts"
sys.path.insert(0, str(KDB_SCRIPTS))

from export_tiger_bars import normalize_record, parse_batch, read_env_file, write_export


def normalize_for_event_risk(record: dict[str, Any]) -> dict[str, Any]:
    """Reuse source validation while preserving Massive's decimal adjusted volume."""
    raw_payload = record["payload_json"]
    payload = json.loads(raw_payload, parse_float=Decimal) if isinstance(raw_payload, str) else raw_payload
    if not isinstance(payload, dict):
        raise ValueError("bar payload must be a JSON object")
    try:
        volume = Decimal(str(payload.get("volume")))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("invalid source volume") from exc
    if not volume.is_finite() or not 0 <= volume < 2**63:
        raise ValueError("volume must be a nonnegative signed 64-bit quantity")

    # The shared KDB exporter stores volume as an integer q long. This event study
    # does not use volume; pass a valid placeholder through its other source checks,
    # then replace it with the exact decimal source value in the event TSV.
    validated_payload = dict(payload)
    validated_payload["volume"] = int(volume) if volume == volume.to_integral_value() else 0
    validated = normalize_record({**record, "payload_json": validated_payload})
    validated["volume"] = volume
    return validated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", action="append", type=parse_batch, required=True,
                        help="explicit source_id=64-character-sha256; repeat for distinct batches")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    args = parser.parse_args()
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
    manifests: dict[tuple[str, str], dict[str, Any]] = {}
    try:
        with psycopg.connect(url, password=password, connect_timeout=20) as conn:
            for index, (source_id, batch_sha) in enumerate(args.batch):
                with conn.cursor() as manifest_cur:
                    manifest_cur.execute("""
                        SELECT row_count, source_url, source_license, retrieved_at, manifest_json
                        FROM public.gqh_ingestion_manifests
                        WHERE source_id = %s AND batch_sha256 = %s
                    """, (source_id, batch_sha))
                    manifest_row = manifest_cur.fetchone()
                if manifest_row is None:
                    raise ValueError(f"no ingestion manifest for selected {source_id} batch")
                expected_counts[(source_id, batch_sha)] = int(manifest_row[0])
                original = manifest_row[4]
                if isinstance(original, str):
                    original = json.loads(original)
                manifests[(source_id, batch_sha)] = {
                    "source_id": source_id, "batch_sha256": batch_sha,
                    "row_count": int(manifest_row[0]), "source_url": manifest_row[1],
                    "source_license": manifest_row[2],
                    "retrieved_at": manifest_row[3].isoformat() if manifest_row[3] else None,
                    "original_manifest": original,
                }
                with conn.cursor(name=f"event_risk_bars_{index}") as cur:
                    cur.execute("""
                        SELECT source_id, batch_sha256, row_index, payload_json::text, row_sha256
                        FROM public.gqh_source_records
                        WHERE source_id = %s AND batch_sha256 = %s
                        ORDER BY event_time_text, row_index
                    """, (source_id, batch_sha))
                    while batch := cur.fetchmany(2000):
                        records.extend(normalize_for_event_risk({
                            "source_id": row[0], "batch_sha256": row[1], "row_index": row[2],
                            "payload_json": row[3], "row_sha256": row[4],
                        }) for row in batch)
        for batch_key, expected in expected_counts.items():
            actual = sum((row["source_id"], row["batch_sha256"]) == batch_key for row in records)
            if actual != expected:
                raise ValueError("selected batch row count differs from its ingestion manifest")
        result = write_export(records, args.output, source_manifests=manifests)
        manifest_path = args.output.with_suffix(args.output.suffix + ".manifest.json")
        export_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        export_manifest["volume_unit"] = "source-reported shares; decimal values preserved"
        export_manifest["volume_used_by_event_risk"] = False
        manifest_path.write_text(json.dumps(export_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception as exc:
        print(f"export failed: {type(exc).__name__}: credentials/connection details suppressed", file=sys.stderr)
        return 1
    print(f"exported and verified {result['rows']} rows across {len(result['symbols'])} symbols")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
