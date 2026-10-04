#!/usr/bin/env python3
"""Report the recorded capacity strategy run in its declared windows.

Reads the two artifacts the frozen run already wrote:

  results/capacity-strategy.csv   the development rows (2016-07 to 2022-08, n=74)
  results/sealed-strategy.txt     the opened run's summary (n=98, the full history)

and reports in-sample and out-of-sample separately, as the track brief requires.
The out-of-sample means are implied from the recorded full-run and development
tables: mean_sealed = (n_full * mean_full - n_dev * mean_dev) / n_sealed. No signal
is re-run, no variant is selected, and the spent holdout is not opened again. The
frozen script's last change predates the sealed run, and this file is a reporter.

Writes results/capacity-strategy-summary.json and results/capacity-equity.svg.
"""
from __future__ import annotations

import csv
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from run_capacity_strategy import _annualised, _curve, _drawdown, _sharpe, net_return  # noqa: E402

CSV_PATH = ROOT / "results" / "capacity-strategy.csv"
TXT_PATH = ROOT / "results" / "sealed-strategy.txt"
OUT_PATH = ROOT / "results" / "capacity-strategy-summary.json"
SVG_PATH = ROOT / "results" / "capacity-equity.svg"

SIGNALS = ("next_year", "current_and_next", "three_year")
DEVELOPMENT = ("2016-07", "2022-08")
SEALED_FIRST, SEALED_N = "2022-10", 24

FULL_ROW = re.compile(r"^(\S+)\s+(\d+)\s+(\d+)\s+(-?[\d.]+)%\s+(-?[\d.]+)%\s+(-?[\d.]+)%\s+"
                      r"(-?[\d.]+)%\s+(-?[\d.]+)\s+(-?[\d.]+)%\s+(\d+)%$")
PLATEAU_ROW = re.compile(r"^\s{2}(all|median|top third)\s+(\d+)\s+(-?[\d.]+)%\s+(-?[\d.]+)%\s+"
                         r"(-?[\d.]+)%\s+(-?[\d.]+)$")


def development_stats(rows: list[dict]) -> dict:
    flips = sum(1 for a, b in zip(rows, rows[1:]) if a["position"] != b["position"])
    turnover = (len(rows) + flips) / len(rows)
    gross = [float(row["gross"]) for row in rows]
    net10 = [net_return(g, turnover * 10, turnover * 10) for g in gross]
    net20 = [net_return(g, turnover * 20, turnover * 20) for g in gross]
    equity10 = _curve(net10)
    return {
        "first": rows[0]["vintage"],
        "last": rows[-1]["vintage"],
        "n": len(rows),
        "flips": flips,
        "turnover": turnover,
        "gross_mean": statistics.mean(gross),
        "net10_mean": statistics.mean(net10),
        "net20_mean": statistics.mean(net20),
        "annualised_net10": _annualised(net10),
        "sharpe_net10": _sharpe(net10),
        "max_drawdown_net10": _drawdown(equity10),
        "hit_rate_net10": sum(1 for value in net10 if value > 0) / len(net10),
        "months": [row["vintage"] for row in rows],
        "equity_net10": equity10,
        "equity_net20": _curve(net20),
    }


def full_run_stats() -> tuple[dict, list[dict]]:
    text = TXT_PATH.read_text()
    found: dict[str, dict] = {}
    plateau: list[dict] = []
    for line in text.splitlines():
        match = FULL_ROW.match(line.strip())
        if match and match.group(1) in SIGNALS:
            found[match.group(1)] = {
                "n": int(match.group(2)), "flips": int(match.group(3)),
                "gross_mean": float(match.group(4)) / 100,
                "net10_mean": float(match.group(5)) / 100,
                "net20_mean": float(match.group(6)) / 100,
                "annualised_net10": float(match.group(7)) / 100,
                "sharpe_net10": float(match.group(8)),
                "max_drawdown_net10": float(match.group(9)) / 100,
                "hit_rate_net10": float(match.group(10)) / 100,
            }
        plateau_match = PLATEAU_ROW.match(line)
        if plateau_match:
            plateau.append({"cut": plateau_match.group(1), "n": int(plateau_match.group(2)),
                            "gross_mean": float(plateau_match.group(3)) / 100,
                            "net10_mean": float(plateau_match.group(4)) / 100,
                            "net20_mean": float(plateau_match.group(5)) / 100,
                            "sharpe_net10": float(plateau_match.group(6))})
    missing = [signal for signal in SIGNALS if signal not in found]
    if missing:
        raise SystemExit(f"could not read the recorded full run for: {', '.join(missing)}")
    return found, plateau


