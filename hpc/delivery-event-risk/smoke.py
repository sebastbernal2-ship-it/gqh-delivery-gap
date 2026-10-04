#!/usr/bin/env python3
"""Synthetic-only compiler, manifest, sealed-fence and output smoke check."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EVENT_FIELDS = [
    "event_id", "event_cluster_id", "ticker", "metric_key", "unit", "available_at_utc",
    "expectation_available_at_utc", "expectation_type", "prior_expectation", "current_value",
    "review_status", "exposure_status", "sector_symbol", "document_sha256", "in_sealed_window",
]
BAR_FIELDS = ["date", "sym", "source_id", "batch_sha256", "row_index", "open_px_e8usd",
              "high_px_e8usd", "low_px_e8usd", "close_px_e8usd", "volume", "row_sha256"]


def make_fixture(directory: Path) -> tuple[Path, Path, Path, Path]:
    events = directory / "events.csv"
    bars = directory / "bars.tsv"
    event_manifest = directory / "events.manifest.json"
    bar_manifest = directory / "bars.tsv.manifest.json"
    seal = dt.date(2022, 12, 1)
    batch = "b" * 64
    document_hash = "a" * 64
    event_rows = []
    dates = ["2020-01-15", "2020-03-15", "2020-05-15", "2020-07-15",
             "2020-09-15", "2021-09-15", "2022-04-15", "2022-11-15"]
    surprise_values = [3, 4, 2, 5, 1, 6, 4, 8]
    for i, day in enumerate(dates):
        stamp = day + "T20:00:00Z"
        event_rows.append({
            "event_id": f"evt-{i}", "event_cluster_id": f"cluster-{i}", "ticker": "ABC",
            "metric_key": "capacity_guidance", "unit": "MW", "available_at_utc": stamp,
            "expectation_available_at_utc": "2019-12-31T20:00:00Z",
            "expectation_type": "management_guidance", "prior_expectation": str(100 + i),
            "current_value": str(100 + i + surprise_values[i]), "review_status": "reviewed", "exposure_status": "verified",
            "sector_symbol": "XLI", "document_sha256": document_hash, "in_sealed_window": "false",
        })
    with events.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=EVENT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(event_rows)
    subprocess.run([
        "python3", str(ROOT / "make_event_manifest.py"), "--events", str(events),
        "--development-start", "2019-01-01", "--sealed-start", seal.isoformat(),
        "--out", str(event_manifest),
    ], check=True, capture_output=True, text=True)

    sessions = []
    day = dt.date(2019, 1, 1)
    while day < seal:
        if day.weekday() < 5:
            sessions.append(day)
        day += dt.timedelta(days=1)
    closes = {sym: 100.0 for sym in ("ABC", "SPY", "XLI")}
    body = []
    for index, session in enumerate(sessions):
        market_move = (0.001 if session < dt.date(2021, 6, 1) else 0.02) * math.sin(index * 0.71)
        for symbol, loading in (("SPY", 1.0), ("ABC", 1.4), ("XLI", 0.8)):
            closes[symbol] *= math.exp(market_move * loading + 0.0004 * math.cos(index * (0.19 + loading)))
            scaled = round(closes[symbol] * 100_000_000)
            prefix = (f"{session.isoformat()}\t{symbol}\tmassive_bars\t{batch}\t{index}\t"
                      f"{scaled}\t{scaled}\t{scaled}\t{scaled}\t100000\t")
            body.append(prefix + hashlib.sha256(prefix.encode()).hexdigest() + "\n")
    with bars.open("w", encoding="utf-8", newline="") as stream:
        stream.write("\t".join(BAR_FIELDS) + "\n")
        stream.writelines(body)
    bar_manifest.write_text(json.dumps({
        "format_version": 1, "dataset": "massive_daily_bars", "rows": len(body),
        "first_date": sessions[0].isoformat(), "last_date": sessions[-1].isoformat(),
        "sha256_tsv_body": hashlib.sha256("".join(body).encode()).hexdigest(),
        "price_scale": 100_000_000, "price_unit": "1e-8 USD", "volume_unit": "shares",
        "symbols": ["ABC", "SPY", "XLI"],
        "batches": [{"source_id": "massive_bars", "batch_sha256": batch}],
        "columns": BAR_FIELDS, "source_manifests": [],
    }, indent=2) + "\n", encoding="utf-8")
    return events, event_manifest, bars, bar_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default="g++")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="gqh-event-risk-smoke-") as tmp:
        folder = Path(tmp)
        executable = folder / "event_risk"
        subprocess.run([args.compiler, "-std=c++17", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-Werror",
                        str(ROOT / "event_risk.cpp"), "-o", str(executable)], check=True)
        events, event_manifest, bars, bar_manifest = make_fixture(folder)
        receipt = folder / "input-receipt.json"
        verify = subprocess.run([
            "python3", str(ROOT / "verify_inputs.py"), "--events", str(events), "--event-manifest", str(event_manifest),
            "--bars", str(bars), "--bars-manifest", str(bar_manifest), "--development-start", "2019-01-01",
            "--sealed-start", "2022-12-01", "--receipt", str(receipt),
        ], capture_output=True, text=True)
        if verify.returncode:
            raise RuntimeError(verify.stderr)
        output = folder / "outputs"
        run = subprocess.run([
            str(executable), "--events", str(events), "--bars", str(bars), "--development-start", "2019-01-01",
            "--sealed-start", "2022-12-01", "--output", str(output),
        ], capture_output=True, text=True)
        if run.returncode:
            raise RuntimeError(run.stderr)
        with (output / "event-outcomes.csv").open(newline="", encoding="utf-8") as stream:
            outcomes = list(csv.DictReader(stream))
        if len(outcomes) != 8:
            raise AssertionError(f"expected 8 events, got {len(outcomes)}")
        if not outcomes[-1]["spy_vol20_ann"] or outcomes[-1]["vol_regime"] not in {"high_vol", "normal_vol"}:
            raise AssertionError("late development event should have an as-of volatility state")
        if outcomes[-1]["stock_return_20"]:
            raise AssertionError("20-session outcome crossing the sealed cutoff must be blank")
        if not outcomes[5]["surprise_z"]:
            raise AssertionError("past-only robust surprise score did not warm up")
        if not (output / "regime-summary.csv").is_file() or not (output / "surprise-association.csv").is_file() or not (output / "report.md").is_file():
            raise AssertionError("expected summary outputs were not written")
        print("synthetic event-risk smoke passed; no market or sealed data used")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
