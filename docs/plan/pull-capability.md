# Can we pull what we need ourselves

Short answer: for public structured sources, yes, and we have proved it repeatedly. For the three datasets behind
a paywall, a raw cloud credential, or a bot wall, no. The single most valuable one turned out to be one credential
away, with a documented path, and our earlier failure on it was our fault for guessing keys instead of reading the
documentation.

## Correction: no AWS account is needed

I asked for an AWS key. That was wrong, and the challenge was right. The archive being requester pays on S3 only
means the bucket refuses anonymous callers. It does not mean S3 is the only route to the same bytes.

Free mirrors of the same chain are on a dataset host that serves over plain HTTPS, with no account and no billing:

| Mirror | Contents | Size |
|---|---|---|
| `gionuibk/hyperliquid-node-fills-by-block` | the archive's fill files, already converted from lz4 to parquet, named by the date they cover | 1,078 files |
| `gionuibk/hyperliquidL2Book-v2` | the L2 book archive, with a catalog file describing the layout | 76,990 files |
| `craftify2221/hyperliquid-fills-raw` | fills and account values, partitioned by date from 2025-10 | 1,908 files |
| `craftify2221/hyperliquid-builder-liquidation-panel` | a prepared liquidation panel with loss cut and exposure tables | 518 files |

The correct approach was the free mirror, not the paid bucket. Requesting a cloud credential would have added a
vendor, a card and an egress bill to reach data that is already published for nothing.

## What we pull ourselves today, with code already in the repo

| Source | What we get | Shape of the work |
|---|---|---|
| EDGAR | filings with acceptance timestamps, XBRL facts, and instance documents with their dimensional members, which is how the segment revenue probe ran | cached, tested, reusable |
| EIA | monthly 860M vintages, 930 hourly grid files | stdlib spreadsheet reader, no dependency |
| NOAA and the drought monitor | statewide monthly weather, weekly drought by state | endpoint quirks documented |
| Listed equities | daily bars | through the shared landings and a local reader |
| Sentinel-2 | imagery windows, read straight out of the COG with range requests | our own reader, no geotiff library |
| Shared landings | bars, 8-Ks, rates, M3 orders and unfilled orders, construction spend, delivery times, supply chain pressure, the GPU spot archive | read only through the pipeline CLI |
| The perpetual venue, forward | book, funding, open interest at a fixed cadence | running collector |

That list covers the top candidate's economics, the index and mandate measurement, the concentration join, and the
compute archive. None of it needs anybody's permission and none of it costs money.

## What needs one credential, and is otherwise documented and public

**The perpetual venue's own archive.** The documented paths are `s3://hyperliquid-archive/market_data/<date>/<hour>/<datatype>/<coin>.lz4`
and `s3://hyperliquid-archive/asset_ctxs/`. A third party indexes the same chain under `s3://hydromancer-reservoir`
with every perp fill and, separately, **liquidation fills per day from 2025-07-28 onward**.

That liquidation dataset is the forced flow candidate's history, which is the single most valuable dataset on our
list, and it is a documented requester pays path. It needs an AWS account and a small egress cost, plus `boto3` or
the AWS command line client. Neither is present in this environment: there is no `aws` binary, no credentials
directory, and no `boto3`. The `lz4` decompressor is present.

Our earlier 403s on this archive came from guessing keys. The documentation was there the whole time.

## What we cannot pull ourselves

| Dataset | Wall | Note |
|---|---|---|
| Historical option chains | entitlement | needs a purchase or a member with market data access |
| Interconnection queue history | bot wall and scripted portals | the national lab returns 403 to this host; one more honest attempt with a browser shaped request is worth making before we ask anyone |
| Executed compute rental | commercial | lowest value; the candidate it reopens is closed |

## Two items I had called data are ours today

The index and mandate flow, where announcements, holdings and bars are all public. The concentration join on the
delivery tail, where the data is held and the join was never built.

## The honest caveat about the word easy

We have the pattern and the code for public sources, so a new one is hours of work rather than minutes. Every
source so far carried its own quirk: a user agent rule, a path segment that silently returns the wrong month, a
nested classification that double counts, an archive that needed a ranged reader. Budget hours per source, not
minutes, and expect one surprise each.

## The ask

An AWS key with read access, or two documented commands run by whoever holds cloud credentials, unlocks the
liquidation fills and the L2 book for the forced flow candidate. That is the only dataset worth asking for right
now. Option chains come after, and the queue after one more attempt at the documented download.
