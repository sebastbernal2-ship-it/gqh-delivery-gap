#!/usr/bin/env python3
"""Offline checks for negative controls and imagery metrics."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from imagery.metrics import classification_metrics  # noqa: E402
from strategy.controls import calendar_placebo, negative_control  # noqa: E402
rows = [{"event_id": "a", "entity_key": "issuer:PWR", "available_at": "2024-01-01", "usable_at": "2024-01-01"}, {"event_id": "b", "entity_key": "issuer:PWR", "available_at": "2024-01-02", "usable_at": "2024-01-02"}]
placebo = calendar_placebo(rows)
assert {row["available_at"] for row in placebo} == {"2024-01-01", "2024-01-02"}
assert negative_control(rows[0], unrelated=True)["exposure_allowed"] is False
metrics = classification_metrics([1, 1, 0, 0], [1, 0, 0, 1])
assert metrics["precision"] == 0.5 and metrics["recall"] == 0.5
print("controls and metrics: 3/3 passed")
