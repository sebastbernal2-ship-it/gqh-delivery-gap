# Index mandate study

This package measures whether a public index change can be converted into a dated and quantity-scaled flow observation.

It does not treat an index list as constituent history.

It does not call an event tradable without a primary announcement clock and pre-effective quantity inputs.

## Pre-registration

The index is the S&P 500.

The development window is 2015-07-01 through 2022-09-30.

The existing delivery holdout begins after this boundary and remains closed.

The event universe is one row for each S&P 500 addition or deletion in the declared window.

The discovery source is the public historical components page at `https://en.wikipedia.org/wiki/Historical_components_of_the_S%26P_500`.

The discovery source is not sufficient evidence for return analysis.

A return-eligible event needs a primary provider announcement, an announcement date, an effective date, pre-effective holdings or target weight, pre-effective fund assets, a pre-effective price, and a source receipt for each input.

The flow estimate is `tracking assets * target weight change / pre-event price`.

The fill must occur after the earliest verified public availability time.

A date-only record with an unknown announcement time is excluded instead of using the effective close.

The falsifier is no quantity-scaled effective-close pressure against a matched non-event date, followed by no predicted post-effective reversal.

Costs must be fixed before any return calculation.

Daily bars cannot establish close-auction spread or impact, so this package reports no tradability result until that cost evidence exists.

## Run

```sh
python3 scripts/build_index_mandate_study.py
```

The event inventory is `results/index-mandate-events.csv`.

The coverage summary is `results/index-mandate-study.csv`.

The current run is a coverage inventory only.

It uses the public historical components page as a secondary discovery source.

It records no primary announcement timestamps and no pre-effective forced quantities.

Therefore it produces zero eligible return events and does not run an event return test.

## Bounded public-source follow-up

The SEC Form N-PORT public data sets are reachable at `https://www.sec.gov/data-research/sec-markets-data/form-n-port-data-sets`.

The SEC readme at `https://www.sec.gov/files/nport_readme.pdf` states that the public data sets begin with submissions from October 2019.

N-PORT can provide as-filed holdings, assets, and report periods for a subset of later events.

N-PORT does not provide the S&P announcement clock or the index effective-date decision.

One SPDR S&P 500 ETF Trust filing is reachable at `https://www.sec.gov/Archives/edgar/data/884394/000175272422196968/primary_doc.xml`.

Its SEC header is `https://www.sec.gov/Archives/edgar/data/884394/000175272422196968/0001752724-22-196968-index-headers.html`.

The filing was accepted on 2022-08-26 and reports holdings and assets for 2022-06-30.

That snapshot predates the inventory's latest 2022-09-19 effective date but does not establish daily weights or event timing.

The S&P DJI index-news archive and a sample announcement path returned HTTP 403 at `https://www.spglobal.com/spdji/en/documents/indexnews/` and `https://www.spglobal.com/spdji/en/documents/indexnews/announcements/20220902-1474027/`.

The bounded pass found no other reproducible primary announcement archive for the declared window.

The result is a no-go for return analysis, not evidence that no public archive exists.

## Interpretation

The mandate mechanism remains plausible because a tracking vehicle must hold the index as defined.

This run does not identify an edge.

The next evidence is a primary announcement archive with historical effective dates and a point-in-time quantity panel.

A source that only lists current constituents or quarterly holdings after the effective date is not enough.
