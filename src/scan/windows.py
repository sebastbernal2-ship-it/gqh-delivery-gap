"""The two declared windows, in one place, with the rule that separates them.

There are two studies here and each one owns its own history and its own holdout. Declaring them together,
before any compute association is measured, is what stops either from being chosen after the fact.

**Study one, the mechanism and the capacity strategy.** History from July 2015, holdout the most recent
twenty-four months of it, development to September 2022.

**Study two, the compute era.** History from June 2022, because that is where the compute price archive
begins, holdout the most recent fifth of that history, development June 2022 to March 2024.

**The firewall.** Nothing found in study two may change the design of study one. Study two's development
window overlaps study one's holdout, so without that rule a discovery in one would quietly spend the
other's held-out data.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Window:
    name: str
    history_start: str
    development_end: str
    sealed_start: str
    sealed_end: str
    what_it_is: str

    def in_development(self, month: str) -> bool:
        """A month counts for discovery only if it sits inside this study's development window."""
        return self.history_start <= month <= self.development_end

    def in_holdout(self, month: str) -> bool:
        return self.sealed_start <= month <= self.sealed_end


MECHANISM = Window(
    name="mechanism-and-strategy",
    history_start="2015-07",
    development_end="2022-09",
    sealed_start="2022-10",
    sealed_end="2024-09",
    what_it_is="the measured delivery mechanism and the capacity revision strategy, reported in the note",
)

COMPUTE_ERA = Window(
    name="compute-era",
    history_start="2022-06",
    development_end="2024-03",
    sealed_start="2024-04",
    sealed_end="2024-09",
    what_it_is="the compute price archive and what associates with it, a separate study",
)

WINDOWS = {window.name: window for window in (MECHANISM, COMPUTE_ERA)}

FIREWALL = ("Nothing measured in the compute era study may change the design of the mechanism and "
            "strategy study, because that study's holdout overlaps this one's development window.")


def get(name: str) -> Window:
    if name not in WINDOWS:
        raise KeyError(f"unknown window '{name}'. Declared windows: {sorted(WINDOWS)}")
    return WINDOWS[name]


def clip(series: dict[str, float], window: Window, include_holdout: bool = False) -> dict[str, float]:
    """Months inside the declared window. The holdout is excluded unless it is explicitly asked for."""
    if include_holdout:
        return {month: value for month, value in series.items()
                if window.history_start <= month <= window.sealed_end}
    return {month: value for month, value in series.items() if window.in_development(month)}


def describe() -> str:
    lines = [f"{'study':22s} {'history':>18s} {'development to':>16s} {'sealed':>18s}"]
    for window in WINDOWS.values():
        lines.append(f"{window.name:22s} {window.history_start + ' to ' + window.sealed_end:>18s} "
                     f"{window.development_end:>16s} "
                     f"{window.sealed_start + ' to ' + window.sealed_end:>18s}")
    lines.append("")
    lines.append(FIREWALL)
    return "\n".join(lines)
