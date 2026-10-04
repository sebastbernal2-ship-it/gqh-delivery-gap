#!/usr/bin/env python3
"""Contracts for the council sleeve: point-in-time peer features and a fair weight grid."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "hpc" / "probabilistic-council"))
from run_council_sleeve import PEER_FEATURES, pool_grid, peer_momentum  # noqa: E402


def rows() -> list[dict]:
    return [
        {"ticker": "A", "group_name": "hyperscaler", "label_available": "2020-02-01T23:59:59+00:00",
         "label_relative_surprise": "0.10"},
        {"ticker": "B", "group_name": "hyperscaler", "label_available": "2020-03-01T23:59:59+00:00",
         "label_relative_surprise": "0.30"},
        {"ticker": "A", "group_name": "hyperscaler", "label_available": "2020-04-01T23:59:59+00:00",
         "label_relative_surprise": "0.50"},
        {"ticker": "C", "group_name": "power", "label_available": "2020-04-01T23:59:59+00:00",
         "label_relative_surprise": "0.70"},
    ]


def test_peer_momentum_reads_only_strictly_prior_disclosures_of_the_declared_group():
    features = peer_momentum(rows())
    first, second, third, fourth = features
    assert first["peer_coverage"] == 0.0 and first["peer_last_surprise"] == 0.0
    assert second["peer_last_surprise"] == 0.10                    # A's February event, same group
    assert third["peer_last_surprise"] == 0.30                     # B, not A's own history
    assert third["peer_mean_surprise_3"] == 0.20                   # mean of 0.10 and 0.30
    assert fourth["peer_last_surprise"] == 0.0                     # a different peer group entirely
    assert set(features[0]) == set(PEER_FEATURES)


def test_pool_grid_offers_the_corners_and_never_the_empty_combination():
    grid = pool_grid(("a", "b", "c"))
    assert {"a": 1.0, "b": 0.0, "c": 0.0} in grid                 # a single specialist is allowed
    assert {"a": 0.0, "b": 0.0, "c": 0.0} not in grid
    assert all(abs(sum(weights.values()) - 1.0) < 1e-9 for weights in grid)


def test_split_conviction_takes_the_specialists_direction_and_the_councils_size():
    from run_council_sleeve import split_conviction
    # a weak council and a strongly bullish specialist: the direction is the specialist's
    assert split_conviction(2.00, 3.00) is None     # a neutral council means no trade at all
    assert split_conviction(2.50, 3.00) == 0.25
    # a strongly bearish council with a mildly bearish specialist: the magnitude is the council's
    assert split_conviction(0.50, 1.50) == -0.75
    assert split_conviction(2.00, 1.00) is None      # a neutral council means no trade at all


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok:", test.__name__)
    print(f"{len(tests)} council-sleeve contract(s) held")
