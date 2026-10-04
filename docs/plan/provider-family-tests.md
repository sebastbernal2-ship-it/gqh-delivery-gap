# Declared study: the provider to family map, tested family by family

**Status: development only, declared before the run.** Both sealed windows are spent. The aggregate test
came back inside the null (T19) and left one object open: each provider is levered to specific rental
families, and this study tests that map.

## The map under test

`docs/scan/provider-family-map.jsonl` declares, for each of ten providers, the rental families that
should lever its revenue, with a condition and a falsifier per entry. The map is marked
`proposed_unverified` and this study is the verification attempt.

## Data

- Provider revenue: `results/provider-revenue-quarterly.csv`, quarterly, SEC XBRL.
- Rental prices: `results/compute-price-monthly.csv`, eighteen families, monthly medians.
- EQIX is declared untestable with rental prices, because colocation rent per megawatt is not a GPU
  family and no rent per megawatt series is held. It is recorded that way, not dropped.

## Tests, all reported

1. **Mapped pairs**: for each provider and each mapped family, Spearman rho between the lagged family
   three month log price change (the quarter before the revenue quarter) and year over year revenue
   growth. Minimum ten usable quarters per pair, otherwise reported as insufficient.
2. **Placebo contrast**, the single declared comparison: the same statistic for every non-mapped family
   with coverage, per provider. The question is whether mapped pairs beat non-mapped pairs as a group.
3. **Combination**: for each provider, the mean rho across its mapped families and across its non-mapped
   families.

## Null

Per pair, a circular shift of the family monthly series against the revenue panel, shifts one to forty
eight months, all reported. A pair survives when the observed rho exceeds its shift null at five percent.

## Falsifier

Mapped pairs do not beat non-mapped pairs as a group.

## Ceiling

Thirty odd provider family pairs on a short revenue history, and providers share the same family series,
so pair counts are descriptive and not independent. Development only.

## Reproduce

    python3 scripts/build_provider_family_tests.py
    python3 scripts/build_provider_family_tests.py --mode relative

## Result, 2026-10-04

Pass one, raw family changes as declared: ten mapped pairs with mean rho -0.27 against thirty two
unmapped pairs at -0.02. Mapped pairs produced zero shift null survivors, unmapped pairs produced five.
The map as written is not supported, and the mapped direction leans against it.

The strongest single association sits where the map says it should not: EQIX, the provider mapped to
colocation rent rather than GPU families, shows +0.71 against g5 and +0.64 against g4ad. That reads as
a shared demand factor rather than a family lever.

Pass two, declared after pass one and before its own run: the same pairs against the relative family
change, the family change minus the cross-family median at the same month, which removes the common
factor. Mapped mean rho -0.17 against unmapped +0.04, with zero mapped survivors against four unmapped.
The removal of the common factor does not rescue the map.

The fact this leaves: family price mapping is retired as the provider transmission variable, on both raw
and relative specifications. The provider object moves to level variables, revenue per megawatt,
contracted share and lease spread, which need filing level data rather than rental prices.
