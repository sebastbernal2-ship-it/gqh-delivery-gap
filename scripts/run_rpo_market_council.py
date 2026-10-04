#!/usr/bin/env python3
"""The council over two genuinely distinct data bundles on the powered RPO panel.

Blocks are data families, not architectures: `issuer_facts` reads what the issuer disclosed about
its own obligations, `market_state` reads what the tape did into the disclosure, absolutely and
against the issuer's peer group. The evaluation reports the fused score against every single block
and against naive concatenation, the redundancy between the blocks, the leave-one-out marginal
contribution of each, and issuer-blocked bootstrap intervals on the paired differences.

    python3 scripts/run_rpo_market_council.py
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "hpc" / "probabilistic-council"))
from decision_layer import DEFAULT_COSTS, ordinal_utility_curve  # noqa: E402
from filing_specialist.market_state import MARKET_FEATURES, build as build_market  # noqa: E402
from filing_specialist.rpo_model import FEATURES, prepare_rows  # noqa: E402
from filing_specialist.rpo_panel import FILING_FEATURES, augment_rows, load_filings  # noqa: E402
from panel_council import evaluate_blocks  # noqa: E402


def decision_summary(probabilities: list[list[float]], labels: list[int]) -> dict:
    rows = ordinal_utility_curve(probabilities, labels, DEFAULT_COSTS)
    return {"ordinal_utility": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vintages", type=Path, default=ROOT / "results" / "rpo-vintages.csv")
    parser.add_argument("--filings", type=Path,
                        default=ROOT / "results" / "filings-register-rpo.csv")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results" / "rpo-market-council.json")
    parser.add_argument("--steps", type=int, default=600)
    args = parser.parse_args()

    prepared, drops = prepare_rows(list(csv.DictReader(args.vintages.open())))
    augmented, join_drops = augment_rows(prepared, load_filings(list(csv.DictReader(args.filings.open()))))
    market_features, coverage = build_market(augmented)
    rows = [{**row, **market_row} for row, market_row in zip(augmented, market_features)]

    blocks = {"issuer_facts": tuple(FEATURES) + tuple(FILING_FEATURES),
              "market_state": MARKET_FEATURES}
    report = evaluate_blocks(rows, blocks, steps=args.steps)
    labels = report["row_detail"]["labels"]
    report.update({
        "schema": "panel-council-v1",
        "scope": "development_only",
        "protocol": "docs/plan/rpo-market-council.md",
        "panel": {"rows": len(rows), "issuers": len({row["ticker"] for row in rows}),
                  "drops": drops, "join_drops": join_drops},
        "market_coverage": coverage,
        "decision": {name: decision_summary(report["row_detail"][name], labels)
                     for name in ("council", "concatenated", "issuer_facts", "market_state")},
        "ready_for_performance_claim": False,
        "limitations": [
            "development only; both sealed windows are spent",
            "two data bundles, no text and no option-implied state in this comparison",
            "RPO names, quarterly labels: this measures disclosure surprises, not returns",
            "the market bundle is price-based; no volume or borrow data on most issuers",
        ],
    })
    args.output.write_text(json.dumps(report, indent=1) + "\n")

    scores = report["scores"]
    print("rows", report["panel"]["rows"], "| split", report["split"]["training"],
          report["split"]["calibration"], report["split"]["gate"], report["split"]["pool"],
          report["split"]["evaluation"])
    print("model                log_loss   brier   accuracy")
    for name in ("prevalence", "issuer_facts", "market_state", "concatenated", "council"):
        values = scores[name]
        print(f"  {name:18s} {values['log_loss']:.4f}  {values['brier']:.4f}   {values['accuracy']:.3f}")
    diagnostics = report["diagnostics"]
    print("council minus best single", diagnostics["best_single"],
          json.dumps(diagnostics["council_minus_best_single"]))
    print("council minus concatenated", json.dumps(diagnostics["council_minus_concatenated"]))
    print("marginal contribution (log loss if dropped):",
          json.dumps(diagnostics["marginal_contribution"]))
    print("redundancy:", json.dumps(diagnostics["redundancy"]))
    print("decision, council:")
    for row in report["decision"]["council"]["ordinal_utility"]:
        exact = row["accuracy_acted"]
        print("   cost %.2f coverage %5.1f%% exact %s utility %+.4f" % (
            row["cost"], 100 * row["coverage"],
            f"{100*exact:5.1f}%" if exact is not None else "  n/a ", row["utility_per_row"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
