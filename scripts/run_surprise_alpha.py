#!/usr/bin/env python3
"""Does the disclosure-surprise forecast predict returns? The alpha bridge, measured.

Out-of-sample rows only: the 70/30 chronological split of the RPO panel that the published
comparison already used, so no row measured here was seen in training. Entry is the close of the
first session strictly after the disclosure, per the strategy's repaired next-session convention.

Three return variants are reported for every horizon:

- raw: the plain close-to-close return,
- month neutral: demeaned inside the entry month, which removes the complex-wide trend,
- month and group neutral: demeaned inside the entry month crossed with the peer group, which also
  removes a peer-group tilt.

Development only; no sealed rows; one price source; borrow cost unmeasured.

    python3 scripts/run_surprise_alpha.py
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.event_returns import (HORIZONS, attach_returns, blocked_spread_ci,  # noqa: E402
                                             entry_month, group_means, long_short, neutralise,
                                             quintile_rows, rank_ic)
from filing_specialist.market_state import load_series  # noqa: E402
from filing_specialist.model import chronological_split, fit_and_forecast  # noqa: E402
from filing_specialist.rpo_model import FEATURES, prepare_rows  # noqa: E402
from filing_specialist.rpo_panel import FILING_FEATURES, augment_rows, load_filings  # noqa: E402

COST_TIERS = (0.0, 10.0, 20.0, 40.0)
VARIANTS = ("raw", "month_neutral", "month_group_neutral")
GROUPS = ("datacenter", "equipment", "utility", "contractor")


def value_key_for(variant: str, horizon: int) -> str:
    return f"fwd_ret_{horizon}" if variant == "raw" else f"{variant}_{horizon}"


def horizon_stats(rows: list[dict], horizon: int, variant: str, top: int, bottom: int) -> dict:
    key = value_key_for(variant, horizon)
    finite = [row[key] for row in rows if not math.isnan(row.get(key, math.nan))]
    return {
        "rows_with_returns": len(finite),
        "mean_return": (sum(finite) / len(finite)) if finite else None,
        "by_predicted_bin": group_means(rows, "predicted_bin", key),
        "by_confidence_quintile": quintile_rows(rows, horizon, value_key=key),
        "information_coefficient": rank_ic([row["expected_bin"] for row in rows],
                                           [row[key] for row in rows]),
        "long_short": [long_short(rows, horizon, top, bottom, cost, value_key=key)
                       for cost in COST_TIERS],
        "long_short_interval_20bps": blocked_spread_ci(rows, horizon, top, bottom, cost_bps=20.0,
                                                       value_key=key),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vintages", type=Path, default=ROOT / "results" / "rpo-vintages.csv")
    parser.add_argument("--filings", type=Path,
                        default=ROOT / "results" / "filings-register-rpo.csv")
    parser.add_argument("--cache", type=Path, default=ROOT / "results" / "bar-cache")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "surprise-alpha.json")
    parser.add_argument("--split", type=float, default=0.7)
    args = parser.parse_args()

    prepared, drops = prepare_rows(list(csv.DictReader(args.vintages.open())))
    augmented, join_drops = augment_rows(prepared, load_filings(list(csv.DictReader(args.filings.open()))))
    train, test = chronological_split(augmented, args.split)
    fitted = fit_and_forecast(augmented, tuple(FEATURES) + tuple(FILING_FEATURES), fraction=args.split)
    classes = list(fitted["classes"])
    probabilities = fitted["softmax_probabilities"]
    if not (len(test) == len(fitted["test_labels"]) == len(probabilities)):
        raise SystemExit("the split and the forecast rows disagree")

    cache = {ticker: load_series(ticker, args.cache)
             for ticker in {str(row["ticker"]) for row in test}}
    coverage = attach_returns(test, cache, HORIZONS)
    for row, values in zip(test, probabilities):
        order = int(values.argmax())
        row["predicted_bin"] = classes[order]
        row["confidence"] = float(values[order])
        row["expected_bin"] = float(sum(k * float(p) for k, p in zip(classes, values)))
        row["entry_month"] = entry_month(row)
        row["peer_group"] = next((group for group in GROUPS
                                  if float(row.get(f"group_{group}") or 0.0) >= 0.5), "other")

    for horizon in HORIZONS:
        for variant, keys in (("month_neutral", ("entry_month",)),
                              ("month_group_neutral", ("entry_month", "peer_group"))):
            for row, value in zip(test, neutralise(test, horizon, keys)):
                row[f"{variant}_{horizon}"] = value

    top, bottom = classes[-1], classes[0]
    report = {
        "schema": "surprise-alpha-v1",
        "scope": "development_only",
        "protocol": "docs/plan/surprise-alpha.md",
        "entry_rule": "close of the first session strictly after the disclosure availability date",
        "variants": {variant: ("raw close-to-close" if variant == "raw" else
                               "demeaned inside " + variant.replace("_neutral", "").replace("_", " x "))
                     for variant in VARIANTS},
        "panel": {"rows": len(augmented), "train_rows": len(train), "test_rows": len(test),
                  "issuers": len({row["ticker"] for row in test}), "drops": drops,
                  "join_drops": join_drops, "return_coverage": coverage},
        "classes": classes, "top_bin": top, "bottom_bin": bottom,
        "statistics": {variant: {} for variant in VARIANTS},
        "ready_for_performance_claim": False,
        "limitations": [
            "development only; the sealed windows are spent and no row here is a fresh holdout",
            "one price source as cached; no borrow cost, no slippage beyond the flat tiers",
            "quarterly disclosures: twenty-session returns overlap across adjacent quarters",
            "about 89 evaluation issuers in the traded bins, so the intervals stay wide",
            "a surprise forecast is not a strategy: no sizing, volatility target or capacity model",
        ],
    }
    for variant in VARIANTS:
        for horizon in HORIZONS:
            report["statistics"][variant][str(horizon)] = horizon_stats(test, horizon, variant,
                                                                        top, bottom)
    args.output.write_text(json.dumps(report, indent=1) + "\n")

    print("test rows", len(test), "| issuers", report["panel"]["issuers"],
          "| return coverage", coverage["share"])
    for horizon in HORIZONS:
        print(f"--- horizon {horizon} session(s)")
        for variant in VARIANTS:
            block = report["statistics"][variant][str(horizon)]
            spread = block["long_short"][2]
            interval = block["long_short_interval_20bps"]
            print("   %-19s mean %+.4f | IC %+.4f | n %d/%d | spread %+.4f | net(20bps) %+.4f | interval [%s, %s] share+ %.2f" % (
                variant, block["mean_return"] or float("nan"), block["information_coefficient"],
                spread["n_long"], spread["n_short"], spread["spread"] or float("nan"),
                spread["net"] or float("nan"),
                f"{interval['lower']:+.4f}" if interval.get("lower") is not None else "n/a",
                f"{interval['upper']:+.4f}" if interval.get("upper") is not None else "n/a",
                interval.get("share_positive", float("nan"))))
        if horizon == 20:
            for variant in VARIANTS:
                print(f"   bins, {variant}: " + ", ".join(
                    "bin %s n %d mean %+.4f" % (g["group"], g["n"], g["mean"])
                    for g in report["statistics"][variant]["20"]["by_predicted_bin"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
