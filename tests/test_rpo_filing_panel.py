#!/usr/bin/env python3
"""Contracts for the filing-to-RPO join: strict clocks, nulls with flags, comparison integrity."""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from filing_specialist.rpo_model import FEATURES, prepare_rows  # noqa: E402
from filing_specialist.rpo_panel import FILING_FEATURES, Filing, augment_rows, filing_features  # noqa: E402

UTC = datetime.timezone.utc


def stamp(day: str, hour: int = 12) -> datetime.datetime:
    year, month, date = (int(part) for part in day.split("-"))
    return datetime.datetime(year, month, date, hour, tzinfo=UTC)


def filing(day: str, form: str = "8-K", items: str = "1.01") -> Filing:
    return Filing("T", "a", form, items, stamp(day))


def vintage(ticker: str, period_end: str, relative: str, availability: str) -> dict:
    return {"ticker": ticker, "period_end": period_end, "relative_surprise_pit": relative,
            "expectation_status": "measured", "availability": availability, "change": "10",
            "previous_value": "100", "history_count": "2", "history_span_days": "365",
            "group": "datacenter", "in_sealed_window": "False"}


def test_features_use_the_latest_filing_strictly_before_the_decision():
    items = [filing("2024-01-01", items="1.01"), filing("2024-03-01", form="10-Q", items=""),
             filing("2024-06-01", items="2.02,7.01")]
    features = filing_features(items, stamp("2024-06-01"))
    assert features["has_filing"] == 1.0
    assert features["form_is_8k"] == 0.0, "a filing at the decision instant is not usable"
    assert features["days_since_last_filing"] == (stamp("2024-06-01") - stamp("2024-03-01")).days
    later = filing_features(items, stamp("2024-06-02"))
    assert later["form_is_8k"] == 1.0 and later["has_item_202"] == 1.0 and later["has_item_701"] == 1.0
    assert later["filings_last_90d"] == 1.0, "the March filing is 93 days back, outside the window"


def test_a_ticker_without_filings_stays_null_with_a_flag():
    features = filing_features([], stamp("2024-06-01"))
    assert features["has_filing"] == 0.0
    assert all(features[name] is None for name in FILING_FEATURES if name != "has_filing")


def test_augmentation_preserves_rows_and_flags_missing_issuers():
    prepared, _ = prepare_rows([
        vintage("T", "2024-03-31", "0.05", "2024-05-01T00:00:00+00:00"),
        vintage("U", "2024-03-31", "0.05", "2024-05-01T00:00:00+00:00"),
    ])
    augmented, drops = augment_rows(prepared, {"T": [filing("2024-01-01")]})
    assert len(augmented) == len(prepared) == 2
    assert drops == {"no_filing_for_issuer": 1}
    by_ticker = {row["ticker"]: row for row in augmented}
    assert by_ticker["T"]["has_filing"] == 1.0
    assert by_ticker["U"]["has_filing"] == 0.0


def test_comparison_runs_with_and_without_filing_features():
    from filing_specialist.model import compare
    prepared = []
    for index in range(60):
        relative = ((index % 7) - 3) / 20.0
        prepared.append(vintage("T", f"20{20 + index // 4}-{(index % 4) * 3 + 3:02d}-30",
                                f"{relative:.4f}",
                                f"20{21 + index // 4}-01-{index % 27 + 1:02d}T12:00:00+00:00"))
    rows, _ = prepare_rows(prepared)
    filings = {"T": [filing(f"20{21 + index // 4}-01-{index % 27 + 1:02d}", "10-Q", "") for index in range(0, 60, 2)]}
    augmented, _ = augment_rows(rows, filings)
    history = compare(augmented, FEATURES, fraction=0.7)
    joined = compare(augmented, FEATURES + FILING_FEATURES, fraction=0.7)
    assert history["split"] == joined["split"]
    for report in (history, joined):
        assert report["softmax"]["log_loss"] > 0.0
        assert 0.0 <= report["softmax"]["accuracy"] <= 1.0


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} filing-join contract(s) held")
