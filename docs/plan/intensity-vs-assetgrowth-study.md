# Declared study: the intensity charge against asset growth

**Status: development only, declared before the run.** Both sealed windows are spent. The intensity charge
is stable in sign across two time windows, and it may be nothing new: high asset growth is a long known
cross-sectional effect, and capex intensity is one way to measure it. This study separates the two.

## The object

Two predictors of forward group excess return, measured on the same panel, in the same within-quarter
design:

1. capex intensity change, capex over revenue year over year, as before;
2. total asset growth, total assets year over year, from SEC XBRL.

The question is whether the intensity reading carries anything beyond asset growth. If the two are
largely the same signal, the honest statement is that we have re-measured a known effect, which is
useful to know and not an edge.

## Tests, all reported

1. The intensity charge as before, within quarter, for reference.
2. The asset growth effect, the same statistic.
3. The incremental test: the cross-sectional correlation of the intensity residual, after removing asset
   growth within each quarter by rank, against forward excess return. A residual effect is the only
   reading that claims novelty.
4. The correlation between the two predictors themselves, so their overlap is visible rather than
   assumed.

Horizons five, twenty and sixty trading days. Nulls are within-quarter permutations, two sided.

## Falsifier

The residual test shows no association at five or twenty days, which would say the charge is asset growth
wearing a different name.

## Ceiling

Same panel, same price source, overlapping windows, and asset growth itself is measured with XBRL
timeliness limits. Development only.

## Reproduce

    python3 scripts/fetch_complex_assets.py
    python3 scripts/build_intensity_vs_assetgrowth_study.py

## Result, 2026-10-04

The two predictors are nearly unrelated in this panel: the mean within-quarter correlation between
intensity change and asset growth is -0.006, so the intensity charge is not asset growth wearing a
different name.

They point in opposite directions. Asset growth is rewarded: +0.067 at five days, +0.133 at twenty and
+0.092 at sixty, which is the opposite sign of the classic asset growth anomaly and coherent with a
buildout where adding capacity is read as demand. Intensity is charged: -0.087 at five days, -0.072 at
twenty, -0.017 at sixty. The intensity reading after removing asset growth is -0.109 at five days
(p 0.018), -0.076 at twenty (p 0.10) and -0.007 at sixty.

The fact this leaves: intensity surprises carry a short-horizon charge beyond asset growth, on a panel
where asset growth is a reward rather than a penalty. The charge is small, concentrated in the first week,
and capacity is unknown. Other known factors are untested, which bounds the claim.
