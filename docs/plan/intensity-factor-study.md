# Declared study: the capex intensity surprise as a cross-sectional factor

**Status: development only, declared before the run.** Both sealed windows are spent. The provider study
found intensity surprises charged over five to twenty trading days. This study asks whether that is a
property of the AI infrastructure complex rather than of eight tickers.

## The object

Every listed name in the complex with measurable quarterly capex and revenue: hyperscalers, compute and
AI names, data center REITs, the buildout contractors, power, and fuel and nuclear. For each name and
quarter, the year over year change in capex intensity, and the equity return after the filing date.

## Data

- Fundamentals: SEC XBRL company concepts for every ticker in the declared market panel groups, fetched
  and cached under `results/sec-complex/`, written to `results/complex-capex-quarterly.csv` and
  `results/complex-revenue-quarterly.csv`. Index and futures tickers and funds are skipped: they do not
  file with the SEC.
- Prices: `results/bar-cache/`, daily closes, read only.
- Event date: the later filing date of the two facts, so the panel is point in time.

## Tests, all reported

1. **Within quarter cross-section, the primary test**: the Spearman correlation between intensity change
   and forward excess return inside each calendar quarter, averaged across quarters with at least five
   names.
2. **Pooled**: the same correlation across all observations.
3. **Tercile spread**: mean forward excess return of the top third of intensity change against the
   bottom third.
4. **Group breakdown**: the mean within quarter correlation per declared group, so the result cannot rest
   on one sector.

Horizons are five, twenty and sixty trading days. The excess return uses two benchmarks, the name's own
declared group and the whole complex equal weight, both reported.

## Null

Within quarter permutation of the intensity labels, five thousand draws, recomputing the mean within
quarter correlation. This controls for common time effects, which matters because the complex reports in
clusters.

## Falsifier

The mean within quarter correlation is not negative at five or twenty days, or it is carried by a single
group.

## Ceiling

Quarterly fundamentals against daily prices, overlapping windows, one free price source, and a sample
that spans a single buildout. This is a research candidate, not a tradable rule, and it opens no sealed
window.

## Reproduce

    python3 scripts/fetch_complex_fundamentals.py
    python3 scripts/build_intensity_factor_study.py

## Result, 2026-10-04

640 observations across 58 names with SEC capex and revenue, 29 quarters, both benchmarks reported.

The declared primary test does not hold: the mean within-quarter correlation is -0.035 against the
complex benchmark at five days (p 0.45) and -0.083 against the own group benchmark (p 0.08). At twenty
days it is -0.000 and -0.060 (p 1.00 and 0.20), and at sixty days the sign is mixed. The eight name
result does not generalise once time effects are controlled by the within-quarter design.

The structure that does survive is segment level and sign consistent: hyperscalers negative at every
horizon (-0.14 to -0.28), compute and AI negative at twenty days (-0.41 against own group), buildout
negative at every horizon (-0.13 to -0.20), while data center REITs are positive at five and sixty days
(+0.08 to +0.19). Power and fuel and nuclear are mixed.

The fact this leaves: capital intensity surprises are charged in the capital intensive segments and not
charged, or rewarded, where capacity is leased or regulated. That is a hypothesis with a named object,
not a factor, and the next study declares the segment split before it runs.
