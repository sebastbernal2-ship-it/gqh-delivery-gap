# Data access, checked rather than assumed

Verified 2026-10-03 by running each route, not by reading about it. The point of writing it down is that the
answer differs by layer, and the difference decides who has to do the work.

## The shared store, table by table

The store holds thirteen tables of its own beyond the Timescale internals. The ones that matter:

| Table | Rows | What it is |
|---|---|---|
| `public.gqh_source_records` | 151,198 | the general landing table, 21 sources, still filling |
| `public.gqh_eia860m_state_vintage` | **87,303** | a pre-aggregated state level vintage table with `available_at` dates, so it is point in time and ready to use. This was missing from my earlier inventory and it is directly useful to the delivery mechanism |
| `public.gqh_ingestion_manifests` | 90 | source provenance: url, licence, row count, retrieval time |
| `public.aws_gpu_spot_prices` | 1,592,024 | the compute price archive, with a gaps register beside it |
| `public.depth_events` | **0** | the order book event schema, provisioned and empty: symbol, segment, update ids, bids, asks, source path |
| `public.trade_events` | **0** | the trade event schema, provisioned and empty: price, quantity, buyer is maker, source hash |
| `public.observations` | **0** | the generic capture table: time, type, source, symbol, json payload |
| `public.source_manifests` | **0** | provenance for captures |

**The event tables are provisioned and waiting.** The order book, trade and generic observation schemas
exist for the q style capture to fill, and all three are empty. That is an architectural fact worth knowing: the
destination is ready, the capture is not.

## Reachable from this environment, right now

**The shared landing table, read only.** `public.gqh_source_records` through the pipeline command line client,
with credentials already configured. **21 sources, 151,198 rows**, and it is still filling: the same table held
137,439 rows earlier the same day. Contents, largest first: EIA-860M full and proposed for December 2024, EIA-923
PJM for 2024, FRED rates and market and industry, massive bars adjusted and unadjusted from 2016, M3 orders,
shipments and unfilled orders from 1992, EIA-860M proposed, SEC filings from 2015, Philadelphia Fed delivery
times, New York Fed supply chain pressure from 1998, massive dividends, massive 8-Ks, Census construction spend
from 2014, an EIA-930 PJM sample, ticker metadata, ticker events and splits.

**The compute price archive.** `public.aws_gpu_spot_prices`, 1.59 million rows, 62 instance types, with a
separate table recording the source gaps.

**Public sources we pull ourselves, with working code.** EDGAR filings, XBRL facts and dimensional instance
documents; EIA vintages and hourly grid files; weather and drought; daily bars; live option chain snapshots;
exchange published volatility history back to 1990; Sentinel-2 imagery through our own reader; the free mirrors
of the perpetual archive; and the venue's forward API through the running collector.

## Credentials, verified 2026-10-03

The Citadel component directory holds one environment file, mode 600, with two names: `FMP_API_KEY` and
`FRED_API_KEY`. Neither is exported into this workspace's shell, and the attended tooling for environment
migration reports that it cannot complete here. The file itself is readable, so the scripts can source it
directly, and it must never be committed: the repository is public and `make secrets` scans for exactly this.

Both keys were tested by using them.

| Key | Works | Does not work on this plan |
|---|---|---|
| `FRED_API_KEY` | full series history: 16,893 observations for the ten year yield, 945 for unemployment | nothing observed |
| `FMP_API_KEY` | company profiles, end of day price history, earnings and estimates, symbol search, an index list of 428 indices | **index constituents, ETF holdings, and institutional ownership are all restricted** on this subscription |

The restricted endpoints are the interesting ones, and EDGAR provides the authoritative free equivalent: a
tracking fund's own holdings filing is the primary source for what it must hold, and holdings are filed quarterly.
So the index and mandate class needs no vendor at all.

Still absent, and still the two things that block the layers listed below: a key for live massive pulls, and any
Snowflake credential. **No cloud key is needed**: the perpetual archive has free mirrors.

## Not reachable from this environment

| Layer | What is missing | What it means | The one line fix |
|---|---|---|---|
| Snowflake | no client, no connector, no credentials | anything loaded only into Snowflake is invisible here, even though our code for it is on main | mirror the tables into the landing table, or install the connector with credentials |
| kdb+/q | no interpreter, no data directory | the replay stack lives with whoever runs it | land the q inputs as parquet in the landing table, which q can read, or run the q work on its own machine |
| massive live pulls | no API key in this environment | we read what has been landed, but no new pulls: bars and 8-Ks stop where the last load stopped | put the key here, or have the pipeline owner pull and land the result |
| option chains, historical | paid product | forward snapshots are free, history is not | decide whether to buy, or collect forward |

## The practical rule this produces

**The shared landing table is the one channel this environment can read.** So anything the team wants used in
this workspace has to land there. Code without credentials is not access, and a dashboard is not a dataset.

## Two findings from the check itself

**Coverage is thin where it matters, and thick where it does not.** The 8-K disclosures hold 201 rows for four
firms, while the grid sample holds 24 rows for a single day. The bulk of the volume is EIA inventory rows and
long macro series.

**One source orders wrong.** Philadelphia Fed delivery times store the reference period as a text month and year,
so sorting that column by text puts September 1999 after April 2000. Any code reading it must parse the month
rather than order the text.
