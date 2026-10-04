# Delivery ownership layer

This package audits the largest slipped entities without promoting matcher proposals into issuer exposure.

## Contract

`results/exposure-panel.csv` is the measured EIA entity panel.

`docs/entity-crosswalk.csv` is the only attribution authority.

A row counts as attributed only when the crosswalk status is `verified` and its source receipt is an HTTP(S) URL.

FERC eLibrary search pages and EIA inventory pages are discovery sources, not ownership evidence by themselves.

A verified row needs the entity link, issuer identity, source document or docket, filing date, URL, and economic channel.

## Run

```sh
python3 scripts/build_ownership_crosswalk.py
```

The output is `results/ownership-crosswalk.csv`.

The script aggregates slipped MW by exact normalized entity name and preserves the panel matcher statuses as context.

Unmapped entities remain `unresolved`.

## Evidence check on 2026-10-03

The exposure panel contains 2,181 rows across 1,070 entities.

The largest twelve entities are listed in `docs/plan/crosswalk-procedure.md`.

Only Georgia Power has a verified row among those twelve.

Its receipt is Southern Company's 2025 10-K, accession `0000092122-26-000006`, filed 2026-02-19.

The receipt is `https://www.sec.gov/Archives/edgar/data/41091/000009212226000006/so-20251231.htm`.

The EIA-860M files inspected here identify entity and plant fields but do not provide the owner link needed for these rows.

FERC eLibrary returned the search application and no docket-specific receipt in the bounded check.

The other largest entities remain unresolved.

This result closes the measurement question without claiming a new listed-owner exposure.

## Bounded public-source follow-up

A second read-only pass checked the public FERC eLibrary search application at `https://elibrary.ferc.gov/eLibrary/search`.

The search surface loaded, but no entity-specific docket receipt was validated for the ten largest unresolved entities.

The EIA-860M landing page at `https://www.eia.gov/electricity/data/eia860m/` was also checked.

The inspected inventory files expose entity and plant fields but not the owner link required for attribution.

SEC EDGAR search at `https://www.sec.gov/edgar/search/` produced no dated filing that explicitly links one of those entities to a listed issuer.

The RWE investor-relations page at `https://www.rwe.com/en/investor-relations/` did not provide a dated receipt for the exact RWE Renewables Americas LLC entity.

No state commission filing was promoted because the current panel lacks project identifiers and jurisdictions for a targeted docket search.

The bounded pass produced zero verified project-to-listed-issuer mappings across the ten unresolved entities.

The remaining source work is project-identified FERC or state-docket research, not broader name matching.

## Falsifier and next evidence

The attribution ceiling changes only if a source-backed project-to-owner link identifies a listed counterparty with a concentrated economic channel.

A name match, a search result, or a proposed ticker does not falsify the ceiling.

A FERC docket or EIA owner record with a citable date and URL would update the corresponding row.
