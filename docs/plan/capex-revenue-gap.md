# Declared study: the provider capex intensity and the capex to revenue gap

**Status: development only, declared before the run.** Both sealed windows are spent. T17 tested capex
against compute prices and T19 tested revenue against compute prices, but the input side and the revenue
side were never joined directly. This study joins them.

## The object

Capital intensity per provider: quarterly capex divided by quarterly revenue. The question is whether the
buildout is outrunning the revenue it serves, and whether that gap is persistent, because the equity leg
of the provider family depends on it.

## Data

`results/provider-capex-quarterly.csv` and `results/provider-revenue-quarterly.csv`, both SEC XBRL, the
same ten providers, aligned by period end within twenty days.

## Tests, all reported

1. **Intensity trend**: per provider, Spearman correlation between capex intensity and the quarter index.
2. **Capex leads revenue**: Spearman between year over year capex growth and next quarter's year over
   year revenue growth, pooled, with a circular shift null on the capex series.
3. **Gap persistence**: the autocorrelation of the gap, year over year capex growth minus year over year
   revenue growth, per provider and pooled.

## Falsifier

Intensity is flat or falling, or capex growth does not lead revenue growth, or the gap has no
persistence.

## Ceiling

Ten providers, short panels, and capex concepts differ across filers. Development only, and nothing here
is priced.

## Reproduce

    python3 scripts/build_capex_revenue_gap.py

## Result, 2026-10-04

Six providers carry aligned capex and revenue panels. Pooled capex intensity is 0.287 of revenue, and
the recent quarters run far above the average for the hyperscalers: MSFT last at 0.471 against a 0.136
mean and a trend rho of +0.94, ORCL last at 2.017 against 0.212 and +0.92, GOOGL last at 0.404 against
0.184 and +0.35. META is flat to down, EQIX is steady.

The pooled gap, capex growth minus revenue growth, averages -0.089, so on average revenue still outran
capex across the panel, and its autocorrelation is -0.28, meaning gaps do not persist. Capex growth does
not lead revenue growth at one quarter: rho -0.07, p 0.70, on 122 ordered pairs.

The fact this leaves: the input side is running ahead of revenue for the hyperscalers in the most recent
quarters, while the aggregate gap is not yet persistent and investment does not show up as revenue within
a quarter. The depreciation wall node now carries evidence, and the open object is whether the market
prices the intensity rise, which needs the market panel and is outside this study.

Four providers have no usable panel and are recorded with reasons: AMZN last tagged the capex concept in
2017, APLD files capex annually, and CRWV and IREN have too few quarters.
