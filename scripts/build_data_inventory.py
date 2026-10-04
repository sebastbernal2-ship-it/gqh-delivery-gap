#!/usr/bin/env python3
"""Build the data inventory: every dataset this repository has looked at, as graph nodes.

Auto discovers files under results/, docs/scan/ and the local caches, then overlays curated knowledge
(source, coverage, access, licence, what each dataset measures) for the sets that matter. Writes
docs/scan/datasets.jsonl and docs/scan/data-inventory-summary.json.

    python3 scripts/build_data_inventory.py
"""
from __future__ import annotations

import csv
import collections
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "scan" / "datasets.jsonl"
SUMMARY = ROOT / "docs" / "scan" / "data-inventory-summary.json"

CURATED: dict[str, dict] = {
    "queue-panel.csv": {"name": "LBNL interconnection queue panel", "source": "source:lbnl",
                        "access": "public xlsx, browser user agent required", "licence": "public research",
                        "coverage": "36,441 projects, requests to 2024-12-31", "kind": "processed",
                        "measures": ["mechanism:capacity:interconnection-bottleneck", "dig:grid:utility-economics"],
                        "notes": "projects, statuses, dates, MW, technology, developer, cluster"},
    "delivery-revisions.csv": {"name": "Promise revisions between vintages", "source": "source:lbnl",
                               "access": "derived from cached vintages", "licence": "public research",
                               "coverage": "6,407 generators tracked monthly", "kind": "derived",
                               "measures": ["promise:power:planned-capacity-revision"], "notes": "truths T1 to T4"},
    "compute-price-monthly.csv": {"name": "Compute rental prices by family", "source": "source:rental-marketplace",
                                  "access": "public marketplace pages, cached", "licence": "public listing",
                                  "coverage": "18 families, 566 rows, 2022-05 to 2026-09", "kind": "processed",
                                  "measures": ["feature:compute:rental-price", "dig:cloud:compute-index"],
                                  "notes": "median usd per instance hour, multiple zones"},
    "provider-capex-quarterly.csv": {"name": "Provider capex, quarterly", "source": "source:sec",
                                     "access": "data.sec.gov xbrl company concept", "licence": "public",
                                     "coverage": "10 providers, 192 rows", "kind": "processed",
                                     "measures": ["outcome:firm:capex-level", "dig:compute:provider-capex"],
                                     "notes": "cash flow capex concepts, quarterly durations, filed dates"},
    "provider-revenue-quarterly.csv": {"name": "Provider revenue, quarterly", "source": "source:sec",
                                       "access": "data.sec.gov xbrl company concept", "licence": "public",
                                       "coverage": "10 providers, 355 rows", "kind": "processed",
                                       "measures": ["dig:compute:provider-revenue-line"],
                                       "notes": "preferred contract revenue concept with fallback"},
    "complex-capex-quarterly.csv": {"name": "Complex capex, quarterly", "source": "source:sec",
                                    "access": "data.sec.gov xbrl company concept", "licence": "public",
                                    "coverage": "59 names across the declared groups", "kind": "processed",
                                    "measures": ["dig:compute:capex-intensity"], "notes": "one row per quarter fact"},
    "complex-revenue-quarterly.csv": {"name": "Complex revenue, quarterly", "source": "source:sec",
                                      "access": "data.sec.gov xbrl company concept", "licence": "public",
                                      "coverage": "62 names", "kind": "processed",
                                      "measures": ["dig:compute:provider-revenue-line"], "notes": "as above"},
    "complex-assets-quarterly.csv": {"name": "Complex total assets, quarterly", "source": "source:sec",
                                     "access": "data.sec.gov xbrl company concept", "licence": "public",
                                     "coverage": "63 names, 3,324 instant facts", "kind": "processed",
                                     "measures": ["factor:asset-growth"], "notes": "used for the asset growth control"},
    "market-panel.json": {"name": "Declared market panel with groups", "source": "source:market",
                          "access": "cached daily loader", "licence": "free vendor terms",
                          "coverage": "89 series across nine groups", "kind": "processed",
                          "measures": ["dig:compute:equity-transmission"],
                          "notes": "groups: hyperscaler, compute and AI, data centre REIT, buildout, power, fuel, rates, market, commodity"},
    "universe-adv-monthly.csv": {"name": "Monthly dollar volume by name", "source": "source:market",
                                 "access": "yfinance daily bars, cached under results/bar-volume",
                                 "licence": "free vendor terms", "coverage": "59 names, 2017-06 to 2026-10",
                                 "kind": "processed", "measures": ["factor:liquidity"],
                                 "notes": "median dollar volume per name-month, the capacity input"},
    "cascade-tape.json": {"name": "Perpetual venue tape summary", "source": "source:hyperliquid",
                          "access": "public venue endpoints, recorded locally under data/tape",
                          "licence": "public", "coverage": "four markets, 7.3 nominal hours at the last write",
                          "kind": "recorded", "measures": ["force:micro:forced-deleveraging", "force:micro:depth-liquidity"],
                          "notes": "mid, spread, depth, funding, open interest, basis; local only"},
    "agency-universe.csv": {"name": "Agency rated data centre deals", "source": "source:rating-agency",
                            "access": "public publications", "licence": "public summaries",
                            "coverage": "deal universe with ratings", "kind": "processed",
                            "measures": ["dig:compute:financing-cost"], "notes": "per site and per deal securitisations"},
    "credit-deal-registry.csv": {"name": "Credit deal registry", "source": "source:edgar",
                                 "access": "public filings", "licence": "public", "coverage": "data centre and related deals",
                                 "kind": "processed", "measures": ["dig:compute:financing-cost"],
                                 "notes": "deal terms, tranches, covenants where filed"},
    "credit-panel.csv": {"name": "Credit panel for the complex", "source": "source:edgar",
                         "access": "public filings", "licence": "public", "coverage": "issuer level credit rows",
                         "kind": "processed", "measures": ["dig:compute:financing-cost"], "notes": "parent and deal panels"},
    "dscr-thresholds.csv": {"name": "DSCR thresholds", "source": "source:edgar",
                            "access": "public filings", "licence": "public", "coverage": "covenant thresholds",
                            "kind": "processed", "measures": ["dig:compute:financing-cost"],
                            "notes": "covenant levels extracted from indentures"},
    "indenture-covenants.csv": {"name": "Indenture covenants", "source": "source:edgar",
                                "access": "public filings", "licence": "public", "coverage": "deal level",
                                "kind": "processed", "measures": ["force:financing:abs-capacity"],
                                "notes": "maintenance and incurrence covenants"},
    "capacity-event-ledger.csv": {"name": "Capacity event ledger", "source": "source:sec",
                                  "access": "edgar full text search, cached", "licence": "public",
                                  "coverage": "8-K and material agreement events", "kind": "processed",
                                  "measures": ["event:sec:8k-material-agreement"], "notes": "rule dated events"},
    "capacity-strategy.csv": {"name": "Capacity strategy panel", "source": "source:sec",
                              "access": "derived", "licence": "public", "coverage": "per firm capacity decisions",
                              "kind": "processed", "measures": ["outcome:firm:capex-level"], "notes": "candidate panel"},
    "bottleneck-factors.csv": {"name": "Bottleneck factor set", "source": "source:mixed",
                               "access": "derived from public series", "licence": "public", "coverage": "supply chain factors",
                               "kind": "processed", "measures": ["mechanism:capacity:constraint"], "notes": "transformers, turbines, labour"},
    "exposure-panel.csv": {"name": "Exposure panel", "source": "source:mixed", "access": "derived",
                           "licence": "public", "coverage": "firm exposure to bottlenecks", "kind": "processed",
                           "measures": ["factor:exposure"], "notes": "used by the delivery model"},
    "fuel-daily.csv": {"name": "Fuel prices, daily", "source": "source:market", "access": "cached loader",
                       "licence": "free vendor terms", "coverage": "daily fuel series", "kind": "processed",
                       "measures": ["factor:commodity:gas"], "notes": "input to the gas thesis"},
    "implied-vol-test.csv": {"name": "Implied volatility test", "source": "source:options", "access": "snapshots held locally",
                             "licence": "venue terms", "coverage": "short window", "kind": "processed",
                             "measures": ["outcome:market:post-event-drift"], "notes": "entitlement limited"},
    "option-snapshots/index.json": {"name": "Option snapshots", "source": "source:options",
                                    "access": "recorded locally", "licence": "venue terms", "coverage": "few snapshots",
                                    "kind": "recorded", "measures": ["outcome:market:post-event-drift"],
                                    "notes": "no historical chains entitlement"},
    "run-manifest.json": {"name": "Run manifest", "source": "source:internal", "access": "local",
                          "licence": "internal", "coverage": "suite and artifact registry", "kind": "internal",
                          "measures": [], "notes": "tracks producers and results"},
}

