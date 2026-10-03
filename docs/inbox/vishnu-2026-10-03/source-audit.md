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

## Additional free-source audit — 2026-10-03

Status: official documentation reviewed; account entitlements and downloads have not been tested.
These sources can replace some paid macro, filings, power and supply-chain inputs. They do not
replace exchange-grade equity history, Databento depth, or Massive's competition-specific tagged
options/event package.

### Highest-value direct or near-direct streams

| Source | Historical span and cadence | How it connects | Important limit |
|---|---|---|---|
| [SEC EDGAR filings and APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) | Filing archive from 1994; accession-level submissions and XBRL APIs update quickly; bulk ZIPs refresh nightly. | Original 8-K/10-Q/10-K text, exhibits, capex, commitments, project/backlog guidance and public timestamps. This can cover ordinary filing retrieval without Massive. | Use accession-specific filing versions. Current Company Facts is not point-in-time history: amendments/restatements can rewrite a value. SEC does not promise an exact first-public timestamp; apply a conservative availability lag after acceptance. No API key; descriptive User-Agent and current fair-access limits apply. |
| [Census construction spending, C30](https://www.census.gov/construction/c30/data/index.html) | Monthly “Data center” private-office series back to January 2014, about 12.5 years. | Direct numeric measure of realized U.S. data-center construction put in place; use as sector buildout context and a check against announcements. | National aggregate, nominal dollars, not site commissioning, MW, company attribution or a forward expectation. Preliminary releases revise; preserve first-release vintages. |
| [Census M3 Manufacturers’ Shipments, Inventories and Orders](https://www.census.gov/manufacturing/m3/historical/timeseries.html) | Monthly history from January 1992 across manufacturing industries. | New orders, shipments, unfilled orders and inventories for electrical equipment, computers/electronics and machinery; long control for bottleneck pressure. | Industry aggregates, not individual transformer/chip lead times or vendor backlog. Semiconductor series definition changed after April 2010; account for breaks and release vintages. |
| [Census international trade HS API](https://api.census.gov/data/timeseries/intltrade/imports/hs.html) | Monthly HS trade data; API coverage generally begins 2010/2013 depending on product/geography; longer annual files exist. | Value, quantity and weight of selected semiconductor, transformer, power equipment and networking imports can proxy supply flows. | Free API key required; commodity mapping and HS revisions matter; no importer/company identity and no direct delivery lead time. Validate each code’s start date before building a panel. |
| [EIA-860M monthly generator inventory](https://www.eia.gov/electricity/data/eia860m/index.php) | Monthly XLS vintages from July 2015; existing, proposed, retired generator records. | Quantify planned in-service dates, status transitions, MW, fuel and geography; build planned-versus-operational capacity changes. | Preliminary estimates can be revised without explanation; this is power generation inventory, not data-center interconnection or site capacity. Save each release vintage. |
| [EIA-860 annual inventory](https://www.eia.gov/electricity/data/eia860/index.php) | Annual generator/plant records 1990 onward (older forms before 2001). | Long-run generating capacity and generator-level location, technology, fuel and owner controls. | Annual, changing form definitions; annual retired/cancelled list is incomplete. Pair with monthly 860M from 2015 onward. |
| [EIA-923 plant operations](https://www.eia.gov/electricity/data/eia923/) | Monthly/annual plant operations; utility history to 1970, nonutility history to 1999. | Generation, fuel use/receipts, stocks and costs; useful for regional supply, utilization and fuel-stress features. | Monthly survey covers a subset of plants; annual final files cover more. Revisions and plant/prime-mover mapping matter; not demand from a named data center. |
| [EIA-930 hourly grid operations](https://www.eia.gov/electricity/data/eia930/) | Hourly system demand, forecast, net generation and interchange from July 2015; some added fields from July 2018. | Regional demand surprise (actual minus forecast), generation mix, imports and system stress. | Balancing-authority scale, not a node/site meter. Some subregional series cover only selected BAs; revisions and reporting delays matter. Free EIA API key or bulk downloads. |
| [EPA CAMPD/CEMS](https://campd.epa.gov/data/bulk-data-files) | Unit-hour monitored operations/emissions from 1995 for covered fossil units. | Capacity utilization, heat input and emissions; independently measures dispatch stress and maps to EIA plants. | Not every generator is covered; hourly wide queries hit caps, so use bulk files. Distinguish measured from substitute/apportioned data; it does not observe data-center load. |

### Useful orthogonal confirmations and controls

| Source | Span / frequency | Use and caveat |
|---|---|---|
| [ISO/RTO wholesale power data](https://www.pjm.com/markets-and-operations/etools/data-miner-2) | NYISO historical LBMP pages reach January 2000; ERCOT products can start 2010; CAISO market history generally from 2016; PJM APIs have shorter rolling archives for high-frequency LMP. | Actual locational congestion and scarcity prices. Select one market by the companies/sites’ geography. PJM requires an account and limits non-member API use; redistribution restrictions apply. ERCOT requires terms/account; retention varies by report. CAISO’s historical bulk downloader may incur AWS costs. Wholesale prices are not a data-center tariff or proof of site power access. |
| [LBNL Queued Up interconnection queues](https://emp.lbl.gov/queues) | Annual harmonized queue snapshot through year-end 2025. | Proposed generation MW, technology, geography, queue dates, status and time to operation; supports supply-pipeline/delay context. | Generation queue, not data-center load queue. Annual snapshots and some fields are estimated/imputed; independent projects and withdrawals matter. |
| [Philly Fed Manufacturing Business Outlook Survey](https://www.philadelphiafed.org/surveys-and-data/regional-economic-analysis/mbos) | Monthly diffusion series from May 1968. | Delivery times, unfilled orders and inventories are a long-run lead-time/backlog control. | Third District manufacturers; survey diffusion index, not days or a global semiconductor/vendor series. |
| [NY Fed Global Supply Chain Pressure Index](https://www.newyorkfed.org/research/policy/gscpi) | Monthly from 1997. | Broad global logistics/supply pressure control for component lead-time regimes. | Composite/macroeconomic control, not a physical backlog measure; avoid using revised values without vintage handling. |
| [NOAA Global Hourly / ISD](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database) | Hourly station observations, many stations with decades of history. | Temperature, wind and precipitation for heating/cooling demand, outages and renewable-output controls. | Station records and siting vary; weather is a confounder/context variable, not a data-center load observation. |
| [USGS Water Data APIs](https://api.waterdata.usgs.gov/) | Daily/continuous streamflow and water-quality station records, often decades but site-dependent. | Drought, river temperature and cooling-water stress near mapped power plants/sites. | Coverage varies by station; national thermoelectric withdrawal survey is only every five years. Requires careful location matching. |
| [USPTO PatentsView / research datasets](https://www.uspto.gov/ip-policy/economic-research/patentsview) | Roughly 40 years of patent/grant and pre-grant publication data. | Slow-moving proxy for innovation and competition in accelerators, cooling, power and networking. | Patent counts are not delivered capacity. Most applications publish around 18 months after priority; use public publication/availability time, not application date, as a signal. |
| [Ken French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html) and [ALFRED vintage API](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html) | Long daily/monthly factor series (factor-specific) and macro vintages. | Factor attribution and point-in-time macro controls; helps separate the proposed effect from market, size, value, momentum and rates. | Factors are benchmarks, not tradable fills. ALFRED history is series-specific; a current FRED download is not necessarily what was known then. |
| [NASA VIIRS Black Marble](https://viirsland.gsfc.nasa.gov/Products/NASA/BlackMarble.html) | Monthly nighttime radiance since 2012. | Optional site-level corroboration of construction/operations after coordinates are independently identified. | Radiance is not MW, commissioning or data-center-specific; lighting, weather and urban growth confound it. Not a first-wave input. |

### What can actually move off the paid providers

- **Massive filings:** SEC can supply underlying public filings and timestamps for a general company-level research panel. Keep Massive for the competition’s AI event tags/options challenge and cross-check its labels against the filing.
- **Databento:** public sources do not recreate consolidated equity trades, historical quotes or continuous L2/L3. For a daily event-study prototype, seek one licensed daily OHLCV source and test history/actions per ticker. Keep high-frequency depth out of the initial signal study.
- **Energy/physical context:** EIA + EPA + one geography-selected ISO/RTO can deliver long histories without Databento/Massive. Their strongest value is conditioning/control and measurable physical context; none directly reports hyperscaler site demand or an investable surprise by itself.
- **Direct construction and backlog context:** pair Census C30 (2014+) with M3 (1992+) and accession-level SEC observations. This creates a differentiated real-economy panel, but C30’s shorter aggregate history cannot validate a decade-plus company-level return effect on its own.

### Recommended ingestion order

1. Preserve SEC accession-level filings and their first usable availability time; build the manually verified company-event panel.
2. Add C30 data-center spending, M3 electrical/computer-sector orders/backlog and Census HS quantities as slow supply/demand context.
3. Add EIA-860M/860/923 and EIA-930, then EPA CAMPD, using EIA plant IDs and explicit state/BA/site mappings.
4. Add only one ISO/RTO series after mapping target firms and sites to its geography; NYISO offers the longest verified historical LBMP index among reviewed portals, while CAISO/PJM/ERCOT provide more recent locational detail with account, retention or retrieval-cost constraints.
5. Add weather, water, queue and patents only when a predeclared feature or confounder needs them. Keep each feature’s source, vintage, units, publication time, ingestion time and quality flags intact in Snowflake/TigerData.

This is a source inventory, not a strategy result. Count independent project shocks and exposure-linked issuers after constructing point-in-time panels; a long source history does not create independent AI-era delivery events.

## AWS Spot archive loaded to the research stores — 2026-10-03

**Source citation:** Eric Pauley (2026), *AWS Spot Price History* (2026-09 version), Zenodo
[record 23082767](https://doi.org/10.5281/zenodo.23082767), CC BY 4.0. The Zenodo API metadata
identifies the creator, version, open access, license and monthly file hashes. The archive
describes data equivalent to AWS EC2 `DescribeSpotPriceHistory`, with global AZ identifiers
replacing account-specific AZ names. It updates monthly and source event times can include the
last preceding price needed at a month boundary; preserve the provider's timestamp semantics.

**Downloaded/local:** 31 decompressed CSV files in ignored `data/aws-compute/csv/`; 1,592,024
observations total; 62 instance types; 2022-05-31 18:50:49 UTC through 2026-09-30 23:00:00 UTC.
The 2024-01 `.v2.csv` file was excluded from the load because it duplicates that month and carries
local ingestion metadata. March–June 2026 is absent. The archive supports spot-price study of
GPU/cloud instance types; it does not directly report GPU utilization, instance availability,
allocation fulfillment, on-demand prices, total compute supply, or named-company data-center
capacity.

**TigerData:** `public.aws_gpu_spot_prices`, verified with a read-only SQL query at 1,592,024 rows,
31 source files, the min/max dates above, and 0 observations in the missing Mar–Jun interval.
**Snowflake:** browser load completed successfully to
`VECTOR_RESEARCH.RAW.AWS_GPU_SPOT_PRICES`; UI reported 1,592,024 rows inserted. Post-load QA
returned 1,592,024 rows, 31 source files, UTC text timestamps `2022-05-31 18:50:49.000 Z` to
`2026-09-30 23:00:00.000 Z`, zero null ingestion times and zero observations in the Mar–Jun source
gap. This validates the imported timestamp representation, not historical provider availability
or the archive's economic completeness.

**Citation format for a slide/report:** `Pauley, E. (2026). AWS Spot Price History, version
2026-09 [Data set]. Zenodo. https://doi.org/10.5281/zenodo.23082767 (CC BY 4.0).` Cite these as
EC2 Spot prices, not as a complete compute-market price index. For derived figures preserve DOI,
version, access date, file-level source MD5s, transformation code and the missingness statement.

## Ornn benchmark repo — official repository reviewed 2026-10-03

[`Ornn-AI/ornn-benchmarking`](https://github.com/Ornn-AI/ornn-benchmarking) describes an
MIT-licensed standardized GPU benchmark CLI. Its README says it runs 30+ compute, memory and
interconnect benchmarks and emits Ornn-I/Ornn-T composites; the CLI guide documents machine-
readable JSON reports, system/GPU inventory, per-section statuses/metrics and opt-in API upload.
The documented scores combine memory bandwidth with FP8 inference performance (Ornn-I), and BF16
training performance with all-reduce bandwidth (Ornn-T).

**Possible use:** run on a controlled HiperGator or Vultr environment; pin repository commit,
benchmark version, CUDA/driver/toolchain, GPU model/count and run conditions; archive JSON with
our own source/version/collection metadata. If an AWS instance SKU can be reliably mapped to the
same GPU configuration, divide observed Spot USD/hour by a measured Ornn score to compare *current
measured performance per dollar*. Treat the score as a resource-cost normalization feature, not
a market-price observation or outcome label. A current benchmark cannot reconstruct historical
SKU performance after hardware changes, prove a cloud instance was available, or create a longer
backtest.

**Caveat:** reports may include GPU UUIDs and machine/software inventory. Store them internally;
do not use the CLI's `--upload` without team approval. No package was installed and no benchmark
was run during this audit; HiperGator access to the required NVIDIA tooling still needs testing.

## Onboarding order for the research stores

The archive above is the only non-market dataset currently loaded into both Snowflake and
TigerData. These loads were independent imports of the same local snapshot; there is no automated
bridge yet. The reviewed URLs below are a *source shortlist*, not download evidence. Onboard in
this order and keep only the high-cadence/as-of features needed by q in TigerData; Snowflake is
the canonical batch research and provenance layer.

| Order | Dataset to validate/load next | Canonical home | TigerData use | Gate before calling it usable |
|---|---|---|---|---|
| 1 | SEC EDGAR filings and numeric event ledger for PWR/ETN/EME/DLR | Snowflake RAW: accessioned source metadata/text; NORMALIZED: reviewed numeric fields, revisions, available-at rule | Compact event rows/features only, if q needs event-window as-of joins | Reconcile original accession/exhibit, filing timestamps, revisions and conservative public-availability lag; manually spot-check extracted values. Massive event tags remain separate enrichment. |
| 1 | Adjusted daily OHLCV and corporate actions for the same four names plus SPY | Snowflake normalized bars/panel | Selected bars in TigerData for q replay/as-of joins | Authenticated test confirms ticker/date coverage, adjustments, pagination, license and no silent truncation. No provider bars have yet been loaded. |
| 2 | Census C30 data-center construction and M3 manufacturing orders | Snowflake vintage-preserving macro/industry tables | Only if an as-of context series is needed by q; typically no need to duplicate national monthly data | Capture original release/vintage, series definition breaks/revisions and release time; document that aggregates are proxies, not company-level delivery data. |
| 2 | EIA-860M generation schedule and EIA-930 hourly grid operations | Snowflake versioned releases/observations | EIA-930 regional time series if q uses it; EIA-860M only compact revised state transitions | Validate vintage/revision behavior, BA/region mapping, publication lag and geography-to-company exposure. |
| 3 | ALFRED/FRED macro, EIA-923, EPA CAMPD, Census trade, grid queues, permits/hearings, water/weather, patents, satellite | Snowflake only after a named hypothesis/confounder requires it | Only if cadence and signal horizon warrant an operational mirror | Demonstrate incremental value and adequate usable history; otherwise remain a documented un-ingested source. |

For each ingestion, first fetch a small, declared sample and persist its source URL/file vintage,
request time, schema, units, checksum, row count, date span, missingness, license and timestamp
semantics. Compare the immutable local export with Snowflake and any TigerData operational copy.
Only then expand historical coverage. Use an idempotent manifest-keyed batch export/import for
the bridge; no secrets or live Snowflake dependency in q/strategy code. Thus: next is source
validation and a narrow filing+price panel, not bulk-loading every source in this inventory.
