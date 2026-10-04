#!/usr/bin/env python3
"""Exact fixed-point and nanosecond conversion tests for the HL fixture adapter."""
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_hyperliquid_fixture import (  # noqa: E402
    milliseconds_to_ns,
    rate,
    rfc3339_ns,
    scaled_integer,
    seconds_to_ns,
    ticks,
    units,
)


assert ticks("1.00005") == 10_001  # positive tie rounds away from zero
assert ticks("-1.00005") == -10_001
assert units(Decimal("0.0000005")) == 1
assert units("-0.0000005") == -1
assert rate("-0.000000005") == -1  # negative rate tie is away from zero
assert seconds_to_ns("1700000000.123456789") == 1_700_000_000_123_456_789
assert milliseconds_to_ns("1700000000123.456789") == 1_700_000_000_123_456_789
assert rfc3339_ns(seconds_to_ns("1700000000.123456789")) == "2023-11-14T22:13:20.123456789Z"
assert rfc3339_ns(seconds_to_ns("1.0000000005")) == "1970-01-01T00:00:01.000000001Z"
assert rfc3339_ns(seconds_to_ns("-0.0000000005")) == "1969-12-31T23:59:59.999999999Z"

print("Hyperliquid fixture exact conversion tests: 10/10 passed")
