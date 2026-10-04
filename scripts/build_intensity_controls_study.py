#!/usr/bin/env python3
"""Intensity under controls, and the conversion interaction.

Protocol: docs/plan/intensity-controls-study.md. Development only, both sealed windows spent. The claim
under test is a falsifiable association, not a charge: capex over revenue is investment intensity, and
this asks whether it predicts weaker relative returns once sector, growth, profitability and the common
investment factor are controlled, and whether the association is stronger when conversion fails.

    python3 scripts/build_intensity_controls_study.py
"""
from __future__ import annotations

import collections
import csv
import json
import math
import statistics
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
CAPEX = ROOT / "results" / "complex-capex-quarterly.csv"
REVENUE = ROOT / "results" / "complex-revenue-quarterly.csv"
ASSETS = ROOT / "results" / "complex-assets-quarterly.csv"
MARGINS = ROOT / "results" / "complex-margins-quarterly.csv"
RPO = ROOT / "results" / "rpo-events.csv"
PANEL = ROOT / "results" / "market-panel.json"
CACHE = ROOT / "results" / "bar-cache"
OUT = ROOT / "results" / "intensity-controls-study.json"
PREFERRED = "RevenueFromContractWithCustomerExcludingAssessedTax"
HORIZON = 20
MIN_NAMES = 8


def month_gap(a: str, b: str) -> int:
    return (int(a[:4]) - int(b[:4])) * 12 + (int(a[5:7]) - int(b[5:7]))


def latest_by_period(path: Path, concept: str | None = None) -> dict[str, dict[str, dict]]:
    out: dict[str, dict[str, dict]] = collections.defaultdict(dict)
    for row in csv.DictReader(path.open()):
        if concept and row.get("concept") != concept:
            continue
        ticker = row["ticker"]
        period = row["period_end"]
        current = out[ticker].get(period)
        if current is None or row.get("filed", "") > current.get("filed", ""):
            out[ticker][period] = row
    return out


