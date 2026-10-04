#!/usr/bin/env python3
"""Score recorded forward snapshots, refusing any event whose outcome cannot exist yet.

The evaluation is mechanical: it reads only snapshots, attaches realised returns where the exit
session is already in the price cache, and reports the metrics with the count of scored and refused
events. It never refits and never backfills.

    python3 scripts/evaluate_forward_window.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.market_state import load_series  # noqa: E402

SNAPSHOTS = ROOT / "results" / "forward" / "snapshots"
HORIZON = 20


def realized(series: dict[str, float], decision: str, horizon: int = HORIZON):
    """Return and exit session, or None when the outcome cannot exist yet."""
    days = sorted(series)
    after = [day for day in days if day > decision[:10]]
    if len(after) < horizon + 1:
        return None
    return series[after[horizon]] / series[after[0]] - 1.0, after[horizon]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / "results" / "bar-cache")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results" / "forward" / "evaluation.json")
    args = parser.parse_args()

    scored, refused, missing = [], 0, 0
    series_cache: dict[str, dict[str, float]] = {}
    snapshots = sorted(SNAPSHOTS.glob("*.json")) if SNAPSHOTS.exists() else []
    for path in snapshots:
        snapshot = json.loads(path.read_text())
        for name, block in snapshot.get("sleeves", {}).items():
            direction = 1.0 if name == "revenue" else -1.0
            for event in block.get("events", []):
                ticker = event["ticker"]
                if ticker not in series_cache:
                    series_cache[ticker] = load_series(ticker, args.cache)
                outcome = realized(series_cache[ticker], event["availability"])
                if outcome is None:
                    refused += 1
                    continue
                value, exit_session = outcome
                scored.append({"snapshot": path.name, "sleeve": name, "ticker": ticker,
                               "decision": event["availability"], "exit": exit_session,
                               "weight": event["weight"], "return": value,
                               "contribution": direction * event["weight"] * value})
    report = {"schema": "forward-window-evaluation-v1", "snapshots": len(snapshots),
              "scored_events": len(scored), "refused_immature": refused, "missing_series": missing,
              "events": scored}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({key: report[key] for key in
                      ("snapshots", "scored_events", "refused_immature")}, indent=1))
    if scored:
        contributions = [row["contribution"] for row in scored]
        print(f"mean contribution per scored event: {sum(contributions)/len(contributions):+.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
