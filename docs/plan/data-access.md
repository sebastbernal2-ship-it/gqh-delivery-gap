# Data access, checked rather than assumed

Verified 2026-10-03 by running each route, not by reading about it. The point of writing it down is that the
answer differs by layer, and the difference decides who has to do the work.

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
