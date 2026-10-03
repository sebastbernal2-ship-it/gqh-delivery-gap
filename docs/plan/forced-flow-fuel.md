# The fuel gauge: how much size sits near its own margin threshold

Measured from the public per account panel, 513,119 rows, one per account per day, cached under `data/hyperliquid/`.

## What the panel carries

Date, address, group, account value, leverage, whether margin is cross or isolated, number of positions, gross
exposure, entry and current distance, and `liq_next`, the distance to liquidation. That is the constraint itself
rather than a proxy for it: how far each leveraged account sits from the rule that will close it, with the size
attached.

## The measured distribution

Live account-days, meaning gross exposure above zero and a finite distance: 513119 rows across 96695
accounts, from 2025-07-29 to 2026-08-18.

| distance to liquidation | account-days | share of gross exposure | gross, millions | median leverage |
|---|---|---|---|---|
| 0.00-0.01 | 496126 | 98.60% | 445935.5 | 10 |
| 0.01-0.03 | 0 | 0.00% | 0.0 | nan |
| 0.03-0.05 | 0 | 0.00% | 0.0 | nan |
| 0.05-0.10 | 0 | 0.00% | 0.0 | nan |
| 0.10-1000000000.00 | 16993 | 1.40% | 6328.3 | 20 |

Accounts at leverage ten or more hold 77.78% of gross exposure. Account-days within 0.03 of the
threshold hold 98.60%.

## The unit, stated honestly

The column's exact scale is not yet confirmed against a known liquidation, so the buckets above are in the
column's own units. The first step of the test confirms the unit by finding an account whose `liq_next` reaches
zero and checking what price move produced it. Until then, read the table as a shape, not as percentages.

## The declared measurement that follows

1. **Fuel**: the distribution above, weighted by gross exposure, per day.
2. **Trigger**: a price move into the thin part of that distribution, at one minute resolution.
3. **Path**: the conditional return over one to sixty minutes after the trigger.
4. **Economics**: net of 4.5 basis points per side, against the measured capacity of 3.3m per side in BTC
   within ten basis points.
5. **Null**: the same statistic after randomly placed moves of the same size, and after the same time of day.

Declared before running. One statistic: mean post trigger return net of costs. If it fails, the ladder of
failures is complete and the answer for this class is no at this size.
