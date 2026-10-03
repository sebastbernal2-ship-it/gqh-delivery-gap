#!/usr/bin/env python3
"""Tests for the delivery-gap metrics.

Run: python3 tests/test_delivery_metrics.py

The state variable is the transport cost between the promised delivery-date
distribution and the realized one, in months, MW weighted. In one dimension the
optimal transport cost has a closed form, so these are checked against numbers
that can be computed by hand.

Conventions:
  delay_months = realized_month_index - promised_month_index
  a positive delay means the unit arrived later than promised
  W1 = MW weighted mean absolute delay
  W2 = sqrt(MW weighted mean squared delay)
  quantiles use the midpoint-position linear convention: each unit sits at
  (weight before it + half its own weight) / total, and the quantile interpolates
  between neighbours. With equal weights that is the usual interpolated
  percentile, so the median of {0, 4} is 2.0 and the p90 of {0..9} is 8.5.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from delivery.metrics import transport_cost  # noqa: E402


def pair(promised, realized, mw=100.0):
    return {"promised": promised, "realized": realized, "mw": mw}


def main() -> int:
    failures = []

    def check(name, got, want, tol=1e-9):
        ok = abs(got - want) <= tol if isinstance(want, float) else got == want
        if not ok:
            failures.append(name)
            print(f"FAIL {name}: got {got!r} want {want!r}")
        else:
            print(f"ok   {name}")

    # Two units, delays of 0 and +4 months, equal MW.
    r = transport_cost([pair(10, 10), pair(10, 14)])
    check("w1 unit mix", r["w1_months"], 2.0)
    check("w2 unit mix", r["w2_months"], (8.0) ** 0.5)
    check("median delay", r["median_delay_months"], 2.0)
    check("n_units", r["n_units"], 2)
    check("mw tracked", r["mw_total"], 200.0)

    # MW weighting must move the answer: the long delay is tiny.
    r = transport_cost([pair(10, 10, 1000.0), pair(10, 14, 1.0)])
    check("w1 mw weighted", r["w1_months"], 4.0 / 1001.0, tol=1e-6)

    # Early arrivals count too, as absolute magnitude.
    r = transport_cost([pair(10, 8), pair(10, 12)])
    check("w1 early and late", r["w1_months"], 2.0)

    # A cohort with no delay at all.
    r = transport_cost([pair(5, 5), pair(6, 6)])
    check("no delay w1", r["w1_months"], 0.0)
    check("no delay median", r["median_delay_months"], 0.0)

    # Cancellation mass is reported separately, not folded into the delay.
    r = transport_cost([pair(10, 10)], canceled_mw=100.0)
    check("cancel share", r["cancelled_share"], 0.5)
    check("cancel share leaves delay alone", r["w1_months"], 0.0)

    # Empty cohort is empty, not an error.
    r = transport_cost([])
    check("empty cohort n", r["n_units"], 0)
    check("empty cohort w1", r["w1_months"], 0.0)

    # p90 is the MW weighted upper quantile of the delay.
    r = transport_cost([pair(10, 10 + i) for i in range(10)])
    check("p90 delay", r["p90_delay_months"], 8.5, tol=1e-9)

    print(f"\n{11 - len(failures)}/11 passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
