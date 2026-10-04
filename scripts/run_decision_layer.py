#!/usr/bin/env python3
"""Score the final decision, not the distribution: one action per case, or none.

Two probability sources feed one declared decision rule
(hpc/probabilistic-council/decision_layer.py):

- the council over the two filing evidence blocks, 20 evaluation rows, read from
  results/filing-council-ab.json, which scripts/run_filing_council.py writes;
- the point-in-time RPO model with its filing features, 833 evaluation rows, refitted here on the
  same chronological split as its published comparison.

Development only. Small samples are labelled, never averaged into a headline.

    python3 scripts/run_decision_layer.py
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
from filing_specialist.model import fit_and_forecast  # noqa: E402
from filing_specialist.rpo_model import FEATURES, prepare_rows  # noqa: E402
from filing_specialist.rpo_panel import FILING_FEATURES, augment_rows, load_filings  # noqa: E402
from decision_layer import (DEFAULT_COSTS, DEFAULT_TARGETS, DEFAULT_THRESHOLDS,  # noqa: E402
                            accuracy_at_target, ordinal_utility_curve, selective_curve,
                            utility_curve)


def index_labels(classes: list[int], labels: list[int]) -> list[int]:
    return [classes.index(int(label)) for label in labels]


def rpo_source(vintages: Path, filings: Path, fraction: float) -> dict:
    prepared, _ = prepare_rows(list(csv.DictReader(vintages.open())))
    augmented, _ = augment_rows(prepared, load_filings(list(csv.DictReader(filings.open()))))
    fitted = fit_and_forecast(augmented, FEATURES + FILING_FEATURES, fraction=fraction)
    return {"classes": list(fitted["classes"]),
            "labels": index_labels(list(fitted["classes"]), list(fitted["test_labels"])),
            "probabilities": fitted["softmax_probabilities"].tolist()}


def council_source(path: Path) -> dict:
    report = json.loads(path.read_text())
    if "row_detail" not in report:
        raise SystemExit(f"{path} has no row_detail; rerun scripts/run_filing_council.py")
    detail = report["row_detail"]
    return {"classes": detail["classes"],
            "labels": index_labels(detail["classes"], detail["labels"]),
            "probabilities": detail["council"]}


def summarise(source: dict) -> dict:
    probabilities, labels = source["probabilities"], source["labels"]
    curve = selective_curve(probabilities, labels, DEFAULT_THRESHOLDS)
    utility = utility_curve(probabilities, labels, DEFAULT_COSTS)
    return {
        "rows": len(labels),
        "classes": source["classes"],
        "selective": curve,
        "utility": utility,
        "ordinal_utility": ordinal_utility_curve(probabilities, labels, DEFAULT_COSTS),
        "accuracy_at_target": {str(target): accuracy_at_target(curve, target)
                               for target in DEFAULT_TARGETS},
        "always_on_accuracy": sum(1 for row in curve if row["threshold"] <= 0.20
                                  and row["accuracy_acted"] is not None) and next(
            (row["accuracy_acted"] for row in curve if row["threshold"] == 0.20), None),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vintages", type=Path, default=ROOT / "results" / "rpo-vintages.csv")
    parser.add_argument("--filings", type=Path,
                        default=ROOT / "results" / "filings-register-rpo.csv")
    parser.add_argument("--council", type=Path,
                        default=ROOT / "results" / "filing-council-ab.json")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "results" / "decision-layer.json")
    parser.add_argument("--split", type=float, default=0.7)
    args = parser.parse_args()

    sources = {"rpo_with_filings": rpo_source(args.vintages, args.filings, args.split),
               "filing_council": council_source(args.council)}
    report = {
        "schema": "decision-layer-v1",
        "scope": "development_only",
        "protocol": "hpc/probabilistic-council/decision_layer.py",
        "rule": "act when reward * (2 * p_best - 1) > cost; a correct call pays +1, a wrong one -1",
        "thresholds": list(DEFAULT_THRESHOLDS),
        "costs": list(DEFAULT_COSTS),
        "sources": {name: summarise(source) for name, source in sources.items()},
        "ready_for_performance_claim": False,
        "limitations": [
            "development only; both sealed windows are spent",
            "the RPO source is one model, the council source is the fused ensemble",
            "20 evaluation rows on the council source, 833 on the RPO source",
            "no trade is placed: utility is the declared classification payoff, not P&L",
        ],
    }
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    for name, block in report["sources"].items():
        print(f"--- {name}: {block['rows']} rows")
        print("   gate  coverage  accuracy_acted")
        for row in block["selective"]:
            if row["accuracy_acted"] is not None:
                print("   %.2f    %5.1f%%     %5.1f%%" % (
                    row["threshold"], 100 * row["coverage"], 100 * row["accuracy_acted"]))
        print("   cost  coverage  exact_hit  utility  acting_blind  gain")
        for row in block["ordinal_utility"]:
            exact = row["accuracy_acted"]
            print("   %.2f   %5.1f%%    %s  %+.4f  %+.4f  %+.4f" % (
                row["cost"], 100 * row["coverage"],
                f"{100 * exact:5.1f}%" if exact is not None else "  n/a ",
                row["utility_per_row"], row["utility_acting_on_every_row"],
                row["utility_gain_over_blind"]))
        for target, best in block["accuracy_at_target"].items():
            if best:
                print("   target %s: coverage %.1f%% at accuracy %.1f%%" % (
                    target, 100 * best["coverage"], 100 * best["accuracy_acted"]))
            else:
                print(f"   target {target}: never reached")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
