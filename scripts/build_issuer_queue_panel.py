#!/usr/bin/env python3
"""Build the issuer level queue panel: which listed entity stands behind which queued megawatts.

Queue names (utility, developer) are matched to SEC registrants through the SEC ticker file, exact and
then fuzzy, with the score kept so a human can audit every candidate. Each matched entity gets its queue
megawatts, its technology mix, and an at risk share using the measured withdrawal propensities from T18
(offshore wind 0.723, wind 0.683, other 0.664, solar plus battery 0.498, battery 0.450, hydro 0.445, and
the panel base rate as the fallback).

Writes results/issuer-queue-crosswalk.csv, results/issuer-queue-panel.csv and
results/issuer-queue-summary.json.

    python3 scripts/build_issuer_queue_panel.py
"""
from __future__ import annotations

import collections
import csv
import difflib
import json
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "results" / "queue-panel.csv"
TICKERS = ROOT / "results" / "sec-capex" / "company_tickers.json"
CROSSWALK_OUT = ROOT / "results" / "issuer-queue-crosswalk.csv"
PANEL_OUT = ROOT / "results" / "issuer-queue-panel.csv"
SUMMARY_OUT = ROOT / "results" / "issuer-queue-summary.json"
SNAPSHOT = "2024-12-31"

WITHDRAWAL = {"Offshore Wind": 0.723, "Wind": 0.683, "Other": 0.664,
              "Solar+Battery": 0.498, "Battery": 0.450, "Hydro": 0.445}
SUFFIXES = {"inc", "incorporated", "corp", "corporation", "co", "company", "llc", "l l c", "lp", "l p",
            "ltd", "limited", "plc", "holdings", "holding", "group", "the", "trust", "partners", "sa",
            "nv", "ag", "usa", "us", "energy", "power", "electric", "utilities", "utility", "resources",
            "services", "systems", "international", "north", "america", "american"}


def parse_mw(value) -> float:
    try:
        return max(0.0, float(value or 0))
    except (TypeError, ValueError):
        return 0.0


def normalise(name: str) -> str:
    text = str(name).lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    words = [word for word in text.split() if word and word not in SUFFIXES]
    return " ".join(words)


