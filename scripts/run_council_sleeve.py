#!/usr/bin/env python3
"""The council as a sleeve: fused per-event distributions become positions, walk forward.

Three declared data bundles, one specialist each, on the complex revenue panel:
  issuer_facts   the company's own disclosure history (the surviving sleeve's features)
  market_state   the tape into the disclosure, absolute and peer relative
  peer_momentum  what the declared peer group disclosed most recently, before this event

Per annual origin the specialists are refit, the pool weights are fitted on the last fifth of that
fold's training rows by decision date, and the fused distribution's expected class becomes the
position's conviction, exactly the rule the surviving sleeve uses. The resulting sleeve is run
through the same engine and compared with the baseline two-sleeve portfolio by month-blocked
intervals on the daily differences.

    python3 scripts/run_council_sleeve.py
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import statistics
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "hpc" / "probabilistic-council"))
from filing_specialist.market_state import MARKET_FEATURES, build as build_market  # noqa: E402
from filing_specialist.model import apply_scaler, fit_scaler, fit_softmax, matrix_from_rows  # noqa: E402
from filing_specialist.portfolio_stats import month_blocked_interval, portfolio_metrics  # noqa: E402
from filing_specialist.rpo_model import FEATURES, prepare_rows  # noqa: E402
from council.fusion import linear_opinion_pool  # noqa: E402
from run_complex_council import PEERS, PEER_MAP, with_peer_flags  # noqa: E402
from run_sleeve_portfolio import COSTS, sleeve_daily  # noqa: E402
from run_three_sleeve_portfolio import align, inverse_vol_weights, weighted_daily  # noqa: E402
from run_walk_forward import ORIGINS, blocks, intensity_walk_forward  # noqa: E402

PEER_FEATURES = ("peer_last_surprise", "peer_mean_surprise_3", "peer_coverage")
WEIGHT_STEP = 0.125




def split_conviction(expected_council: float, expected_issuer: float) -> float | None:
    """The declared T60 follow-up: the specialist's direction, the fused distribution's magnitude.

    T60 measured that the single specialist reads the direction of the extreme rows slightly better
    while the council scores the same rows better. This rule keeps both advantages: the sign comes
    from the specialist's expected class, the size from the council's distance to the middle.
    Returns None when either side is neutral, so the caller skips the event.
    """
    magnitude = min(1.0, abs(expected_council - 2.0) / 2.0)
    direction = expected_issuer - 2.0
    if abs(direction) < 1e-9 or magnitude < 1e-9:
        return None
    return math.copysign(magnitude, direction)


def peer_momentum(rows: list[dict]) -> list[dict]:
    """Each row's declared peer group's most recent prior disclosures, strictly before the event."""
    by_group: dict[str, list[tuple[str, float]]] = {}
    ordered = sorted(rows, key=lambda row: str(row["label_available"]))
    features = []
    for row in ordered:
        group = PEER_MAP.get(str(row.get("group_name") or "").strip(), "")
        history = by_group.setdefault(group, [])
        decision = str(row["label_available"])[:10]
        values = [surprise for day, surprise in history if day < decision]
        last = values[-1] if values else 0.0
        recent = values[-3:]
        features.append({
            "peer_last_surprise": last,
            "peer_mean_surprise_3": statistics.mean(recent) if recent else 0.0,
            "peer_coverage": float(min(len(recent), 3)) / 3.0,
        })
        surprise = row.get("label_relative_surprise")
        if surprise not in (None, ""):
            history.append((decision, float(surprise)))
    order = {id(row): position for position, row in enumerate(ordered)}
    return [features[order[id(row)]] for row in rows]


def fit_fold(rows: list[dict], blocks_map: dict[str, tuple[str, ...]], start: str
             ) -> tuple[dict, dict, list[float]]:
    """Block models and pool weights for one origin, plus the index set of the fold's training rows."""
    training = [row for row in rows if str(row["label_available"])[:10] < start]
    later = [row for row in rows if str(row["label_available"])[:10] >= start]
    if len(training) < 60:
        return {}, {}, []
    cut = max(1, int(0.8 * len(training)))
    fit_rows, calibration = training[:cut], training[cut:]
    train_labels = np.array([int(row["label_bin"]) for row in fit_rows], dtype=int)
    classes = tuple(sorted({int(label) for label in train_labels}))
    cal_labels = np.array([int(row["label_bin"]) for row in calibration], dtype=int)
    leaders = {}
    for name, names in blocks_map.items():
        matrix, _ = matrix_from_rows(fit_rows, names)
        stats = fit_scaler(matrix)
        parameters = fit_softmax(apply_scaler(matrix, stats), train_labels, classes)
        leaders[name] = (names, stats, parameters, classes)
    return leaders, {"calibration": calibration, "cal_labels": cal_labels, "classes": classes,
                     "later": later}, []


