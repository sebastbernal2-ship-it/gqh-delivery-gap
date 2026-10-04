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
  median as the aggregate stand-in. The exact 566-row family panel is also in Snowflake
  `RAW.SOURCE_RECORDS` source `aws_compute_monthly_family`, batch
  `044a082fe24c9afd3410a974f7fa471ce3b5dc12a6f4cf2a651b6accc9d331bb`.
- **Outcome**: quarterly capital spending from SEC XBRL `PaymentsToAcquirePropertyPlantAndEquipment`,
  fetched per issuer and cached under `results/sec-capex/`. Declared issuers, resolved from the SEC
  ticker file at fetch time: hyperscalers MSFT, AMZN, GOOGL, META, ORCL; host and neocloud issuers
  CRWV, IREN, HUT, CORZ, APLD; data centre REITs EQIX and DLR as a separate group. Quarter-over-quarter
  log growth of capex. The current 192-row extract is centrally loaded as
  `sec_provider_capex_quarterly`, batch
  `48534d7bf98d785d2e1f738eaa867882dca57056e634b9deaa453e7844e0ee6e`; it may contain
  restatements and is not a point-in-time filing-vintage panel.
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

## Unit-of-observation audit, 2026-10-04

The original 42-row inference is retained above as its immutable historical receipt, but it should
not be read as 42 independent compute shocks: the same quarterly AWS feature is repeated across
several issuers. There are also two implementation caveats in that run: the displayed compute
window used the legacy `g3` family’s last month (2025-02), not the latest family in the archive, and
the implementation permitted adjacent *observed* quarters to bridge calendar-quarter gaps. Family
hourly-instance prices also combine SKUs of different sizes, so composition can move the family
median even without a matched-SKU price change.

The separate, conservative audit in `scripts/audit_compute_lead_dependence.py` leaves the original
protocol/result untouched. It requires all three monthly observations for each family/quarter,
requires calendar-adjacent quarters, uses log changes, and collapses issuer outcomes to one median
per group per compute quarter. It excludes the 2026 March–June source gap and produces no p-values.
Current diagnostic: 13 unique quarter pairs for the pooled issuer group (descriptive Spearman rho
about -0.03), 7 hyperscaler pairs (about -0.29), 0 host pairs, and 6 REIT pairs (about +0.09).
Those small counts are not evidence for a trade; the changed unit, stricter completeness, and
provider composition make the result a diagnostic rather than a replacement hypothesis test.
Reproduce with:

```sh
python3 scripts/audit_compute_lead_dependence.py
```

The audit queries those pinned Snowflake batches directly and archives the exact CSV/JSON outputs
to `VECTOR_RESEARCH.RAW.RESEARCH_ARTIFACTS`.

The AWS archive is still useful as a bounded compute-rental context stream: 1.592M observations,
62 instance types, USD per whole instance-hour, 2022-05-31 through 2026-09-30, with March–June 2026
absent. It is not GPU-hour price, utilization, fulfilled allocation, total supply, a named-company
capacity meter, nor verified historical data-arrival time. Keep it as a separate retrospective
study; do not feed it into the equity event study without a new exposure mechanism and declared
test.

Both the compute index removal clause and the falsifier are met by the data: only the aggregate
produces anything, and it is not a positive association. The chain must stand on its other links.
