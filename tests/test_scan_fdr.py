#!/usr/bin/env python3
"""Offline tests for the false discovery rate control."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from scan.fdr import benjamini_hochberg, p_values, report  # noqa: E402

failures: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        failures.append(f"{name}: got {got!r}, want {want!r}")


rows = [
    {"pair": "strong", "coverage": "measured", "placebo_percentile": "1.00"},
    {"pair": "weak", "coverage": "measured", "placebo_percentile": "0.50"},
    {"pair": "skipped", "coverage": "too few months", "placebo_percentile": "1.00"},
    {"pair": "missing", "coverage": "measured", "placebo_percentile": ""},
]
values = p_values(rows)
check("only measured pairs with a percentile get a p-value", len(values), 2)
check("a perfect percentile gives a zero p-value", dict(values)["strong"], 0.0)
check("a middle percentile gives a middle p-value", dict(values)["weak"], 0.5)

# Twenty pairs, one clearly real: only it should survive, and the count must fall as the pool grows.
clean = [("real", 0.0005)] + [(f"noise{i}", 0.3 + i * 0.01) for i in range(19)]
result = benjamini_hochberg(clean, 0.10)
check("the real pair survives", result["survivors"], ["real"])
check("the pool size is reported", result["tested"], 20)

# The same evidence inside a bigger searched space must not survive as easily. That is the whole point of
# controlling the rate rather than counting crossings: at 220 pairs the first rank needs p <= 0.00045.
big = clean + [(f"extra{i}", 0.4 + i * 0.001) for i in range(200)]
check("a larger search space is reported as larger", benjamini_hochberg(big, 0.10)["tested"], 220)
check("the same evidence stops surviving once the space is large enough",
      benjamini_hochberg(big, 0.10)["survivors"], [])
decisive = [("real", 0.00001)] + [(f"noise{i}", 0.4 + i * 0.001) for i in range(200)]
check("evidence strong enough still survives in a large space",
      benjamini_hochberg(decisive, 0.10)["survivors"], ["real"])

nothing = [(f"noise{i}", 0.4 + i * 0.001) for i in range(50)]
check("a pool of noise yields no survivors", benjamini_hochberg(nothing, 0.10)["survivors"], [])
check("an empty pool is handled", benjamini_hochberg([], 0.10)["survivors"], [])
check("an empty pool reports zero tested", benjamini_hochberg([], 0.10)["tested"], 0)

text = report(nothing)
check("the report says a threshold count is not evidence",
      "is not evidence" in text, True)
check("the report states the rate", "false discovery rate of 10%" in text, True)

if failures:
    print("\n".join(f"  FAIL {f}" for f in failures))
    print(f"\n{15 - len(failures)}/15 passed")
    raise SystemExit(1)
print("\n15/15 passed")