def block_probabilities(leader, rows: list[dict]) -> np.ndarray:
    names, stats, parameters, classes = leader
    matrix, _ = matrix_from_rows(rows, names)
    design = apply_scaler(matrix, stats)
    from filing_specialist.model import predict_softmax
    return np.array(predict_softmax(parameters, design))


def pool_grid(names: tuple[str, ...]) -> list[dict]:
    steps = int(round(1.0 / WEIGHT_STEP))
    weights = []
    for combination in itertools.product(range(steps + 1), repeat=len(names)):
        if sum(combination) == steps:      # single-specialist corners are allowed on purpose: the
                                           # fusion must be able to fall back on the best block

            weights.append({name: value * WEIGHT_STEP for name, value in zip(names, combination)})
    return weights


def log_loss(probabilities: np.ndarray, labels: np.ndarray) -> float:
    picked = np.clip(probabilities[np.arange(len(labels)), labels], 1e-12, 1.0)
    return float(-np.log(picked).mean())


def choose_weights(names: tuple[str, ...], calibration: list[dict],
                   leader_probabilities: dict[str, np.ndarray], cal_labels: np.ndarray,
                   classes: tuple[int, ...]) -> tuple[dict, dict]:
    best, scores = None, {}
    for weights in pool_grid(names):
        fused = []
        for position in range(len(calibration)):
            opinions = {name: tuple(leader_probabilities[name][position]) for name in names}
            fused.append(linear_opinion_pool(opinions, weights))
        positions = [classes.index(int(label)) for label in cal_labels]
        value = log_loss(np.array(fused), np.array(positions))
        scores[json.dumps(weights, sort_keys=True)] = value
        if best is None or value < best[1]:
            best = (weights, value)
    return best[0], {"best_log_loss": best[1], "grid": len(scores)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vintages", type=Path, default=ROOT / "results" / "revenue-vintages-pit.csv")
    parser.add_argument("--cache", type=Path, default=ROOT / "results" / "bar-cache")
    parser.add_argument("--baseline", type=Path, default=ROOT / "results" / "walk-forward-baseline.json")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "council-sleeve.json")
    parser.add_argument("--sizing", choices=("conviction", "sign", "split"), default="conviction",
                        help="sign: equal weight, council direction; split: specialist direction, "
                             "council magnitude (the declared T60 follow-up)")
    args = parser.parse_args()

    rows, drops = prepare_rows(list(csv.DictReader(args.vintages.open())))
    rows = with_peer_flags(rows)
    market_features, market_coverage = build_market(rows, cache=args.cache, groups=PEERS)
    for row, features in zip(rows, market_features):
        row.update(features)
    for row, features in zip(rows, peer_momentum(rows)):
        row.update(features)
    rows.sort(key=lambda row: str(row["label_available"]))
    blocks_map = {"issuer_facts": tuple(FEATURES), "market_state": tuple(MARKET_FEATURES),
                  "peer_momentum": PEER_FEATURES}
    names = tuple(blocks_map)

    events, folds, rows_detail = [], [], []
    for start, end in blocks(ORIGINS):
        leaders, fold, _ = fit_fold(rows, blocks_map, start)
        if not leaders:
            continue
        calibration, cal_labels, classes = fold["calibration"], fold["cal_labels"], fold["classes"]
        leader_probabilities = {name: block_probabilities(leaders[name], calibration) for name in names}
        weights, fit_info = choose_weights(names, calibration, leader_probabilities, cal_labels, classes)
        later = [row for row in fold["later"] if start <= str(row["label_available"])[:10] < end]
        point_probabilities = {name: block_probabilities(leaders[name], later) for name in names}
        fold_events = 0
        for position, row in enumerate(later):
            opinions = {name: tuple(point_probabilities[name][position]) for name in names}
            fused = linear_opinion_pool(opinions, weights)
            expected = sum(k * float(p) for k, p in zip(classes, fused))
            conviction = (expected - 2.0) / 2.0
            if abs(conviction) < 1e-9:
                continue
            expected_issuer = sum(k * float(p) for k, p in zip(classes, opinions["issuer_facts"]))
            if args.sizing == "sign":
                conviction = math.copysign(1.0, conviction)
            elif args.sizing == "split":
                split = split_conviction(expected, expected_issuer)
                if split is None:
                    continue
                conviction = split
            rows_detail.append({"label": int(row["label_bin"]), "council": list(fused),
                                "issuer_facts": list(opinions["issuer_facts"]),
                                "expected_council": expected, "expected_issuer": expected_issuer})
            events.append({"ticker": str(row["ticker"]), "decision": str(row["label_available"])[:10],
                           "weight": conviction, "period_end": str(row["period_end"]), "block": start})
            fold_events += 1
        folds.append({"block": start, "train": len(rows), "later": len(later), "events": fold_events,
                      "weights": weights, "calibration_log_loss": fit_info["best_log_loss"],
                      "grid": fit_info["grid"]})
        print("block %s later %3d events %3d weights %s" % (
            start, len(later), fold_events,
            {name: round(value, 3) for name, value in weights.items()}))

    daily, info = sleeve_daily(events, args.cache, COSTS["base"])
    intensity, _ = intensity_walk_forward(1.0)
    baseline = json.loads(args.baseline.read_text())
    baseline_sleeve = baseline["sleeves"]["revenue"]
    baseline_composite = baseline["portfolio_daily"]["without_capex_inverse_vol"]

    dates, values = align([daily, intensity])
    weights_pair = inverse_vol_weights(values)
    composite = weighted_daily(dates, values, weights_pair)

    def score_rows(key: str, subset: list[dict]) -> dict:
        if not subset:
            return {"rows": 0, "log_loss": None, "direction_hit": None}
        losses, hits = [], []
        for detail in subset:
            probabilities = np.array(detail[key])
            losses.append(-math.log(max(float(probabilities[detail["label"]]), 1e-12)))
            expected = detail["expected_council" if key == "council" else "expected_issuer"]
            if abs(expected - 2.0) > 1e-9:
                hits.append(1.0 if (expected - 2.0) * (detail["label"] - 2.0) > 0 else 0.0)
        return {"rows": len(subset), "log_loss": statistics.mean(losses),
                "direction_hit": statistics.mean(hits) if hits else None}

    extremes = [detail for detail in rows_detail if detail["label"] in (0, 4)]
    mechanism = {"all_rows": {key: score_rows(key, rows_detail) for key in ("council", "issuer_facts")},
                 "extreme_rows": {key: score_rows(key, extremes) for key in ("council", "issuer_facts")}}

    report = {
        "schema": "council-sleeve-v1",
        "mechanism": mechanism, "scope": "development_only",
        "protocol": "docs/plan/open-work.md", "panel": {
            "rows": len(rows), "issuers": len({row["ticker"] for row in rows}), "drops": drops,
            "market_coverage": market_coverage, "blocks": {k: list(v) for k, v in blocks_map.items()}},
        "folds": folds,
        "sleeve": {"events": len(events), "sessions": info.get("sessions"),
                   "metrics": portfolio_metrics(daily)},
        "composite": {"weights": weights_pair, "metrics": portfolio_metrics(composite)},
        "baseline": {"sleeve_metrics": baseline_sleeve["metrics"],
                     "composite_metrics": portfolio_metrics(baseline_composite)},
        "intervals": {
            "sleeve_daily_difference": month_blocked_interval(daily, baseline["portfolios"] and daily),
            "composite_minus_baseline": month_blocked_interval(composite, baseline_composite),
        },
        "ready_for_performance_claim": False,
        "limitations": [
            "development only; both sealed windows are spent",
            "the pool grid is coarse: three weights on eighths",
            "the peer map and the peer-momentum block are declared here, not part of a frozen recipe",
        ],
    }
    report["intervals"]["sleeve_daily_difference"] = None
    args.output.write_text(json.dumps(report, indent=1) + "\n")

    sleeve_metrics = report["sleeve"]["metrics"]
    print("council sleeve: events %d net %+.2f%% vol %.1f%% sharpe %+.3f dd %+.1f%%" % (
        len(events), sleeve_metrics["annual_return"] * 100, sleeve_metrics["annual_vol"] * 100,
        sleeve_metrics["sharpe"], sleeve_metrics["max_drawdown"] * 100))
    print("baseline sleeve: net %+.2f%% sharpe %+.3f dd %+.1f%%" % (
        baseline_sleeve["metrics"]["annual_return"] * 100, baseline_sleeve["metrics"]["sharpe"],
        baseline_sleeve["metrics"]["max_drawdown"] * 100))
    mean_weights = [round(statistics.mean(weights), 3) for weights in weights_pair]
    print("council composite: net %+.2f%% sharpe %+.3f dd %+.1f%% | mean weights %s" % (
        report["composite"]["metrics"]["annual_return"] * 100,
        report["composite"]["metrics"]["sharpe"], report["composite"]["metrics"]["max_drawdown"] * 100,
        mean_weights))
    print("baseline composite: net %+.2f%% sharpe %+.3f dd %+.1f%%" % (
        portfolio_metrics(baseline_composite)["annual_return"] * 100,
        portfolio_metrics(baseline_composite)["sharpe"],
        portfolio_metrics(baseline_composite)["max_drawdown"] * 100))
    interval = report["intervals"]["composite_minus_baseline"]
    print("composite minus baseline: point %+.4f CI [%+.4f, %+.4f] share+ %.3f months %s" % (
        interval["point"], interval["lower"], interval["upper"], interval["share_positive"],
        interval.get("months")))
    print("written", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
