# Declared study: do compute prices lead provider capex?

**Status: development only, declared before the run.** Both sealed windows are spent. Nothing here is
an instrument test, and nothing may be called out of sample. The protocol is committed before the data
is fetched.

## The question

Do compute family price changes lead provider capital spending by one quarter? The mechanism reading
is simple: listed prices express provider inventory state, and inventory state should shape the next
quarter's capex. If the link exists at all, our own truths say it must exist family by family, because
the aggregate index hides ten essentially independent markets (T8) and the price is a policy price
rather than a clearing price (T9).

## Data, declared before fetching

- **Feature**: monthly median price per instance hour by family, `results/compute-price-monthly.csv`,
  2022-05 to 2026-09, 18 families. Quarter-over-quarter log change per family, and the cross-family
  median as the aggregate stand-in.
- **Outcome**: quarterly capital spending from SEC XBRL `PaymentsToAcquirePropertyPlantAndEquipment`,
  fetched per issuer and cached under `results/sec-capex/`. Declared issuers, resolved from the SEC
  ticker file at fetch time: hyperscalers MSFT, AMZN, GOOGL, META, ORCL; host and neocloud issuers
  CRWV, IREN, HUT, CORZ, APLD; data centre REITs EQIX and DLR as a separate group. Quarter-over-quarter
  log growth of capex.
- **Overlap**: quarters with both a compute observation and a reported capex figure. Providers with
  fewer than six usable quarters are reported but excluded from the pooled test.

## Tests, all reported

1. **Aggregate**: pooled Spearman correlation between the cross-family median price change in quarter t
   and provider capex growth in quarter t+1.
2. **Per family**: the same correlation for each of the 18 families, with the full list reported and
   the count of nominally significant families compared with the count expected under the null.
3. **By group**: hyperscalers, host and neocloud issuers, and REITs, reported separately, because their
   capex processes differ.

## Null

The provider-quarter pairing is shuffled within each provider, 5,000 draws, and the same statistics are
recomputed. The reported p-values are permutation p-values. No state conditioning is possible at this
sample size, and the study says so.

## The compute index removal clause

The study must show whether the link survives without the aggregate. If only the aggregate correlates
and no family does, the finding is reported as an aggregate artifact and the chain's compute link is
marked dead. The chain itself must still stand on its other links.

## Falsifier

No positive association between price changes and later capex in the pooled test, or association present
only in the aggregate, with families flat.

## Ceiling and honesty

Small sample, quarterly disclosure, one provider cycle. Whatever this says, the strongest possible
verdict is a development read on a phase marker, not an edge. Both sealed windows stay closed.

## Reproduce

    python3 scripts/fetch_provider_capex.py
    python3 scripts/build_compute_lead_study.py

## Result, 2026-10-04

Run as declared on 42 provider-quarters. The declared positive mechanism does not hold. The aggregate
test is nominally significant and points the **wrong way**: rho = -0.326, p = 0.044, meaning higher
compute price changes precede **slower** next-quarter capex growth. The family tests are at chance: 2
nominal survivors out of 13 tested against 0.65 expected under the null, names g5 and g5g. The groups
split the same way: hyperscalers rho -0.22 (p 0.32), hosts -0.60 (p 0.12), REITs 0.01 (p 1.0).

Verdict: the compute link as declared is dead. The compute index does not lead provider capex in the
declared direction, and the one significant number is negative and marginal on 42 observations, so it
is not read as a reversed signal. What the negative sign most plausibly shows is that prices are
policy responses to inventory, not a leading demand signal: providers already building tend to list
softer prices, and price spikes arrive when capacity is already tight rather than before capex turns.
That reading is a hypothesis for a new study, not a result.

Both the compute index removal clause and the falsifier are met by the data: only the aggregate
produces anything, and it is not a positive association. The chain must stand on its other links.