CACHE_DIRS = {
    "results/edgar-cache": {"name": "EDGAR cache", "source": "source:edgar", "access": "public filings",
                            "licence": "public", "notes": "full text and filing documents, local only"},
    "results/eia-cache": {"name": "EIA cache", "source": "source:eia", "access": "public api",
                          "licence": "public", "notes": "vintage xlsx archives"},
    "results/sec-capex": {"name": "SEC capex concept cache", "source": "source:sec", "access": "public api",
                          "licence": "public", "notes": "raw concept responses for provider capex"},
    "results/sec-revenue": {"name": "SEC revenue concept cache", "source": "source:sec", "access": "public api",
                            "licence": "public", "notes": "raw concept responses for provider revenue"},
    "results/sec-complex": {"name": "SEC complex concept cache", "source": "source:sec", "access": "public api",
                            "licence": "public", "notes": "capex, revenue and assets for the full complex"},
    "results/bar-cache": {"name": "Daily close cache", "source": "source:market", "access": "cached loader",
                          "licence": "free vendor terms", "notes": "89 series, daily closes"},
    "results/bar-volume": {"name": "Daily close and volume cache", "source": "source:market",
                           "access": "yfinance", "licence": "free vendor terms",
                           "notes": "59 names, used for ADV and the capacity curve"},
    "results/usdm-cache": {"name": "USD momentum cache", "source": "source:market", "access": "cached loader",
                           "licence": "free vendor terms", "notes": "auxiliary market series"},
    "results/vintage-aggregates": {"name": "Vintage aggregates", "source": "source:lbnl", "access": "derived",
                                   "licence": "public research", "notes": "per vintage summary of the queue panel"},
    "data/tape": {"name": "Recorded venue tape", "source": "source:hyperliquid", "access": "public endpoints",
                  "licence": "public", "notes": "JSONL rows: mid, spread, depth, funding, open interest, basis"},
    "data/queues": {"name": "Local queue archives", "source": "source:lbnl", "access": "public xlsx",
                    "licence": "public research", "notes": "downloaded workbooks"},
    "data/factors": {"name": "Local factor series", "source": "source:mixed", "access": "derived",
                     "licence": "mixed", "notes": "intermediate factor panels"},
    "data/promise-series": {"name": "Local promise series", "source": "source:lbnl", "access": "derived",
                            "licence": "public research", "notes": "per generator promise histories"},
    "data/sec-instances": {"name": "SEC instance documents", "source": "source:sec", "access": "public filings",
                           "licence": "public", "notes": "xbrl instances for accounting extraction"},
    "data/hyperliquid": {"name": "Venue recordings", "source": "source:hyperliquid", "access": "public endpoints",
                         "licence": "public", "notes": "pre tape recording of venue data"},
}


