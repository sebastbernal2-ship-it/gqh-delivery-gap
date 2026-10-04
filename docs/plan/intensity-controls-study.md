# Declared study: intensity under controls, and the conversion interaction

**Status: development only, declared before the run.** Both sealed windows are spent. This study tightens
the intensity claim after the captain's correction: capex over revenue measures investment intensity, and
by itself it does not show that spending exceeded expectations or failed to convert into revenue. Until an
expectation channel and a counterparty are identified, the claim is a falsifiable association, not a
market charge.

## Test A, intensity under controls

Quarterly cross sectional regressions of forward twenty day group excess return on standardised
predictors, one regression per filing quarter with at least eight names:

- capex intensity change, the candidate;
- revenue growth, year over year;
- asset growth, year over year;
- operating margin, operating income over revenue, as the profitability control;
- the common investment factor, the cross sectional mean intensity change in that quarter, so the test is
  about relative intensity rather than the level of the whole complex;
- declared peer group as a fixed effect, achieved by demeaning every predictor within group.

The estimator is Fama-MacBeth: mean coefficient across quarters, its t statistic from the cross quarter
dispersion, and the share of quarters with the expected sign. The candidate is only interesting if its
mean coefficient is negative with a t statistic beyond two.

## Test B, the conversion interaction

The expectation channel, first version, with data in hand:

- **Revenue conversion failure**: revenue growth below the name's own trailing four quarter mean.
- **Backlog conversion failure**: RPO change below its typical seasonal change (the RPO panel), for the
  names that carry it.

Declared interaction test: the candidate coefficient is estimated again with the conversion flag and with
the candidate times flag term. The claim would be strengthened if the candidate term is more negative in
the failure group, and weakened if the interaction is absent.

## Test C, the filing surfaces, declared as the next stage

The 8-K and related filings carry the expectation itself: item 2.02 results, item 7.01, and earnings
releases with guidance. The register already holds 465 filings for a few names, and RPO disclosures cover
22 names in the complex. The next stage fetches 8-K metadata for all 59 names, then guidance language from
the earnings exhibits, and conditions the candidate on guidance revisions rather than on realised revenue.
This study only declares that plan; it does not claim the channel.

## Falsifier

The candidate coefficient is zero or positive once the controls are in, or the interaction term is absent.

## Ceiling

Small cross sections per quarter, one price source, RPO coverage limited to 22 names, and no guidance data
yet. Development only.

## Reproduce

    python3 scripts/build_intensity_controls_study.py

## Result, 2026-10-04

The tightened test fails. 637 observations across 58 names and 127 quarters, 22 quarters with a large
enough cross section.

- Univariate, Fama-MacBeth: mean coefficient -0.0068, t -0.98. Even without controls the association is
  not significant under this estimator.
- With sector (group fixed effect), revenue growth, asset growth and operating margin controlled: the
  intensity coefficient is +0.0061, t 0.65. The sign flips and nothing survives.
- Adding the common investment factor changes nothing: +0.0061, t 0.65.
- Conversion interaction, revenue version: failure group +0.0105 (t 1.05), passing group -0.0076 (t -0.54).
  That is the opposite of the declared expectation.
- Conversion interaction, backlog version: 192 observations, fewer than four usable quarters, reported as
  insufficient rather than as a result.

The fact this leaves: capex intensity does not predict weaker relative returns once sector, growth,
profitability and the common investment factor are controlled, and the realised revenue conversion split
does not rescue it. The correction is confirmed empirically: capex over revenue measures investment
intensity, and on this panel intensity alone is not a priced expectation surprise. The association stays
only as a falsifiable hypothesis about the expectation channel, which is stage C.
