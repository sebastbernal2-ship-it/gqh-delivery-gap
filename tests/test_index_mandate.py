"""Behavior checks for the public index mandate-flow event contract."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from strategy.index_mandate import event_eligibility, forced_shares, validate_event  # noqa: E402


BASE = {
    "event_id": "sp500-2020-09-21-AAA-add",
    "index_id": "sp500",
    "ticker": "AAA",
    "direction": "addition",
    "announcement_date": "2020-09-04",
    "effective_date": "2020-09-21",
    "availability_date": "2020-09-04",
    "source_url": "https://example.test/announcement.pdf",
    "evidence_status": "primary",
    "target_weight_change": "0.001",
    "tracking_assets": "1000000000",
    "fund_assets_date": "2020-09-03",
    "pre_event_price": "100",
    "price_date": "2020-09-18",
    "forced_shares": "10000",
    "exclusion_reason": "",
}

assert forced_shares(1_000_000_000, 0.001, 100) == 10_000
assert forced_shares(None, 0.001, 100) is None
assert event_eligibility(BASE, "2022-09-30") == (True, "eligible")
assert event_eligibility({**BASE, "announcement_date": ""}, "2022-09-30") == (
    False,
    "missing announcement date",
)
assert event_eligibility({**BASE, "availability_date": "2020-09-22"}, "2022-09-30") == (
    False,
    "evidence became available after the effective date",
)
assert event_eligibility({**BASE, "effective_date": "2022-10-01"}, "2022-09-30") == (
    False,
    "outside development window",
)
assert validate_event(BASE) is None

try:
    validate_event({**BASE, "direction": "hold"})
except ValueError as exc:
    assert "direction" in str(exc)
else:
    raise AssertionError("invalid direction was accepted")

print("index mandate: 9/9 passed")
