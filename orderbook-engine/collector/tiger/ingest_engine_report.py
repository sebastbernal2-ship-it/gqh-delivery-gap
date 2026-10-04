#!/usr/bin/env python3
"""Idempotently publish scalar fixture_report telemetry to TigerData.

The full, immutable report belongs in Snowflake. This bridge writes only run
identity/provenance and scalar metrics; it never ingests market events/books.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


HEX64 = re.compile(r"^[0-9a-f]{64}$")
FORBIDDEN_VENUE_WORDS = ("binance",)


@dataclass(frozen=True)
class Metric:
    metric_time: datetime
    liquidity_mode: str
    output_kind: str
    metric_name: str
    metric_value: Decimal
    unit: str


@dataclass(frozen=True)
class PreparedReport:
    run_key: str
    fixture_sha256: str
    config_sha256: str
    simulator_build: str
    report_sha256: str
    report_uri: str
    source_hashes: list[str]
    venue: str
    symbol: str
    run_status: str
    generated_at: datetime
    event_count: int
    chain_gaps: int
    book_mismatch: bool
    metadata: dict[str, Any]
    metrics: list[Metric]


def _hash(value: Any, field: str) -> str:
    text = str(value or "").lower()
    if not HEX64.fullmatch(text):
        raise ValueError(f"{field} must be a 64-character lowercase SHA-256 hex digest")
    return text


def _timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be an RFC3339 timestamp")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an RFC3339 timestamp") from exc
    if result.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return result.astimezone(timezone.utc)


def _unit(name: str) -> str:
    leaf = name.rsplit(".", 1)[-1]
    if leaf.endswith("_units") or leaf in {"position", "filled_units", "taker_units", "maker_units"}:
        return "quantity_units_1e-6"
    if leaf in {"fees", "realized_pnl", "collateral", "reserved_margin", "equity", "naive_equity", "realistic_equity", "equity_gap"}:
        return "money_units_1e-8"
    if leaf.endswith("_ticks") or leaf in {"book_best_bid", "book_best_ask"}:
        return "price_ticks_1e-4"
    if leaf.endswith("_bps"):
        return "basis_points"
    if leaf in {"seconds", "total_seconds"}:
        return "seconds"
    if leaf == "events_per_second":
        return "events/second"
    if leaf.endswith("_bytes"):
        return "bytes"
    return "count"


def _number(value: Any, field: str) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    if not isinstance(value, (int, float, Decimal)):
        return None
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"{field} is not a finite number") from exc
    if not result.is_finite():
        raise ValueError(f"{field} is not a finite number")
    integer_digits = max(0, result.adjusted() + 1) if result else 0
    fractional_digits = max(0, -result.as_tuple().exponent)
    if integer_digits > 26 or fractional_digits > 12 or integer_digits + fractional_digits > 38:
        raise ValueError(f"{field} exceeds TigerData NUMERIC(38,12) precision")
    return result


def _flatten(
    value: Any,
    prefix: str,
    metric_time: datetime,
    output_kind: str,
    liquidity_mode: str = "",
) -> list[Metric]:
    out: list[Metric] = []
    if isinstance(value, dict):
        mode = str(value.get("mode", liquidity_mode))
        label = str(value.get("label", ""))
        for key, child in value.items():
            if key in {"mode", "label", "statement", "caveat", "book_checksum", "checksum", "rule_all", "rule_training", "rule_holdout"}:
                continue
            child_kind = output_kind
            if key in {"modes", "per_mode"}:
                child_kind = "liquidity_mode"
            elif key in {"training_attribution", "holdout_attribution", "attribution"}:
                child_kind = key
            child_mode = mode or label or liquidity_mode
            out.extend(_flatten(child, f"{prefix}.{key}".strip("."), metric_time, child_kind, child_mode))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            # Give unlabeled array items stable path names; common report arrays
            # carry a `mode` or `label` and are represented as dimensions instead.
            suffix = "" if isinstance(child, dict) and ("mode" in child or "label" in child) else f"[{index}]"
            out.extend(_flatten(child, f"{prefix}{suffix}", metric_time, output_kind, liquidity_mode))
    else:
        number = _number(value, prefix)
        if number is not None:
            if not prefix:
                raise ValueError("metric path cannot be empty")
            out.append(Metric(metric_time, liquidity_mode, output_kind, prefix, number, _unit(prefix)))
    return out


def prepare_report(
    report_bytes: bytes,
    *,
    simulator_build: str,
    venue: str,
    symbol: str,
    report_uri: str,
    execution_config_sha256: str | None = None,
    execution_config_json: str | dict[str, Any] | None = None,
) -> PreparedReport:
    """Validate the stable report contract and derive deterministic run identity."""
    if not simulator_build.strip():
        raise ValueError("simulator_build is required")
    if not venue.strip() or not symbol.strip():
        raise ValueError("venue and symbol must be explicit (not inferred from a fixture name)")
    if any(word in venue.lower() for word in FORBIDDEN_VENUE_WORDS):
        raise ValueError("Binance venue reports are not accepted by the Quanthacks Tiger writer")
    if not report_uri.startswith("snowflake://"):
        raise ValueError("report_uri must identify the immutable Snowflake report artifact")
    try:
        report = json.loads(report_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("report must be valid UTF-8 JSON") from exc
    if not isinstance(report, dict) or not isinstance(report.get("manifest"), dict):
        raise ValueError("report must contain a manifest object")
    manifest = report["manifest"]
    fixture_sha = _hash(manifest.get("fixture_sha256"), "manifest.fixture_sha256")
    if execution_config_sha256 is not None and execution_config_json is not None:
        raise ValueError("provide only one execution config override: hash or JSON")
    if execution_config_json is not None:
        if isinstance(execution_config_json, str):
            try:
                config_object = json.loads(execution_config_json)
            except json.JSONDecodeError as exc:
                raise ValueError("execution_config_json must contain valid JSON") from exc
        else:
            config_object = execution_config_json
        if not isinstance(config_object, dict):
            raise ValueError("execution_config_json must be a JSON object")
        try:
            canonical_config = json.dumps(
                config_object, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError("execution_config_json must be a finite JSON object") from exc
        config_sha = hashlib.sha256(canonical_config).hexdigest()
        config_hash_source = "explicit_execution_config_json"
    elif execution_config_sha256 is not None:
        config_sha = _hash(execution_config_sha256, "execution_config_sha256")
        config_hash_source = "explicit_execution_config_sha256"
    else:
        config_sha = _hash(manifest.get("config_sha256"), "manifest.config_sha256 or explicit execution config override")
        config_hash_source = "manifest.config_sha256"
    generated_at = _timestamp(manifest.get("created_at"), "manifest.created_at")
    raw_source_hashes = manifest.get("source_hashes")
    if not raw_source_hashes and manifest.get("source_sha256") is not None:
        raw_source_hashes = [manifest["source_sha256"]]
    if not isinstance(raw_source_hashes, list) or not raw_source_hashes:
        raise ValueError("manifest must contain source_hashes[] or one source_sha256 provenance hash")
    source_hashes = sorted({_hash(x, "manifest.source_hashes[]") for x in raw_source_hashes})
    report_sha = hashlib.sha256(report_bytes).hexdigest()
    run_key = hashlib.sha256(
        json.dumps(
            {"fixture_sha256": fixture_sha, "config_sha256": config_sha, "simulator_build": simulator_build},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    try:
        event_count = int(report["events"])
        chain_gaps = int(report["chain_gaps"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("report must contain integer events and chain_gaps") from exc
    if event_count < 0 or chain_gaps < 0:
        raise ValueError("event and gap counters must be nonnegative")
    if not isinstance(report.get("book_mismatch"), bool):
        raise ValueError("report.book_mismatch must be boolean")
    quality_bad = (
        event_count == 0
        or report["book_mismatch"]
        or chain_gaps > 0
        or int(report.get("parse_errors", 0)) > 0
        or int(report.get("chain_pending", 0)) > 0
    )
    metrics: list[Metric] = []
    for key, value in report.items():
        if key == "manifest":
            continue
        kind = "replay"
        if key == "modes":
            kind = "liquidity_mode"
        elif key == "features":
            kind = "feature"
        elif key == "throughput":
            kind = "throughput"
        elif key == "uncertainty":
            kind = "uncertainty"
        elif key == "regimes":
            kind = "regime"
        elif key == "assumption_gap":
            kind = "assumption_gap"
        metrics.extend(_flatten(value, key, generated_at, kind))
    # Ensure dimension-key uniqueness before database insertion.
    seen = set()
    for metric in metrics:
        key = (metric.metric_time, metric.liquidity_mode, metric.output_kind, metric.metric_name)
        if key in seen:
            raise ValueError(f"duplicate metric identity: {key}")
        seen.add(key)
    metadata = {
        "query_version": manifest.get("query_version"),
        "source": manifest.get("source"),
        "fixture_name": manifest.get("fixture"),
        "kind": manifest.get("kind"),
        "config_hash_source": config_hash_source,
        # `complete` means the replay passed structural validation; preserve a
        # source manifest's more specific caveat instead of upgrading a bounded
        # snapshot capture to an unqualified `healthy` status here.
        "quality": "rejected" if quality_bad else str(manifest.get("quality", "healthy")),
        "time_range": manifest.get("event_time_range"),
    }
    return PreparedReport(
        run_key=run_key,
        fixture_sha256=fixture_sha,
        config_sha256=config_sha,
        simulator_build=simulator_build,
        report_sha256=report_sha,
        report_uri=report_uri,
        source_hashes=source_hashes,
        venue=venue,
        symbol=symbol,
        run_status="rejected" if quality_bad else "complete",
        generated_at=generated_at,
        event_count=event_count,
        chain_gaps=chain_gaps,
        book_mismatch=report["book_mismatch"],
        metadata=metadata,
        metrics=metrics,
    )


def write_report(prepared: PreparedReport, *, database_url: str, password: str | None = None) -> int:
    """Persist one report and its metrics; exact reruns are no-ops, drift fails closed."""
    import psycopg
    from psycopg.types.json import Jsonb

    with psycopg.connect(database_url, password=password, connect_timeout=20) as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO public.engine_run_reports
                    (run_key,fixture_sha256,config_sha256,simulator_build,report_sha256,report_uri,
                     source_hashes,venue,symbol,run_status,generated_at,event_count,chain_gaps,
                     book_mismatch,metadata)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (run_key) DO NOTHING""",
                    (prepared.run_key, prepared.fixture_sha256, prepared.config_sha256,
                     prepared.simulator_build, prepared.report_sha256, prepared.report_uri,
                     Jsonb(prepared.source_hashes), prepared.venue, prepared.symbol,
                     prepared.run_status, prepared.generated_at, prepared.event_count,
                     prepared.chain_gaps, prepared.book_mismatch, Jsonb(prepared.metadata)),
                )
                cursor.execute(
                    """SELECT fixture_sha256,config_sha256,simulator_build,report_sha256,
                              report_uri,venue,symbol,run_status,generated_at,event_count,
                              chain_gaps,book_mismatch
                       FROM public.engine_run_reports WHERE run_key=%s""",
                    (prepared.run_key,),
                )
                existing = cursor.fetchone()
                expected = (prepared.fixture_sha256, prepared.config_sha256, prepared.simulator_build,
                            prepared.report_sha256, prepared.report_uri, prepared.venue, prepared.symbol,
                            prepared.run_status, prepared.generated_at, prepared.event_count,
                            prepared.chain_gaps, prepared.book_mismatch)
                if existing != expected:
                    raise ValueError("run_key already exists with different report bytes or metadata; refusing overwrite")
                cursor.executemany(
                    """INSERT INTO public.engine_metric_points
                    (metric_time,emitted_at,run_key,venue,symbol,liquidity_mode,output_kind,
                     metric_name,metric_value,unit,source_report_sha256)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT DO NOTHING""",
                    [(m.metric_time, datetime.now(timezone.utc), prepared.run_key, prepared.venue,
                      prepared.symbol, m.liquidity_mode, m.output_kind, m.metric_name,
                      m.metric_value, m.unit, prepared.report_sha256) for m in prepared.metrics],
                )
                cursor.execute("SELECT count(*) FROM public.engine_metric_points WHERE run_key=%s", (prepared.run_key,))
                stored = cursor.fetchone()[0]
                if stored != len(prepared.metrics):
                    raise ValueError(f"metric row reconciliation failed: stored {stored}, expected {len(prepared.metrics)}")
    return len(prepared.metrics)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="fixture_report JSON file")
    parser.add_argument("--simulator-build", required=True, help="immutable engine build ID or git commit")
    parser.add_argument("--venue", required=True, help="explicit venue; Binance is rejected")
    parser.add_argument("--symbol", required=True, help="explicit instrument symbol")
    parser.add_argument("--report-uri", required=True, help="immutable Snowflake report URI/identifier")
    config_group = parser.add_mutually_exclusive_group()
    config_group.add_argument(
        "--execution-config-sha256",
        help="SHA-256 of the simulator execution config (not capture/preprocessing config)",
    )
    config_group.add_argument(
        "--execution-config-json",
        type=Path,
        help="path to simulator execution-config JSON; canonicalized and SHA-256 hashed",
    )
    parser.add_argument("--dry-run", action="store_true", help="validate and report row counts without connecting")
    args = parser.parse_args(argv)

    raw = args.report.read_bytes()
    execution_config_json = args.execution_config_json.read_text(encoding="utf-8") if args.execution_config_json else None
    prepared = prepare_report(raw, simulator_build=args.simulator_build, venue=args.venue,
                              symbol=args.symbol, report_uri=args.report_uri,
                              execution_config_sha256=args.execution_config_sha256,
                              execution_config_json=execution_config_json)
    if args.dry_run:
        print(json.dumps({"run_key": prepared.run_key, "report_sha256": prepared.report_sha256,
                          "status": prepared.run_status, "metrics": len(prepared.metrics),
                          "market_rows_written": 0}, sort_keys=True))
        return 0
    repo_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(repo_root / "src" / "central_ingest"))
    import sync  # loads only the selected gitignored variables, without logging them
    sync.load_local_env()
    database_url = os.environ.get("TIGERDATA_URL")
    if not database_url:
        parser.error("TIGERDATA_URL is not configured")
    inserted = write_report(prepared, database_url=database_url, password=os.getenv("TIGERDATA_PASSWORD"))
    print(json.dumps({"run_key": prepared.run_key, "report_sha256": prepared.report_sha256,
                      "status": prepared.run_status, "metric_rows": inserted,
                      "market_rows_written": 0}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
