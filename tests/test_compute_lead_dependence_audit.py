#!/usr/bin/env python3
"""Small deterministic checks for unique-quarter compute/capex audit rules."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_compute_lead_dependence import adjacent, next_quarter, quarter, spearman  # noqa: E402

assert quarter("2026-09") == "2026Q3"
assert adjacent("2025Q4", "2026Q1")
assert not adjacent("2025Q1", "2025Q3")
assert next_quarter("2025Q4") == "2026Q1"
assert round(spearman([1.0, 2.0, 3.0, 4.0], [4.0, 3.0, 2.0, 1.0]), 8) == -1.0
assert spearman([1.0, 2.0, 3.0], [3.0, 2.0, 1.0]) is None
print("compute lead dependence audit tests: 6/6 passed")
