#!/usr/bin/env python3
"""Offline tests for the compute price consumer. No network, no database."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from scan.compute import ENV_VARIABLE, family_index, load_direct, load_export, series  # noqa: E402

failures: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        failures.append(f"{name}: got {got!r}, want {want!r}")


tmp = Path(tempfile.mkdtemp(prefix="compute-"))
export = tmp / "compute-price-monthly.csv"
export.write_text(
    "month,family,quotes,median_usd_per_instance_hour,zones\n"
    "2022-06-01,g5,120,1.20,2\n"
    "2022-06-01,p4,80,3.60,2\n"
    "2022-07-01,g5,130,1.50,2\n"
    "2022-07-01,p4,90,3.60,2\n"
    "2022-08-01,g5,140,,2\n"
)

loaded = load_export(export)
check("both families are read", sorted(loaded), ["g5", "p4"])
check("a blank median is skipped, not guessed", loaded["g5"], {"2022-06": 1.2, "2022-07": 1.5})
check("the second family is read", loaded["p4"], {"2022-06": 3.6, "2022-07": 3.6})

index = family_index(loaded)
check("the index has one value per month with at least two families", sorted(index), ["2022-06", "2022-07"])
check("each family is rebased, so movement decides and not the price level",
      round(index["2022-06"], 4), 1.0)
check("a family that did not move holds the index down",
      round(index["2022-07"], 4), round((1.5 / 1.2 + 1.0) / 2, 4))

check("a missing export returns nothing rather than raising",
      load_export(tmp / "absent.csv"), {})

saved = os.environ.pop(ENV_VARIABLE, None)
direct, status = load_direct()
check("with no connection variable the direct route declines", direct, {})
check("the status explains why without quoting anything",
      "is not set" in status or "not installed" in status, True)
check("the status never contains a connection string", "://" not in status, True)
if saved is not None:
    os.environ[ENV_VARIABLE] = saved

data, line = series()
check("the series route reports itself", isinstance(line, str), True)
check("no credential can appear in the status line", "://" not in line, True)

if failures:
    print("\n".join(f"  FAIL {f}" for f in failures))
    print(f"\n{13 - len(failures)}/13 passed")
    raise SystemExit(1)
print("\n13/13 passed")
