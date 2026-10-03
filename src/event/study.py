"""Event windows around a firm's own disclosed revision, with the rules the rubric demands.

Three rules, all structural rather than stylistic:

1. **Lag every signal.** A revision becomes usable at its availability timestamp. The fill is the close
   of the first session strictly *after* that moment, and the return starts there. Same-bar fills are
   refused by construction.
2. **Abnormal, not raw.** Market and sector movement is the first alternative explanation, so the raw
   return is reported next to a benchmark-adjusted one.
3. **The horizon is a plateau, not a choice.** Several horizons are measured and all are reported. The
   primary horizon has to be declared before the sealed test, and picking the best cell afterwards would
   be tuning, so nothing here elects a winner.
"""
from __future__ import annotations

import datetime as dt
import statistics
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


def sessions(bar_index, after: dt.datetime | dt.date | str):
    """Trading sessions strictly after a moment. This is the lag rule, in one place."""
    moment = _as_datetime(after)
    later = [stamp for stamp in bar_index if _as_datetime(stamp) > moment]
    return later


def _as_datetime(value):
    if isinstance(value, dt.datetime):
        return value if value.tzinfo else value.replace(tzinfo=dt.timezone.utc)
    if isinstance(value, dt.date):
        return dt.datetime(value.year, value.month, value.day, 23, 59, tzinfo=dt.timezone.utc)
    text = str(value).strip()
    if not text:
        raise ValueError("empty timestamp")
    parsed = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)


def window_return(closes: dict, bar_index: list, after, horizon: int) -> float | None:
    """Close-to-close return from the first session after the signal, over ``horizon`` sessions."""
    later = sessions(bar_index, after)
    if len(later) < horizon + 1:
        return None
    start, end = later[0], later[horizon]
    first, last = closes.get(start), closes.get(end)
    if not first or not last:
        return None
    return last / first - 1.0


def abnormal(firm: float | None, benchmark: float | None) -> float | None:
    if firm is None or benchmark is None:
        return None
    return firm - benchmark


def surprise(value: float, history: list[float]) -> float | None:
    """A revision against what this firm usually reports, which is a declared, simple expectation.

    A fall in remaining obligations is not automatically bad news: work gets delivered and the balance
    falls. So the raw change is reported beside the change relative to the firm's own typical change.
    """
    if not history:
        return None
    return value - statistics.median(history)


def revision_surprise(current_value: float | None, prior_expectation: float | None) -> float | None:
    """The primary signal: current public value minus the earlier public expectation."""
    if current_value is None or prior_expectation is None:
        return None
    return float(current_value) - float(prior_expectation)


def summarise(rows: list[dict], horizons: list[int]) -> str:
    lines = []
    lines.append(f"events: {len(rows)}")
    lines.append("")
    lines.append(f"{'horizon':>7s} {'n':>4s} {'mean raw':>10s} {'mean abnormal':>14s} {'median abnormal':>16s}")
    for horizon in horizons:
        pairs = [(r[f"raw_{horizon}"], r[f"abnormal_{horizon}"])
                 for r in rows
                 if r.get(f"abnormal_{horizon}") is not None]
        if not pairs:
            lines.append(f"{horizon:>7d} {0:>4d} {'n/a':>10s} {'n/a':>14s} {'n/a':>16s}")
            continue
        raws = [p[0] for p in pairs]
        abnormals = [p[1] for p in pairs]
        lines.append(f"{horizon:>7d} {len(pairs):>4d} {statistics.mean(raws):>9.2%} "
                     f"{statistics.mean(abnormals):>13.2%} {statistics.median(abnormals):>15.2%}")
    lines.append("")
    lines.append("The whole plateau is reported. Electing the best horizon after seeing these numbers")
    lines.append("would be tuning on the development window, so no horizon is chosen here.")
    return "\n".join(lines)
