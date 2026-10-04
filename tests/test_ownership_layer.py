"""Behavior checks for the evidence-backed delivery ownership layer."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from strategy.ownership import build_review, top_entities, validate_review_row  # noqa: E402


EXPOSURE = [
    {"entity_name": "Alpha Project LLC", "slipped_mw": "100", "status": "unmatched"},
    {"entity_name": "Alpha Project LLC", "slipped_mw": "25", "status": "proposed"},
    {"entity_name": "Beta Power Co", "slipped_mw": "80", "status": "ambiguous"},
]


CROSSWALK = [{
    "entity_name": "Beta Power Co",
    "ticker": "BET",
    "cik": "123",
    "status": "verified",
    "weight": "1.0",
    "direction": "negative",
    "evidence": "FERC docket 123",
    "identity_vintage": "2024-01-01",
    "source_receipt": "https://example.test/ferc/123",
    "economic_channel": "rate base",
}]


top = top_entities(EXPOSURE, limit=2)
assert [(row["entity_name"], row["slipped_mw"]) for row in top] == [
    ("Alpha Project LLC", 125.0),
    ("Beta Power Co", 80.0),
]

review = build_review(EXPOSURE, CROSSWALK, limit=2)
assert review[0]["attribution_status"] == "unresolved"
assert review[0]["reason"] == "no evidence-backed crosswalk row"
assert review[1]["attribution_status"] == "verified"
assert review[1]["ticker"] == "BET"
assert validate_review_row(review[1]) is None

bad = dict(review[1], source_receipt="")
try:
    validate_review_row(bad)
except ValueError as exc:
    assert "source_receipt" in str(exc)
else:
    raise AssertionError("verified review row without a receipt was accepted")

print("ownership layer: 7/7 passed")
