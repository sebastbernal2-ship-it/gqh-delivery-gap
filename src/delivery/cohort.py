"""Match a promised vintage against a realization vintage.

A cohort is every unit promised in one EIA-860M vintage. For each unit, what actually
happened is read from a later vintage:

  in Operating             -> realized, actual operating month
  in Canceled or Postponed -> cancelled, mass reported separately
  still in Planned         -> not yet realized, censored and excluded from the delay
  absent from every sheet  -> unexplained, counted separately and never guessed

Nothing here fills a gap with information from a later date, because the realization
vintage is the only one that may report an outcome.
"""
from __future__ import annotations

import pandas as pd


def _key(frame: pd.DataFrame):
    return list(zip(frame["plant_id"].astype(str), frame["generator_id"].astype(str)))


def match_cohort(planned: pd.DataFrame, actual: pd.DataFrame, cancelled: pd.DataFrame,
                 still_planned: pd.DataFrame | None = None) -> dict:
    """Return matched pairs, cancellation mass, censoring and unexplained counts.

    still_planned is the realization vintage's Planned sheet. It is what separates a
    unit that has not been energized yet from a unit that disappeared without notice.
    """
    actual_by_key = {k: row for k, row in zip(_key(actual), actual.to_dict("records"))}
    cancelled_by_key = {k: row for k, row in zip(_key(cancelled), cancelled.to_dict("records"))}
    pending = still_planned if still_planned is not None else pd.DataFrame(
        columns=["plant_id", "generator_id"])
    planned_by_key = {k: row for k, row in zip(_key(pending), pending.to_dict("records"))}

    pairs = []
    cancelled_mw = 0.0
    n_censored = 0
    n_unexplained = 0
    regions: dict[str, dict] = {}

    for row in planned.to_dict("records"):
        key = (str(row["plant_id"]), str(row["generator_id"]))
        region = str(row.get("ba_code") or "UNKNOWN")
        bucket = regions.setdefault(region, {"mw_promised": 0.0, "mw_arrived": 0.0,
                                             "cancelled_mw": 0.0, "n_promised": 0})
        promised_mw = float(row.get("mw") or 0.0)
        bucket["mw_promised"] += promised_mw
        bucket["n_promised"] += 1

        if key in actual_by_key:
            hit = actual_by_key[key]
            realized = hit.get("operating_month_index")
            if realized is None or pd.isna(realized):
                n_censored += 1
                continue
            mw = hit.get("mw")
            mw = promised_mw if mw is None or pd.isna(mw) else float(mw)
            pairs.append({
                "promised": int(row["month_index"]),
                "realized": int(realized),
                "mw": mw,
                "ba_code": region,
                "technology": str(row.get("technology") or ""),
            })
            bucket["mw_arrived"] += mw
        elif key in cancelled_by_key:
            hit = cancelled_by_key[key]
            mw = hit.get("mw")
            mw = promised_mw if mw is None or pd.isna(mw) else float(mw)
            cancelled_mw += mw
            bucket["cancelled_mw"] += mw
        elif key in planned_by_key:
            n_censored += 1
        else:
            n_unexplained += 1

    return {
        "pairs": pairs,
        "cancelled_mw": cancelled_mw,
        "n_arrived": len(pairs),
        "n_censored": n_censored,
        "n_unexplained": n_unexplained,
        "by_region": regions,
    }


def select_window(planned: pd.DataFrame, start_index: int, end_index: int, report: bool = False):
    """Restrict a cohort to units whose promised arrival is inside the observable window.

    A unit promised after the window cannot be measured yet. Leaving it in would mix a
    measured delay with an unmeasurable promise and understate the delay.
    """
    mask = planned["month_index"].map(
        lambda value: value is not None and not pd.isna(value)
        and start_index <= int(value) <= end_index)
    selected = planned[mask].copy()
    if report:
        selected.attrs["excluded"] = int((~mask).sum())
        return selected
    return selected
