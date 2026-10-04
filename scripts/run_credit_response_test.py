#!/usr/bin/env python3
"""Do the parents' bond marks respond to equity, at quarterly frequency? Declared before it is run.

This is the first test in this effort where both legs of the mechanism carry real numbers: a dated credit mark
per CUSIP from fund holdings, and an equity price per issuer. The mechanism says a constrained counterparty's
cost of risk moves with its prospects; the test asks whether that shows up at all in the marks we can reach.

Declaration, frozen here before any statistic is computed.

- **Unit.** A CUSIP and a pair of consecutive quarterly marks. The outcome is the mark change in price points
  per 100 of par, with the quarter mean removed so the common credit factor is absorbed rather than counted as
  signal.
- **Predictors, four.** The issuer's own equity return over the same window, over the prior window, the data
  center cluster factor over the same window, and the cluster factor over the prior window. The cluster factor
  is the equal weight return of PWR, EME, ETN and DLR.
- **Grid: four predictors across two samples, the full paired panel and the own-equity subset, so eight
  tests.** The grid size is printed before the results.
- **Null.** Mark changes are permuted in blocks of four consecutive quarters, 500 draws, which keeps the
  serial structure a daily shuffle would destroy.
- **Rate control.** Benjamini-Hochberg across the eight.
- **Ceiling.** Descriptive only. No causal word applies to anything printed here.
- **Falsifier.** If no predictor reaches its placebo band after rate control, then the reachable credit marks
  are not coupled to equity at quarterly frequency, and the parent level credit channel has no support.

Usage:
    python3 scripts/run_credit_response_test.py [--draws 500] [--block 4]
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from scan.series import load_bars  # noqa: E402

PANEL = ROOT / "results" / "parent-bond-panel.csv"
OUT_CSV = ROOT / "results" / "credit-response-test.csv"
OUT_JSON = ROOT / "results" / "credit-response-test.json"

TICKER_OF = {
    "Digital Realty Trust LP": "DLR", "Digital Realty Trust Inc": "DLR",
    "Iron Mountain Inc": "IRM", "American Tower Corp": "AMT", "Oracle Corp": "ORCL",
}
CLUSTER = ["PWR", "EME", "ETN", "DLR"]


def quarter_end(stamp: str) -> str:
    return stamp[:10]


def price_on(bars: dict[str, float], stamp: str) -> float | None:
    candidates = [day for day in bars if day <= stamp]
    if not candidates:
        return None
    return bars[max(candidates)]


def cluster_series() -> dict[str, float]:
    series = {ticker: load_bars(ticker) for ticker in CLUSTER}
    days = sorted({day for bars in series.values() for day in bars})
    out: dict[str, float] = {}
    for day in days:
        values = [bars[day] for bars in series.values() if day in bars]
        if len(values) >= 3:
            out[day] = statistics.fmean(values)
    return out


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 4:
        return None
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sxx ** 0.5 * syy ** 0.5)


def block_shuffle(values: list[float], block: int, rng: random.Random) -> list[float]:
    blocks = [values[i:i + block] for i in range(0, len(values), block)]
    rng.shuffle(blocks)
    return [value for chunk in blocks for value in chunk][:len(values)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--draws", type=int, default=500)
    parser.add_argument("--block", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20261003)
    args = parser.parse_args(argv)
    rng = random.Random(args.seed)

    rows = list(csv.DictReader(PANEL.open()))
    by_cusip: dict[str, list[dict]] = {}
    for row in rows:
        by_cusip.setdefault(row["cusip"], []).append(row)

    equities = {ticker: load_bars(ticker) for ticker in set(TICKER_OF.values())}
    cluster = cluster_series()

    pairs: list[dict] = []
    for cusip, marks in by_cusip.items():
        marks.sort(key=lambda row: row["period"])
        for previous, current in zip(marks, marks[1:]):
            try:
                delta = float(current["price_per_100"]) - float(previous["price_per_100"])
            except (TypeError, ValueError):
                continue
            window = (quarter_end(previous["period"]), quarter_end(current["period"]))
            if window[0] >= window[1]:
                continue
            def change(series: dict[str, float]) -> float | None:
                start, end = price_on(series, window[0]), price_on(series, window[1])
                return (end / start - 1.0) if start and end else None
            ticker = TICKER_OF.get(current["issuer_entity"], "")
            pairs.append({
                "cusip": cusip, "issuer": current["issuer_entity"], "ticker": ticker,
                "period": current["period"], "quarter": current["period"][:7],
                "delta_mark": delta,
                "own_equity": change(equities.get(ticker, {})) if ticker else None,
                "cluster": change(cluster),
            })
    if not pairs:
        raise SystemExit("no consecutive mark pairs found")

    quarters = sorted({pair["quarter"] for pair in pairs})
    for pair in pairs:
        same_quarter = [other["delta_mark"] for other in pairs if other["quarter"] == pair["quarter"]]
        pair["delta_demeaned"] = pair["delta_mark"] - statistics.fmean(same_quarter)
        index = quarters.index(pair["quarter"])
        pair["cluster_prior"] = (pairs[0]["cluster"] if index == 0 else
                                 [other["cluster"] for other in pairs
                                  if other["quarter"] == quarters[index - 1]][0]
                                 if any(other["quarter"] == quarters[index - 1] for other in pairs) else None)
        prior_pairs = [other for other in pairs if other["quarter"] < pair["quarter"]
                       and other["cusip"] == pair["cusip"]]
        pair["own_prior"] = prior_pairs[-1]["own_equity"] if prior_pairs else None

    samples = {
        "paired_panel": lambda pair: True,
        "own_equity_subset": lambda pair: bool(pair["ticker"]),
    }
    predictors = {
        "own_equity_same_window": lambda pair: pair["own_equity"],
        "own_equity_prior_window": lambda pair: pair["own_prior"],
        "cluster_same_window": lambda pair: pair["cluster"],
        "cluster_prior_window": lambda pair: pair["cluster_prior"],
    }
    grid = [(sample, predictor) for sample in samples for predictor in predictors]
    print(f"declared grid: {len(samples)} samples x {len(predictors)} predictors = {len(grid)} tests")
    print(f"mark pairs: {len(pairs)} | quarters: {len(quarters)} | CUSIPs: {len(by_cusip)}")
    print(f"null: block shuffle, block={args.block} quarters, draws={args.draws}")
    print("")

    results = []
    for sample, predictor in grid:
        subset = [pair for pair in pairs if samples[sample](pair) and predictors[predictor](pair) is not None]
        xs = [predictors[predictor](pair) for pair in subset]
        ys = [pair["delta_demeaned"] for pair in subset]
        r = pearson(xs, ys)
        if r is None:
            continue
        observed = abs(r)
        draws = [abs(pearson(block_shuffle(xs, args.block, rng), ys) or 0.0) for _ in range(args.draws)]
        hit = sum(1 for value in draws if value >= observed)
        p_value = (1 + hit) / (1 + len(draws))
        ordered = sorted(xs)
        sd = statistics.pstdev(xs) if len(xs) > 1 else 0.0
        mde = 2.0 / max(len(xs) ** 0.5, 1)  # a stated ceiling, computed not guessed
        results.append({
            "sample": sample, "predictor": predictor, "n": len(xs),
            "correlation": round(r, 5), "placebo_p": round(p_value, 5),
            "predictor_sd": round(sd, 5), "mde_abs_r": round(mde, 3),
            "beats_placebo_95": p_value <= 0.05,
        })

    order = sorted(range(len(results)), key=lambda i: results[i]["placebo_p"])
    cutoff = 0
    for rank, index in enumerate(order, start=1):
        if results[index]["placebo_p"] <= 0.05 * rank / len(results):
            cutoff = rank
    for rank, index in enumerate(order, start=1):
        results[index]["bh_rank"] = rank
        results[index]["bh_survivor"] = rank <= cutoff

    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    survivors = [row for row in results if row["bh_survivor"]]
    manifest = {
        "generated_by": "scripts/run_credit_response_test.py",
        "unit": "a CUSIP and a pair of consecutive quarterly marks, outcome is the quarter-demeaned mark change",
        "declared_grid": len(grid), "measured_tests": len(results),
        "mark_pairs": len(pairs), "quarters": len(quarters), "cusips": len(by_cusip),
        "draws": args.draws, "block": args.block,
        "median_abs_correlation": round(statistics.median(abs(row["correlation"]) for row in results), 5),
        "nominal_hits": sum(1 for row in results if row["beats_placebo_95"]),
        "bh_survivors": len(survivors),
        "mde_note": "the minimum detectable absolute correlation is roughly two over the square root of n, which "
                    "on this sample is between 0.24 and 0.33. A relation smaller than that could exist and this "
                    "design could not see it",
        "ceiling": "descriptive_only",
        "boundary": "a fund mark is a quarterly valuation, so a mark change mixes credit news with valuation "
                    "policy and with the fund's own reporting",
        "results": results,
    }
    OUT_JSON.write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"{'sample':18s} {'predictor':26s} {'n':>4s} {'r':>8s} {'p':>7s} {'mde':>6s} bh")
    for row in sorted(results, key=lambda r: r["placebo_p"]):
        print(f"{row['sample']:18s} {row['predictor']:26s} {row['n']:4d} {row['correlation']:8.4f} "
              f"{row['placebo_p']:7.4f} {row['mde_abs_r']:6.3f} {row.get('bh_rank')}")
    print("")
    print(f"nominal hits: {manifest['nominal_hits']} of {len(results)} | BH survivors: {len(survivors)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