def rows_of(path: Path) -> int | None:
    if path.suffix == ".csv":
        try:
            with path.open() as handle:
                return max(0, sum(1 for _ in handle) - 1)
        except Exception:
            return None
    if path.suffix == ".jsonl":
        try:
            with path.open() as handle:
                return sum(1 for line in handle if line.strip())
        except Exception:
            return None
    return None


def main() -> int:
    entries = []
    seen = set()
    for relative, meta in CURATED.items():
        path = ROOT / relative if (ROOT / relative).exists() else ROOT / "results" / relative
        if not path.exists():
            entries.append({"id": f"dataset:{Path(relative).stem}", "path": relative, "status": "missing",
                            **meta})
            seen.add(relative)
            continue
        entries.append({"id": f"dataset:{Path(relative).stem}", "path": relative, "status": "in_hand",
                        "bytes": path.stat().st_size, "rows": rows_of(path), **meta})
        seen.add(relative)
    for pattern in ("results/*.csv", "results/*.json", "results/*.jsonl", "docs/scan/*.jsonl", "docs/scan/*.json"):
        for path in sorted(ROOT.glob(pattern)):
            relative = str(path.relative_to(ROOT))
            if relative in seen or path.name in seen:
                continue
            entries.append({"id": f"dataset:{path.parent.name.replace('results', 'results')}-{path.stem}",
                            "path": relative, "status": "in_hand", "kind": "artifact",
                            "bytes": path.stat().st_size, "rows": rows_of(path), "source": "source:internal",
                            "access": "in repository", "licence": "internal",
                            "notes": "auto discovered; curated entry pending"})
    for relative, meta in CACHE_DIRS.items():
        path = ROOT / relative
        if not path.exists():
            continue
        files = [item for item in path.rglob("*") if item.is_file()]
        entries.append({"id": f"dataset:{Path(relative).name}", "path": relative,
                        "status": "in_hand", "kind": "cache", "files": len(files),
                        "bytes": sum(item.stat().st_size for item in files), "rows": None, **meta})
    for entry in entries:
        entry.setdefault("measures", [])
        entry.setdefault("notes", "")
        entry.setdefault("coverage", "")
    OUT.write_text("".join(json.dumps(entry) + "\n" for entry in entries))
    by_status = collections.Counter(entry["status"] for entry in entries)
    by_source = collections.Counter(entry.get("source", "unknown") for entry in entries)
    total_bytes = sum(entry.get("bytes") or 0 for entry in entries)
    summary = {"datasets": len(entries), "by_status": dict(by_status.most_common()),
               "by_source": dict(by_source.most_common(12)),
               "total_bytes": total_bytes,
               "with_coverage": sum(1 for entry in entries if entry.get("coverage")),
               "with_measures": sum(1 for entry in entries if entry.get("measures")),
               "missing": [entry["path"] for entry in entries if entry["status"] == "missing"]}
    SUMMARY.write_text(json.dumps(summary, indent=1) + "\n")
    print(f"datasets {summary['datasets']} ({dict(by_status)}), {total_bytes / 1e6:.1f} MB, "
          f"{summary['with_coverage']} with coverage, {summary['with_measures']} tied to graph nodes")
    print("by source:", json.dumps(summary["by_source"]))
    if summary["missing"]:
        print("referenced but absent:", summary["missing"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
