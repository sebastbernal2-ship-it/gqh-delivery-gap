# Source and capability audit

Owner: Vishnu. Status at 2026-10-03. No keys or participant accounts were tested by this capture.

## Evidence vocabulary

- User-reported: the participant reports access; not an entitlement/download test.
- Documentation-verified: official page describes capability; still test account, symbol and date.
- Listing-verified: public file listing observed; binary contents have not been downloaded.
- Download-verified: reserve this label for saved files and checked manifests. None claimed here.
- Archived result: belongs to the earlier branch, not reproduced on current main.

## User-reported inventory

The user reports API access for Databento, Massive competition data, FMP, FRED, Census, IMF,
BEA, UN Comtrade, EIA, Congress, USGS Landsat M2M, NASA FIRMS and Copernicus. Some inventory
entries explicitly say their connector is not yet connected. A key is not blanket access to
all products/history. Never copy values into this public repo.

Massive is intended for competition filings/events, with an optional options challenge. Exact
stock-data entitlement and point-in-time options availability need testing. FMP transcript,
consensus, delisted and historical-universe entitlements are not certified. Databento dataset,
schema, date, license and download costs must be checked individually.

The Databento screenshot shows an expensive multi-year MBP-10 estimate. Its exact symbol
selection was not browser-verified. Do not infer a fixed per-stock price or buy it automatically.

## Practical free shortlist

### Alpaca Basic — documentation-verified

Official plan advertises stock historical data since 2016 and 200 historical calls/minute.
The FAQ explicitly allows historical SIP queries without subscription when `end` is at least
15 minutes old. Set `feed=sip`; default/live free IEX is a different coverage set. This supports
historical bars, trades and top-of-book quotes, not full depth or order identities.

Next check: participant paper/data credentials, PWR/SPY old daily bars and a small 2018 quote/trade
window; inspect entitlement responses, returned dates and all pagination. Do not promise all
inactive/OTC symbols. An older feed overview has ambiguous free-feed wording; the explicit FAQ
is the basis here, and an authenticated test is still necessary.

Sources: [plan](https://docs.alpaca.markets/us/docs/about-market-data-api),
[SIP FAQ](https://docs.alpaca.markets/us/docs/market-data-faq),
[quotes/pagination](https://docs.alpaca.markets/us/reference/stockquotes-1).

### Tiingo EOD — documentation-verified

Dataset advertises history reaching 1962 for some securities; actual dates vary by ticker.
Free plan: 50 requests/hour, 1,000/day, 1 GB/month. Raw/adjusted OHLCV, dividends and splits
are suitable for a small daily equity panel. Query metadata for each security. This is not
intraday depth or a guaranteed survivorship-free universe. Individual internal-use licensing
requires review before team distribution or public raw-data display.

Sources: [product/limits](https://www.tiingo.com/products/end-of-day-stock-price-data),
[metadata/fields](https://www.tiingo.com/documentation/end-of-day).

### SEC EDGAR — documentation-verified; example text inspected

Free original filings and exhibits; public indexes from 1994Q3. Declare a contact User-Agent
and respect the current maximum 10 requests/second. Company submissions/XBRL APIs do not
make all operational fields standardized. Use historical filings and original source tables.

A PWR release dated February 2011 includes historical backlog and named project schedule
forecasts. It proves useful fields exist historically, not a complete comparable series.

Sources: [archive/access](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data),
[APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces),
[PWR example](https://www.sec.gov/Archives/edgar/data/1050915/000095012311016779/h79890exv99w1.htm).

### Nasdaq public ITCH — listing-verified

Selected days including 2019 and 2021 are present. The 2019-01-30 gzip listing is about 4.76 GB.
Use for order-event/replay engineering; it is sparse, single-venue data, not free continuous
ten-year validation. Stream/filter only what is needed. Contents/download/license use still
need review. No arbitrary-day entitlement inferred.

Sources: [public listing](https://emi.nasdaq.com/ITCH/Nasdaq%20ITCH/),
[official sample FAQ](https://www.nasdaqtrader.com/Content/TechnicalSupport/FAQs/ITCH_FAQ.pdf).

### EIA and ALFRED — documentation-verified

EIA-860M monthly XLS vintages begin July 2015. Annual EIA-860 extends much farther, but is not
the same monthly schedule/revision panel. Preserve vintages and publication evidence; EIA notes
preliminary values may change. These are generator inventories, not a complete data-center feed.
ALFRED realtime/vintage parameters support macro values known at the time; coverage is series-specific.

Sources: [860M](https://www.eia.gov/electricity/data/eia860m/index.php),
[860 annual](https://www.eia.gov/electricity/data/eia860/index.php),
[vintage semantics](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html).

## Candidate-company source receipts

These recent disclosures support the data audit, not ten-year coverage or an alpha claim:

- [PWR backlog/timing](https://investors.quantaservices.com/news-events/press-releases/detail/390/quanta-services-reports-fourth-quarter-and-full-year-2025-results).
- [ETN electrical orders/backlog](https://www.eaton.com/us/en-us/company/news-insights/news-releases/2026/eaton-reports-record-fourth-quarter-2025-results.html).
- [EME RPO and segments](https://www.sec.gov/Archives/edgar/data/105634/000010563426000025/eme-20251231.htm).
- [DLR leases/commencement lag](https://investor.digitalrealty.com/news-releases/news-release-details/digital-realty-reports-fourth-quarter-2025-results).

## Not a reliable shortcut

Alpha Vantage's full daily history requires premium; its free compact daily response is only
100 observations. [Official documentation](https://www.alphavantage.co/documentation/).
LOBSTER sample-host DNS failed in the attempted check; no binary download was verified. No
free continuous decade-long equity L2/L3 archive was verified. Unofficial mirrors and broker
CFD quotes are not automatically equivalent to exchange equity trades/books.

Ornn trial was requested in the conversation, not confirmed. Index history/methodology and ICE
compute futures existence/access/liquidity in the old draft remain unverified here. Likewise,
0xArchive wallet-level history/window/credit consumption and Hyperliquid S3 archives need a
separate exact endpoint/market/plan audit. Do not silently import those claims from IDEA.md.

## What each new verified download must leave behind

Provider, dataset/feed, schema, security identifier, requested/actual range, fetch time,
pagination completeness, content hash, size/row count, license disposition, missingness report
and provenance path. A successful HTTP response is not sufficient. Large raw files stay out
of git; small public synthetic fixtures may be added under tests when implemented.