def main() -> int:
    capex = latest_by_period(CAPEX)
    revenue_rows: dict[tuple[str, str], dict] = {}
    for row in csv.DictReader(REVENUE.open()):
        key = (row["ticker"], row["period_end"])
        current = revenue_rows.get(key)
        if current is None or (row["concept"] == PREFERRED and current["concept"] != PREFERRED):
            revenue_rows[key] = row
    revenue: dict[str, dict[str, dict]] = collections.defaultdict(dict)
    for (ticker, period), row in revenue_rows.items():
        revenue[ticker][period] = row
    assets: dict[str, dict[str, dict]] = collections.defaultdict(dict)
    for row in csv.DictReader(ASSETS.open()):
        assets[row["ticker"]].setdefault(row["period_end"], row)
    operating: dict[str, dict[str, dict]] = collections.defaultdict(dict)
    for row in csv.DictReader(MARGINS.open()):
        if row["concept"] == "OperatingIncomeLoss":
            operating[row["ticker"]].setdefault(row["period_end"], row)
    rpo: dict[str, list[dict]] = collections.defaultdict(list)
    for row in csv.DictReader(RPO.open()):
        try:
            row["_change"] = float(row["change"])
            row["_typical"] = float(row["typical_change"])
            row["_value"] = float(row["value"])
        except (ValueError, KeyError):
            continue
        rpo[row["ticker"]].append(row)
    for rows in rpo.values():
        rows.sort(key=lambda row: row.get("earliest_availability_utc", ""))

    prices = {}
    for path in sorted(CACHE.glob("*.json")):
        series = json.loads(path.read_text())
        if isinstance(series, dict):
            prices[path.stem] = series
    groups = json.loads(PANEL.read_text())["groups"]
    group_of, group_members = {}, {}
    for group, payload in groups.items():
        members = [series["ticker"] for series in payload["series"]]
        group_members[group] = members
        for ticker in members:
            group_of.setdefault(ticker, group)

    observations = []
    for ticker, quarters in sorted(capex.items()):
        if ticker not in prices:
            continue
        growth_history = collections.defaultdict(list)
        for period_end, cap_row in sorted(quarters.items()):
            rev_row = next((candidate for rev_end, candidate in revenue[ticker].items()
                            if abs(month_gap(rev_end, period_end)) <= 20), None)
            if not rev_row or float(rev_row["value_usd"]) <= 0 or float(cap_row["value_usd"]) <= 0:
                continue
            year_ago = f"{int(period_end[:4]) - 1}{period_end[4:]}"
            year_cap = next((candidate for cand_end, candidate in quarters.items()
                             if abs(month_gap(cand_end, year_ago)) <= 1), None)
            year_rev = next((candidate for cand_end, candidate in revenue[ticker].items()
                             if abs(month_gap(cand_end, year_ago)) <= 1), None)
            if not year_cap or not year_rev or float(year_cap["value_usd"]) <= 0 or float(year_rev["value_usd"]) <= 0:
                continue
            intensity = float(cap_row["value_usd"]) / float(rev_row["value_usd"])
            prior = float(year_cap["value_usd"]) / float(year_rev["value_usd"])
            filed = max(cap_row.get("filed", ""), rev_row.get("filed", ""))
            if intensity <= 0 or prior <= 0 or not filed:
                continue
            revenue_growth = math.log(float(rev_row["value_usd"]) / float(year_rev["value_usd"]))
            growth_history[ticker].append((filed, revenue_growth))
            asset_row = next((candidate for cand_end, candidate in assets[ticker].items()
                              if abs(month_gap(cand_end, period_end)) <= 20), None)
            asset_yoy = None
            if asset_row:
                prior_asset = next((candidate for cand_end, candidate in assets[ticker].items()
                                    if abs(month_gap(cand_end, year_ago)) <= 20), None)
                if prior_asset and float(prior_asset["value_usd"]) > 0:
                    asset_yoy = math.log(float(asset_row["value_usd"]) / float(prior_asset["value_usd"]))
            margin_row = next((candidate for cand_end, candidate in operating[ticker].items()
                               if abs(month_gap(cand_end, period_end)) <= 20), None)
            margin = None
            if margin_row and float(rev_row["value_usd"]) > 0:
                margin = float(margin_row["value_usd"]) / float(rev_row["value_usd"])
            trailing = [value for _, value in growth_history[ticker][-4:-1]]
            conversion_fail = None
            if len(trailing) >= 3:
                conversion_fail = 1 if revenue_growth < statistics.mean(trailing) else 0
            backlog_surprise = None
            for entry in reversed(rpo.get(ticker, [])):
                available = entry.get("earliest_availability_utc", "")
                if available and available[:10] <= filed and entry["_value"]:
                    backlog_surprise = (entry["_change"] - entry["_typical"]) / abs(entry["_value"])
                    break
            series = sorted(prices[ticker])
            start = next((date for date in series if date >= filed), None)
            if start is None:
                continue
            start_index = series.index(start)
            if start_index + HORIZON >= len(series):
                continue
            end = series[start_index + HORIZON]
            own = prices[ticker][end] / prices[ticker][start] - 1
            peers = []
            for member in group_members.get(group_of.get(ticker), []):
                if member == ticker or member not in prices:
                    continue
                member_series = sorted(prices[member])
                member_start = next((date for date in member_series if date >= filed), None)
                if member_start is None:
                    continue
                member_index = member_series.index(member_start)
                if member_index + HORIZON >= len(member_series):
                    continue
                peers.append(prices[member][member_series[member_index + HORIZON]] / prices[member][member_start] - 1)
            if len(peers) < 2:
                continue
            observations.append({"ticker": ticker, "group": group_of.get(ticker, "unlisted"),
                                 "quarter": filed[:7], "filed": filed,
                                 "intensity": math.log(intensity / prior), "revenue_growth": revenue_growth,
                                 "asset_growth": asset_yoy, "margin": margin,
                                 "conversion_fail": conversion_fail, "backlog_surprise": backlog_surprise,
                                 "excess": own - statistics.mean(peers)})
    print(f"observations {len(observations)} across {len({o['ticker'] for o in observations})} names, "
          f"{len({o['quarter'] for o in observations})} quarters")

    def standardise(rows: list[dict], keys: list[str]) -> np.ndarray:
        matrix = []
        for key in keys:
            values = np.array([row[key] for row in rows], dtype=float)
            sd = values.std()
            matrix.append((values - values.mean()) / sd if sd else values * 0)
        return np.column_stack(matrix)

    def fama_macbeth(rows: list[dict], predictors: list[str]) -> dict:
        by_quarter = collections.defaultdict(list)
        for row in rows:
            if all(row.get(key) is not None for key in predictors):
                by_quarter[row["quarter"]].append(row)
        coefficients = collections.defaultdict(list)
        quarters = 0
        for quarter, group in sorted(by_quarter.items()):
            if len(group) < MIN_NAMES:
                continue
            # group fixed effect: demean predictors and the outcome within group within the quarter
            adjusted = []
            for row in group:
                adjusted.append(dict(row))
            for key in predictors + ["excess"]:
                buckets = collections.defaultdict(list)
                for row in adjusted:
                    buckets[row["group"]].append(row[key])
                means = {bucket: statistics.mean(values) for bucket, values in buckets.items()}
                for row in adjusted:
                    row[key] = row[key] - means[row["group"]]
            x = standardise(adjusted, predictors)
            x = np.column_stack([np.ones(len(adjusted)), x])
            y = np.array([row["excess"] for row in adjusted], dtype=float)
            beta, *_ = np.linalg.lstsq(x, y, rcond=None)
            for index, key in enumerate(predictors, start=1):
                coefficients[key].append(beta[index])
            quarters += 1
        summary = {}
        for key, values in coefficients.items():
            if len(values) < 4:
                summary[key] = {"quarters": len(values), "status": "insufficient"}
                continue
            mean = statistics.mean(values)
            sd = statistics.pstdev(values)
            t_stat = mean / (sd / math.sqrt(len(values))) if sd else None
            summary[key] = {"quarters": len(values), "mean": round(mean, 5),
                            "t": round(t_stat, 2) if t_stat is not None else None,
                            "negative_share": round(sum(1 for value in values if value < 0) / len(values), 3)}
        return {"quarters": quarters, "coefficients": summary}

    predictors = ["intensity", "revenue_growth", "asset_growth", "margin"]
    report = {
        "status": "development only; both sealed windows spent; protocol docs/plan/intensity-controls-study.md",
        "observations": len(observations),
        "names": len({o["ticker"] for o in observations}),
        "horizon_days": HORIZON,
        "controls": fama_macbeth(observations, predictors),
        "univariate": fama_macbeth(observations, ["intensity"]),
    }
    # conversion interaction: revenue conversion failure and backlog conversion failure
    report["conversion_revenue"] = {
        "fail": fama_macbeth([o for o in observations if o["conversion_fail"] == 1], ["intensity"]),
        "pass": fama_macbeth([o for o in observations if o["conversion_fail"] == 0], ["intensity"]),
    }
    backlog_rows = [o for o in observations if o["backlog_surprise"] is not None]
    report["conversion_backlog"] = {
        "observations": len(backlog_rows),
        "names": len({o["ticker"] for o in backlog_rows}),
        "fail": fama_macbeth([o for o in backlog_rows if o["backlog_surprise"] < 0], ["intensity"]),
        "pass": fama_macbeth([o for o in backlog_rows if o["backlog_surprise"] >= 0], ["intensity"]),
    }
    # common investment factor: cross sectional mean intensity per quarter as its own predictor
    by_quarter = collections.defaultdict(list)
    for row in observations:
        by_quarter[row["quarter"]].append(row)
    means = {quarter: statistics.mean([row["intensity"] for row in group]) for quarter, group in by_quarter.items()}
    for row in observations:
        row["common_factor"] = means[row["quarter"]]
    report["with_common_factor"] = fama_macbeth(observations, ["intensity", "common_factor", "revenue_growth",
                                                               "asset_growth", "margin"])
    OUT.write_text(json.dumps(report, indent=1) + "\n")
    print("univariate:", json.dumps(report["univariate"]["coefficients"].get("intensity")))
    print("controls:", json.dumps(report["controls"]["coefficients"]))
    print("with common factor:", json.dumps(report["with_common_factor"]["coefficients"].get("intensity")))
    print("conversion (revenue) fail/pass:",
          json.dumps(report["conversion_revenue"]["fail"]["coefficients"].get("intensity")),
          json.dumps(report["conversion_revenue"]["pass"]["coefficients"].get("intensity")))
    print("conversion (backlog) n", report["conversion_backlog"]["observations"],
          "fail/pass:", json.dumps(report["conversion_backlog"]["fail"]["coefficients"].get("intensity")),
          json.dumps(report["conversion_backlog"]["pass"]["coefficients"].get("intensity")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
