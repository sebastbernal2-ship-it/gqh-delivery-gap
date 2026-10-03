# Imagery test: pre-registered before fetching anything

Declared 2026-10-03, before any scene for this test is fetched. The earlier probe on eight sites is treated as
exploration and is not evidence for anything.

## The claim under test

A site that will be delivered late shows less physical progress in satellite imagery than its promise implies.
The measurable version: **the change in surface texture at a site between its promise month and its realised
month correlates with how many months the delivery slipped.**

Texture is the mean absolute difference between neighbouring pixels in the extracted window. Moving earth,
pouring foundations, staging turbines and laying panels all raise it. Bare ground and finished ground are both
flat, which is why brightness alone did not separate anything: the eight site probe found a median brightness
difference in differences of minus 0.7, which is nothing.

## Design, designed for power rather than for convenience

- **Cross section, not time series.** Forty sites, one observation each, chosen by the declared rule already in
  `scripts/build_site_labels.py`: present in the planned sheet of an early vintage and the operating sheet of a
  later one, at least a three month gap between promise and realisation, usable coordinates, largest by
  capacity first.
- **Power stated in advance.** With forty sites a Spearman correlation of 0.44 is detectable at the conventional
  level. The eight site exploration suggested 0.72, so forty is enough to confirm or destroy it.
- **Declared statistic**: Spearman rank correlation between `texture_change` and `slip_months`. One statistic,
  declared here, reported whatever it says.
- **Declared direction**: positive. More slip, more texture change, because the site is still being worked when
  it was supposed to be finished.

## Two nulls, both required

1. **Permutation null**: shuffle `slip_months` across sites two thousand times and record the distribution of
   Spearman correlation. The real value must sit outside it.
2. **Date placebo**: for the same sites, fetch two scenes at the same separation but at dates **randomly placed
   within the same two year span**, and compute the same statistic against `slip_months`. If a made up date pair
   produces the same correlation, the statistic is reading season and cloud, not construction.

## What would make this a finding, and what would end it

A finding needs the real correlation outside the permutation null **and** materially larger than the date
placebo. Anything else ends the direction, and it is recorded as a truth about imagery at this resolution.

## Stated limits, before the numbers arrive

Ten metre pixels cannot resolve a substation or an access road. Clouds, snow and shadow contaminate windows and
are reported as a cloud fraction per scene. Sites are wind and solar, which are large and flat, so the measure
may work where a compact gas site would not. Two scenes per site is a coarse view of a construction process that
takes years.
