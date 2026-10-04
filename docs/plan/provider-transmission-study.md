# Declared study: does the compute rental change reach provider revenue

**Status: development only, declared before the run.** Both sealed windows are spent. This is the weak
link inside the provider family, tested on its own terms.

## The link

The provider family claims: compute rental change transmits into the economics of the listed providers,
which is what makes the rental series holdable at all. The capex lead was already tested and came back
negative as declared (T17). Capex is the input side. The revenue side was never connected, and that is
the link that decides whether the family has a holdable path.

## Data

- Compute rental prices: `results/compute-price-monthly.csv`, eighteen families, monthly.
- Provider revenue: quarterly, fetched from SEC XBRL company facts for the ten providers already in the
  capex file, preferring `RevenueFromContractWithCustomerExcludingAssessedTax` and falling back to
  `Revenues`, quarterly durations only, latest filed fact per period.
- The aggregate rental change: the median three month log change across families with coverage at that
  month.

## Tests, all reported

1. Pooled Spearman correlation between the lagged aggregate rental change (the quarter before the
   revenue quarter) and year over year revenue growth.
2. Family level: the same correlation per family with at least twenty four months of coverage.
3. The reverse control: revenue growth against the following quarter's rental change. If the reverse
   control dominates, the family is discounted rather than led, and that is a different fact.

## Null

Circular shifts of the rental series against the revenue panel, five thousand draws. The question the
null answers is whether the timing alignment matters at all.

## Falsifier

The forward correlation is not positive, or the reverse control dominates it.

## Ceiling

Ten providers and a short revenue history. Small samples bound what a positive result would mean.
Development only, and no result here opens a sealed window.

## Reproduce

    python3 scripts/fetch_provider_revenue.py
    python3 scripts/build_provider_transmission_study.py

## Result, 2026-10-04

Run as declared. 91 usable provider-quarters across ten providers. The lagged aggregate rental change
shows rho -0.16 against year over year revenue growth, and the circular shift null places that inside
noise (p 0.85, null median +0.01). The reverse control is also null at -0.05, so the panel is not
discounting either. The family level signs disagree: p5 at +0.21 against p3 at -0.23.

The fact this leaves is precise: the aggregate rental median washes out family heterogeneity, and the
next object is the provider to family exposure map, tested family by family against the providers that
actually sell that family. The aggregate is retired as the transmission variable.
