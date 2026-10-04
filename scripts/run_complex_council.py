#!/usr/bin/env python3
"""The council over two data bundles on the complex revenue panel, not the RPO panel.

Blocks are data families: issuer facts (the disclosure history features) and market state (the tape
into the disclosure, absolute and peer-relative). The peer groups are mapped from the market panel's
own group names into four declared peer sets, so the relative features are meaningful.

Reports the proper scores of every single block, the concatenation reference and the fused council,
the three numbers the design asks for, and the ordinal decision view.

    python3 scripts/run_complex_council.py
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "hpc" / "probabilistic-council"))
from decision_layer import DEFAULT_COSTS, DEFAULT_THRESHOLDS, accuracy_at_target  # noqa: E402
from decision_layer import ordinal_utility_curve, selective_curve  # noqa: E402
from filing_specialist.market_state import MARKET_FEATURES, build as build_market  # noqa: E402
from filing_specialist.rpo_model import FEATURES, prepare_rows  # noqa: E402
from panel_council import evaluate_blocks  # noqa: E402

PEER_MAP = {"data_center_reit": "datacenter", "hyperscaler": "datacenter",
            "compute_and_ai": "equipment", "buildout": "equipment",
            "power": "utility", "fuel_and_nuclear": "utility"}
PEERS = ("datacenter", "equipment", "utility", "contractor")


def with_peer_flags(rows: list[dict]) -> list[dict]:
    """Map the market panel's group names onto the four declared peer sets."""
    mapped = []
    for row in rows:
        peer = PEER_MAP.get(str(row.get("group_name") or "").strip(), "")
        enriched = dict(row)
        for name in PEERS:
            enriched[f"group_{name}"] = 1.0 if name == peer else 0.0
        mapped.append(enriched)
    return mapped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vintages", type=Path,
                        default=ROOT / "results" / "revenue-vintages-pit.csv")
    parser.add_argument("--cache", type=Path, default=ROOT / "results" / "bar-cache")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results" / "complex-council.json")
    parser.add_argument("--steps", type=int, default=600)
    args = parser.parse_args()

    rows, drops = prepare_rows(list(csv.DictReader(args.vintages.open())))
    rows = with_peer_flags(rows)
    market_features, market_coverage = build_market(rows, cache=args.cache, groups=PEERS)
    for row, features in zip(rows, market_features):
        row.update(features)

    blocks = {"issuer_facts": tuple(FEATURES), "market_state": MARKET_FEATURES}
    report = evaluate_blocks(rows, blocks, steps=args.steps)
    labels = report["row_detail"]["labels"]
    report.update({
        "schema": "complex-council-v1", "scope": "development_only",
        "protocol": "docs/plan/open-work.md", "panel": {
            "rows": len(rows), "issuers": len({row["ticker"] for row in rows}), "drops": drops,
            "market_coverage": market_coverage, "peer_map": PEER_MAP, "peers": list(PEERS)},
        "decision": {name: {"selective": selective_curve(report["row_detail"][name], labels,
                                                         DEFAULT_THRESHOLDS),
                            "ordinal": ordinal_utility_curve(report["row_detail"][name], labels,
                                                             DEFAULT_COSTS)}
                     for name in ("council", "concatenated", "issuer_facts", "market_state")},
        "ready_for_performance_claim": False,
        "limitations": [
            "development only; both sealed windows are spent",
            "complex names only, 55 issuers, quarterly events",
            "the peer map is declared here and is not part of any frozen recipe",
            "flat costs are irrelevant here: this scores distributions, not trades",
        ],
    })
    best_single = report["diagnostics"]["best_single"]
    for target in ("0.5", "0.6", "0.7"):
        report.setdefault("accuracy_at_target", {})[f"council_{target}"] = accuracy_at_target(
            report["decision"]["council"]["selective"], float(target))
    args.output.write_text(json.dumps(report, indent=1) + "\n")

    print(f"panel {len(rows)} rows | issuers {report['panel']['issuers']} | market coverage {market_coverage['market_return_60']['share']}")
    print("model               log_loss   brier   accuracy")
    for name in ("prevalence", "issuer_facts", "market_state", "concatenated", "council"):
        values = report["scores"][name]
        print("  %-16s  %.4f   %.4f    %.3f" % (name, values["log_loss"], values["brier"],
                                                values["accuracy"]))
    print("best single:", best_single)
    print("council minus best single:", json.dumps(report["diagnostics"]["council_minus_best_single"]))
    print("council minus concatenated:", json.dumps(report["diagnostics"]["council_minus_concatenated"]))
    print("marginal contribution:", json.dumps(report["diagnostics"]["marginal_contribution"]))
    print("redundancy:", json.dumps(report["diagnostics"]["redundancy"]))
    print("decision, council ordinal:")
    for row in report["decision"]["council"]["ordinal"]:
        exact = row["accuracy_acted"]
        print("   cost %.2f coverage %5.1f%% exact %s utility %+.4f" % (
            row["cost"], 100 * row["coverage"],
            f"{100*exact:5.1f}%" if exact is not None else "  n/a ", row["utility_per_row"]))
    print("written", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
