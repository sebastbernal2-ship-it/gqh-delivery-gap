# The disclosure clock A/B for the intensity strategy

Status: development only. Owner: sebas. Date: 2026-10-04. Runner:
`scripts/run_intensity_pit_clock_test.py`. Artifact: `results/intensity-clock-test.json`.

## What was wrong

`results/complex-capex-quarterly.csv` and `complex-revenue-quarterly.csv`, built by
`scripts/fetch_complex_fundamentals.py`, keep the **latest** filing that reported each quarter,
which is normally the following year's ten-K comparative. The median lag between a quarter's end
and its recorded availability is 401 days, so every intensity signal carries a clock about thirteen
months late relative to the original disclosure.

`scripts/build_complex_panels_pit.py` rebuilds both panels from the same local cache with the
**earliest** filing that reported each quarter. Same rows, same tickers, and the median lag falls to
34 days for capex and 36 for revenue.

## The A/B

The declared base configuration, one unit of gross capital, group neutral, terciles, twenty-session
holds, run on both clocks:

| Clock | Net annualised | Volatility | Sharpe | Max drawdown | Cohorts |
|---|---|---|---|---|---|
| Latest filed, as published | +2.94% | 8.5% | 0.347 | -22.9% | 267 |
| Earliest filed, corrected | **-4.89%** | 7.8% | **-0.630** | **-48.0%** | 260 |
| Latest filed, doubled costs | +1.44% | 8.5% | 0.170 | -26.5% | 267 |
| Corrected, doubled costs | -6.24% | 7.8% | -0.804 | -53.4% | 260 |

## Reading

The published edge does not survive the corrected disclosure clock. Trading the signal when the
market first saw the quarter loses money across the sample; the positive result came from entering
about thirteen months late, which shifts the cohort dates into a different regime and re-uses facts
after later periods were already public. The RPO and obligation panels are unaffected: their median
availability lags are 38 and 55 days, so the expectation-gap studies keep their clocks.

## Ceiling and next step

One price source, development only, both sealed windows spent. The corrected panels are new files;
the originals are another workstream's artifact and were not touched. Reconciling the published
note and thesis with this result belongs to that owner, and it is reported to the captain.
