#!/usr/bin/env python3
"""The options leg: implied volatility against realized, declared before it is measured.

Why this is the cheapest new information in the effort: implied volatility is a risk price, nobody else in this
work has looked at it, and the capture is free going forward. The limitation is stated up front and it is
binding: there is one snapshot, so nothing here is a time series. What a single snapshot permits is a
cross section, and that is what this declares.

Declaration, frozen before any statistic.

- **Universe.** The twelve names in the first snapshot: DLR, EQIX, IRM, AMT, PWR, ETN, VRT, GEV, CEG, VST, NRG,
  CRWV.
- **Measures, three per name.**
  1. **Variance risk premium**: at the money implied volatility at the nearest expiry minus realized close to
     close volatility over the trailing 21 trading days.
  2. **Term structure slope**: at the money implied volatility at the longest captured expiry minus the nearest.
  3. **Skew**: the implied volatility of the put whose strike is nearest ten percent below spot minus the call
     nearest ten percent above.
- **Grid: twelve names across three measures, plus three group means, so thirty nine numbers.** The grid is
  printed before any of them is computed.
- **Group split.** Data center and interconnection names, DLR, EQIX, IRM, AMT, CRWV, against the power and
  equipment names, PWR, ETN, VRT, GEV, CEG, VST, NRG.
- **Ceiling.** Descriptive only. One snapshot cannot support a claim about a premium being earned over time, and
  a cross section of twelve names cannot separate a signal from a sector tilt.
- **Falsifier.** If the variance risk premium is negative for most names, or the group means are inside the
  cross sectional spread, the snapshot says nothing about a compensation for risk at this date.

Usage:
    python3 scripts/run_implied_vol_test.py
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOTS = ROOT / "results" / "option-snapshots"
PANEL = ROOT / "results" / "market-panel.json"
BARS = ROOT / "results" / "bar-cache"
OUT_CSV = ROOT / "results" / "implied-vol-test.csv"
OUT_JSON = ROOT / "results" / "implied-vol-test.json"

DATA_CENTER = {"DLR", "EQIX", "IRM", "AMT", "CRWV"}


def atm_iv(rows: list[dict], spot: float, expiry: str, side: str = "call") -> float | None:
    candidates = [row for row in rows if row["expiry"] == expiry and row["side"] == side and row.get("implied_vol")]
    if not candidates or not spot:
        return None
    nearest = min(candidates, key=lambda row: abs(float(row["strike"]) - spot))
    return float(nearest["implied_vol"])


def wing_iv(rows: list[dict], spot: float, expiry: str, side: str, target: float) -> float | None:
    candidates = [row for row in rows if row["expiry"] == expiry and row["side"] == side and row.get("implied_vol")]
    if not candidates or not spot:
        return None
    nearest = min(candidates, key=lambda row: abs(float(row["strike"]) - spot * target))
    return float(nearest["implied_vol"])


def realized_vol(ticker: str, days: int = 21) -> float | None:
    path = BARS / f"{ticker}.json"
    if not path.exists():
        return None
    closes = json.loads(path.read_text())
    stamps = sorted(closes)[-days - 1:]
    values = [float(closes[stamp]) for stamp in stamps]
    if len(values) < 5:
        return None
    returns = [values[i] / values[i - 1] - 1.0 for i in range(1, len(values))]
    return statistics.pstdev(returns) * (252 ** 0.5)


def main() -> int:
    snapshots = sorted(SNAPSHOTS.glob("snapshot-*.json"))
    if not snapshots:
        raise SystemExit("no snapshot to read")
    snapshot = json.loads(snapshots[-1].read_text())
    names = snapshot["names"]
    names_count, measures = len(names), 3
    print(f"declared grid: {names_count} names x {measures} measures + 3 group means = "
          f"{names_count * measures + 3} numbers")
    print(f"snapshot: {snapshot['taken_utc']} | expiries captured per name: up to 4")

    rows: list[dict] = []
    for ticker, entry in names.items():
        chain = entry.get("chain") or []
        spot = entry.get("underlying") or 0.0
        expiries = entry.get("expiries") or []
        if not chain or not expiries or not spot:
            rows.append({"ticker": ticker, "group": "data_center" if ticker in DATA_CENTER else "power_equipment",
                         "atm_iv": "", "realized_21d": "", "variance_risk_premium": "",
                         "term_slope": "", "skew_10pct": "", "note": "no usable chain"})
            continue
        near, far = expiries[0], expiries[-1]
        atm = atm_iv(chain, spot, near) or 0.0
        realized = realized_vol(ticker) or 0.0
        far_atm = atm_iv(chain, spot, far)
        put_wing = wing_iv(chain, spot, near, "put", 0.90)
        call_wing = wing_iv(chain, spot, near, "call", 1.10)
        rows.append({
            "ticker": ticker, "group": "data_center" if ticker in DATA_CENTER else "power_equipment",
            "spot": round(spot, 2), "nearest_expiry": near,
            "atm_iv": round(atm, 4), "realized_21d": round(realized, 4),
            "variance_risk_premium": round(atm - realized, 4),
            "term_slope": round((far_atm - atm), 4) if far_atm is not None else "",
            "skew_10pct": round((put_wing - call_wing), 4) if put_wing is not None and call_wing is not None else "",
            "note": "",
        })

    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    def mean(key: str, group: str | None = None) -> float | None:
        values = [float(row[key]) for row in rows
                  if row.get(key) not in ("", None) and (group is None or row["group"] == group)]
        return round(statistics.fmean(values), 4) if values else None

    premiums = [float(row["variance_risk_premium"]) for row in rows if row.get("variance_risk_premium") not in ("", None)]
    manifest = {
        "generated_by": "scripts/run_implied_vol_test.py",
        "snapshot": snapshot["taken_utc"], "names": names_count,
        "declared_numbers": names_count * measures + 3,
        "variance_risk_premium_mean": mean("variance_risk_premium"),
        "variance_risk_premium_mean_data_center": mean("variance_risk_premium", "data_center"),
        "variance_risk_premium_mean_power_equipment": mean("variance_risk_premium", "power_equipment"),
        "names_with_positive_premium": sum(1 for value in premiums if value > 0),
        "names_measured": len(premiums),
        "term_slope_mean": mean("term_slope"), "skew_mean": mean("skew_10pct"),
        "ceiling": "descriptive_only",
        "binding_limit": "one snapshot is a cross section and cannot support a statement about a premium earned "
                         "over time. Any history this archive has begins at its first snapshot",
        "falsifier": "if the premium is negative for most names, or the two group means sit inside the cross "
                     "sectional spread, the snapshot says nothing about compensation for risk at this date",
        "rows": rows,
    }
    OUT_JSON.write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"{'ticker':7s} {'group':16s} {'spot':>8s} {'ATM IV':>8s} {'realized':>9s} {'premium':>8s} "
          f"{'slope':>8s} {'skew':>8s}")
    for row in sorted(rows, key=lambda r: (str(r["group"]), r["ticker"])):
        print(f"{row['ticker']:7s} {row['group']:16s} {str(row.get('spot', '')):>8s} {str(row['atm_iv']):>8s} "
              f"{str(row['realized_21d']):>9s} {str(row['variance_risk_premium']):>8s} "
              f"{str(row['term_slope']):>8s} {str(row['skew_10pct']):>8s}")
    print("")
    print(f"mean premium {manifest['variance_risk_premium_mean']} | data center "
          f"{manifest['variance_risk_premium_mean_data_center']} | power and equipment "
          f"{manifest['variance_risk_premium_mean_power_equipment']}")
    print(f"names with a positive premium: {manifest['names_with_positive_premium']} of "
          f"{manifest['names_measured']} | mean term slope {manifest['term_slope_mean']} | "
          f"mean skew {manifest['skew_mean']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