def main() -> int:
    tickers_payload = json.loads(TICKERS.read_text())
    registry = []
    for row in tickers_payload.values():
        title = row.get("title", "")
        if title:
            registry.append({"ticker": row["ticker"], "cik": str(row["cik_str"]).zfill(10),
                             "title": title, "norm": normalise(title)})
    norm_index = collections.defaultdict(list)
    for entry in registry:
        if entry["norm"]:
            norm_index[entry["norm"]].append(entry)
    print(f"SEC registry {len(registry)} registrants, {len(norm_index)} normalised names")

    rows = list(csv.DictReader(QUEUE.open()))
    base_share = sum(1 for row in rows if row["q_status"] == "withdrawn") / len(rows)

    def match(name: str) -> tuple[dict | None, float]:
        norm = normalise(name)
        if not norm or norm in {"na", "n a", "masked", "various", "unknown"}:
            return None, 0.0
        if norm in norm_index:
            return norm_index[norm][0], 1.0
        best, best_score = None, 0.0
        for candidate in norm_index:
            if abs(len(candidate) - len(norm)) > 12:
                continue
            if candidate[:4] != norm[:4]:
                continue
            score = difflib.SequenceMatcher(None, norm, candidate).ratio()
            if score > best_score:
                best, best_score = norm_index[candidate][0], score
        return (best, best_score) if best_score >= 0.90 else (None, best_score)

    by_name: dict[str, dict] = collections.defaultdict(lambda: {"mw": 0.0, "projects": 0, "withdrawn_mw": 0.0})
    for row in rows:
        try:
            mw = max(0.0, float(row["mw1"] or 0))
        except ValueError:
            mw = 0.0
        for column in ("utility", "developer"):
            name = (row.get(column) or "").strip()
            if not name or name.upper() in {"NA", "N/A", "MASKED"}:
                continue
            entry = by_name[f"{column}:{name}"]
            entry["mw"] += mw
            entry["projects"] += 1
            if row["q_status"] == "withdrawn":
                entry["withdrawn_mw"] += mw

    crosswalk_rows = []
    panel: dict[str, dict] = collections.defaultdict(lambda: {"mw": 0.0, "at_risk_mw": 0.0, "projects": 0,
                                                              "withdrawn_mw": 0.0, "names": set(),
                                                              "technologies": collections.Counter()})
    matched_mw = 0.0
    for key, entry in sorted(by_name.items()):
        column, name = key.split(":", 1)
        if entry["mw"] < 1.0:
            continue
        registrant, score = match(name)
        crosswalk_rows.append({"queue_name": name, "column": column, "mw": round(entry["mw"], 1),
                               "projects": entry["projects"], "ticker": registrant["ticker"] if registrant else "",
                               "cik": registrant["cik"] if registrant else "",
                               "sec_title": registrant["title"] if registrant else "",
                               "match_score": round(score, 3),
                               "status": "matched" if registrant else "unmatched"})
        if not registrant:
            continue
        matched_mw += entry["mw"]
        target = panel[registrant["ticker"]]
        target["mw"] += entry["mw"]
        target["projects"] += entry["projects"]
        target["withdrawn_mw"] += entry["withdrawn_mw"]
        target["names"].add(name)
    # technology mix and at risk MW per ticker, from the project rows directly
    for row in rows:
        try:
            mw = max(0.0, float(row["mw1"] or 0))
        except ValueError:
            continue
        for column in ("utility", "developer"):
            name = (row.get(column) or "").strip()
            if not name or name.upper() in {"NA", "N/A", "MASKED"}:
                continue
            registrant, score = match(name)
            if not registrant:
                continue
            target = panel[registrant["ticker"]]
            technology = row.get("type_clean", "Other")
            share = WITHDRAWAL.get(technology, base_share)
            target["at_risk_mw"] += mw * share
            target["technologies"][technology] += mw

    panel_rows = []
    for ticker, entry in sorted(panel.items(), key=lambda item: -item[1]["mw"]):
        panel_rows.append({"ticker": ticker, "queue_mw": round(entry["mw"], 1),
                           "at_risk_mw": round(entry["at_risk_mw"], 1),
                           "at_risk_share": round(entry["at_risk_mw"] / entry["mw"], 3) if entry["mw"] else None,
                           "withdrawn_mw": round(entry["withdrawn_mw"], 1),
                           "projects": entry["projects"], "names": " | ".join(sorted(entry["names"])[:4]),
                           "top_technology": entry["technologies"].most_common(1)[0][0] if entry["technologies"] else ""})
    with CROSSWALK_OUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["queue_name", "column", "mw", "projects", "ticker", "cik",
                                                    "sec_title", "match_score", "status"])
        writer.writeheader()
        writer.writerows(crosswalk_rows)
    with PANEL_OUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["ticker", "queue_mw", "at_risk_mw", "at_risk_share",
                                                    "withdrawn_mw", "projects", "names", "top_technology"])
        writer.writeheader()
        writer.writerows(panel_rows)
    summary = {
        "queue_rows": len(rows),
        "named_rows": sum(1 for row in rows if (row.get("utility") or "").strip().upper() not in {"", "NA", "N/A"}),
        "names_seen": len(by_name),
        "matched_names": sum(1 for row in crosswalk_rows if row["status"] == "matched"),
        "unmatched_names": sum(1 for row in crosswalk_rows if row["status"] == "unmatched"),
        "matched_mw": round(matched_mw, 1),
        "matched_mw_share": round(matched_mw / max(1.0, sum(parse_mw(row["mw1"]) for row in rows)), 4),
        "issuers": len(panel_rows),
        "top_issuers": [{"ticker": row["ticker"], "queue_mw": row["queue_mw"], "at_risk_share": row["at_risk_share"]}
                        for row in panel_rows[:12]],
        "base_withdrawal_share": round(base_share, 4),
    }
    SUMMARY_OUT.write_text(json.dumps(summary, indent=1) + "\n")
    print(f"crosswalk: {summary['matched_names']} matched, {summary['unmatched_names']} unmatched names, "
          f"{summary['matched_mw_share']:.1%} of MW matched to listed issuers, {summary['issuers']} issuers")
    for row in summary["top_issuers"][:8]:
        print(" ", row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
