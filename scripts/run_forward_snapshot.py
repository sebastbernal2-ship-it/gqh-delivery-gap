#!/usr/bin/env python3
"""Record frozen forward-window predictions before any outcome exists.

Each run refreshes the complex filings, refits the frozen recipes on data available at the run time,
and appends one snapshot: the events seen, their predicted distributions, their sleeve weights and
the resulting positions, together with a hash manifest of the inputs and the fitted parameters. A
snapshot is never overwritten.

    python3 scripts/run_forward_snapshot.py --refresh
"""
from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.model import fit_and_forecast  # noqa: E402
from filing_specialist.rpo_model import FEATURES, prepare_rows  # noqa: E402

SNAPSHOTS = ROOT / "results" / "forward" / "snapshots"
FORWARD = ROOT / "results" / "forward"
PANELS = {"revenue": ROOT / "results" / "revenue-vintages-pit.csv",
          "capex": ROOT / "results" / "capex-vintages-pit.csv"}
DIRECTIONS = {"revenue": 1.0, "capex": -1.0}
UNIVERSE = ROOT / "results" / "rpo-universe-vintages.csv"
COMPLEX = ROOT / "results" / "market-panel.json"


def new_snapshot_path(directory: Path, stamp: str) -> Path:
    """The append-only guard: a snapshot filename is used once, ever."""
    path = directory / f"{stamp}.json"
    if path.exists():
        raise FileExistsError(f"{path} exists; snapshots are append only")
    return path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def complex_tickers() -> dict[str, str]:
    """Ticker to CIK for the complex register, from the SEC ticker file, cached locally."""
    import urllib.request

    wanted = set()
    panel = json.loads(COMPLEX.read_text())
    for group, payload in panel.get("groups", {}).items():
        for series in payload.get("series", []):
            ticker = series["ticker"]
            if ticker and ticker.isalpha():           # funds, futures and indices have no CIK
                wanted.add(ticker.upper())
    cache = ROOT / "results" / "sec-complex" / "company_tickers.json"
    if cache.exists():
        mapping = json.loads(cache.read_text())
    else:
        request = urllib.request.Request("https://www.sec.gov/files/company_tickers.json",
                                         headers={"User-Agent": "VECTOR research gqh-delivery-gap",
                                                  "Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=60) as response:
            mapping = json.loads(response.read())
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(mapping))
    pairs = {}
    for row in mapping.values():
        ticker = str(row.get("ticker", "")).upper()
        if ticker in wanted:
            pairs.setdefault(ticker, str(row.get("cik_str", "")).zfill(10))
    return pairs


def refresh_panels(stamp: str) -> dict[str, Path]:
    """Fetch fresh filings for the complex register and build dated panels for this snapshot."""
    import time
    import urllib.request
    from fetch_universe_fundamentals import CONCEPTS, FIELDS, quarterly_earliest

    raw = FORWARD / "raw" / stamp
    raw.mkdir(parents=True, exist_ok=True)
    pairs = complex_tickers()
    rows_by_concept: dict[str, list[dict]] = {name: [] for name in CONCEPTS}
    agent = {"User-Agent": "VECTOR research gqh-delivery-gap contact: sebastian@example.com",
             "Accept": "application/json"}
    for ticker, cik in sorted(pairs.items()):
        for name, concept in CONCEPTS.items():
            url = f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/{concept}.json"
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=agent), timeout=60) as response:
                    payload = json.loads(response.read())
            except Exception:
                continue
            (raw / f"{ticker}_{concept}.json").write_text(json.dumps(payload))
            rows_by_concept[name].extend(quarterly_earliest(payload, ticker, concept))
            time.sleep(0.12)
    outputs = {}
    for name, rows in rows_by_concept.items():
        path = FORWARD / f"{stamp}-{name}-quarterly.csv"
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        outputs[name] = path
    return outputs


PREFERRED = {"revenue": "RevenueFromContractWithCustomerExcludingAssessedTax",
             "capex": "PaymentsToAcquirePropertyPlantAndEquipment"}


def predictions(panel: Path, direction: float, as_of: str, split: float = 0.7,
                sleeve: str = "") -> dict:
    """The frozen recipe applied to rows available at `as_of`, with parameters recorded."""
    from build_driver_vintages import build_input_rows
    from filing_specialist.vintages import build_vintages

    raw = list(csv.DictReader(panel.open()))
    if raw and "relative_surprise_pit" in raw[0]:
        rows, _ = prepare_rows(raw)                        # already vintages
    else:
        prepared_input, _ = build_input_rows(raw, PREFERRED.get(sleeve, ""), {})
        vintage_rows, _ = build_vintages(prepared_input)
        rows, _ = prepare_rows(vintage_rows)
    rows = [row for row in rows if str(row["label_available"])[:10] <= as_of]
    if len(rows) < 50:
        return {"events": [], "parameter_digest": None, "rows": len(rows)}
    fitted = fit_and_forecast(rows, tuple(FEATURES), fraction=split)
    digest = hashlib.sha256(json.dumps(fitted["coefficients"]).encode()).hexdigest()
    events = []
    for row, values in zip(rows, fitted["train_probabilities"]):
        if str(row["label_available"])[:10] != as_of:
            continue
        expected = sum(k * float(p) for k, p in zip(fitted["classes"], values))
        conviction = direction * (expected - 2.0) / 2.0
        events.append({"ticker": str(row["ticker"]), "period_end": str(row["period_end"]),
                       "availability": str(row["label_available"]),
                       "expected_bin": round(expected, 4),
                       "weight": round(conviction, 4),
                       "distribution": [round(float(p), 6) for p in values]})
    return {"events": events, "parameter_digest": digest, "rows": len(rows),
            "classes": list(fitted["classes"])}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", default=datetime.date.today().isoformat())
    parser.add_argument("--refresh", action="store_true",
                        help="refetch the complex filings before recording (not yet wired)")
    args = parser.parse_args()
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    try:
        path = new_snapshot_path(SNAPSHOTS, stamp)
    except FileExistsError as error:
        raise SystemExit(str(error))

    panels = dict(PANELS)
    if args.refresh:
        panels = refresh_panels(stamp)
    report = {"schema": "forward-window-snapshot-v1", "run_utc": stamp, "as_of": args.as_of,
              "protocol": "docs/plan/forward-window.md", "refresh": bool(args.refresh),
              "manifest": {str(panel.relative_to(ROOT)): sha256(panel) for panel in panels.values()},
              "sleeves": {}, "positions": {},
              "note": "predictions recorded before any window outcome exists"}
    for name, panel in panels.items():
        block = predictions(panel, DIRECTIONS[name], args.as_of, sleeve=name)
        report["sleeves"][name] = block
        for event in block["events"]:
            report["positions"][f"{name}:{event['ticker']}:{event['period_end']}"] = event["weight"]
    path.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"snapshot": str(path), "as_of": args.as_of,
                      "events": {name: len(block["events"]) for name, block in report["sleeves"].items()},
                      "parameter_digests": {name: block["parameter_digest"]
                                            for name, block in report["sleeves"].items()}}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