def imply_sealed(development: dict, full: dict) -> dict:
    """Isolate the opened window's mean contribution from two recorded runs."""
    n_sealed = full["n"] - development["n"]
    return {
        "n": n_sealed,
        "gross_mean": (full["n"] * full["gross_mean"] - development["n"] * development["gross_mean"]) / n_sealed,
        "net10_mean": (full["n"] * full["net10_mean"] - development["n"] * development["net10_mean"]) / n_sealed,
        "net20_mean": (full["n"] * full["net20_mean"] - development["n"] * development["net20_mean"]) / n_sealed,
        "method": "mean = (n_full * mean_full - n_dev * mean_dev) / n_sealed, from the two recorded runs",
        "row_path": "not archived by the frozen script; not reconstructed",
    }


def equity_svg(series: dict[str, list[float]], months: list[str]) -> str:
    width, height = 640, 170
    left, right, top, bottom = 42, 12, 10, 26
    values = [value for name in ("next_year", "current_and_next") for value in series[name]]
    low, high = min(values), max(values)
    span = high - low or 1.0
    count = len(months) - 1 or 1

    def x(index: int) -> float:
        return left + (width - left - right) * index / count

    def y(value: float) -> float:
        return top + (height - top - bottom) * (1 - (value - low) / span)

    def polyline(values_: list[float]) -> str:
        points = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(values_))
        return f'<polyline points="{points}" fill="none" stroke-width="1.6"/>'

    grid = []
    for fraction in (0.0, 0.5, 1.0):
        level = high - span * fraction
        y_value = top + (height - top - bottom) * fraction
        grid.append(f'<line x1="{left}" y1="{y_value:.1f}" x2="{width - right}" y2="{y_value:.1f}" '
                    f'stroke="#ddd" stroke-width="0.6"/>')
        grid.append(f'<text x="{left - 5}" y="{y_value + 2.6:.1f}" font-size="9" text-anchor="end" '
                    f'fill="#555">{level:.2f}</text>')
    labels = (f'<text x="{left}" y="{height - 8}" font-size="9" fill="#555">{months[0]}</text>'
              f'<text x="{width - right}" y="{height - 8}" font-size="9" text-anchor="end" '
              f'fill="#555">{months[-1]}</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="100%" role="img" aria-label="development-window equity, net of costs">'
            + "".join(grid)
            + f'<g stroke="#1a4a7a">{polyline(series["next_year"])}</g>'
            + f'<g stroke="#b06a00">{polyline(series["current_and_next"])}</g>'
            + labels
            + f'<text x="{left}" y="{top + 10}" font-size="9" fill="#1a4a7a">next-year signal</text>'
            + f'<text x="{left + 110}" y="{top + 10}" font-size="9" fill="#b06a00">current-and-next</text>'
            + "</svg>\n")


def main() -> int:
    rows = [row for row in csv.DictReader(CSV_PATH.open())]
    if not rows:
        raise SystemExit(f"{CSV_PATH} is empty; run the development pass first")
    development = {signal: development_stats([row for row in rows if row["signal"] == signal])
                   for signal in SIGNALS}
    full, plateau = full_run_stats()
    report = {
        "generated": __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        .isoformat(timespec="seconds"),
        "sources": {
            "development_rows": "results/capacity-strategy.csv",
            "opened_run_summary": "results/sealed-strategy.txt",
        },
        "windows": {
            "development": {"first": DEVELOPMENT[0], "last": DEVELOPMENT[1],
                            "n": development["next_year"]["n"]},
            "sealed": {"first": SEALED_FIRST, "n": SEALED_N,
                       "status": "opened once by the owner; reported, not re-opened"},
        },
        "signals": {
            signal: {"development": development[signal], "full_run": full[signal],
                     "implied_sealed": imply_sealed(development[signal], full[signal])}
            for signal in SIGNALS
        },
        "plateau_full_run": plateau,
    }
    OUT_PATH.write_text(json.dumps(report, indent=1) + "\n")
    SVG_PATH.write_text(equity_svg(
        {signal: development[signal]["equity_net10"] for signal in SIGNALS},
        development["next_year"]["months"]))
    print(f"wrote {OUT_PATH.relative_to(ROOT)} and {SVG_PATH.relative_to(ROOT)}")
    for signal in SIGNALS:
        dev, imp, full_stats = development[signal], report["signals"][signal]["implied_sealed"], full[signal]
        print(f"  {signal:17s} dev n={dev['n']:>3d} net10={dev['net10_mean']:+.4f} "
              f"net20={dev['net20_mean']:+.4f} | sealed n={imp['n']:>3d} "
              f"net10={imp['net10_mean']:+.4f} net20={imp['net20_mean']:+.4f} | "
              f"full net10={full_stats['net10_mean']:+.4f} net20={full_stats['net20_mean']:+.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
