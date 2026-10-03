# Fixing the blocked things, one by one

Every blocker on the list was re-tested rather than assumed. Most are fixable, three need something we cannot code
around, and each of those three has a substitute that changes the design rather than ending the question.

## The refusal, in the archive's own words

Requesting the documented archive path anonymously returns:

    Anonymous users cannot invoke requests against Requester Pays buckets.

That is a billing rule, not a permissions puzzle, so no code bypasses it. Requester pays means the caller pays the
egress, which means the caller must be identified, which means an AWS identity. Everything else about that archive
is public: the bucket name, the path layout, and a third party index that separates every perp fill from
liquidation fills by day.

**Where the key comes from.** The stack today is kdb+/q, Snowflake and TigerData, and none of those carries an AWS
identity. So the key must come from an AWS account. Two routes, both small:

1. A new free tier AWS account, an IAM user with read access to the two buckets, and the key either used directly
   or given to whoever runs the ingest pipeline. Cost is egress only, which for liquidation fills is cents.
2. The machine or cluster that already runs the pipeline, if it happens to sit on AWS, which would already carry an
   instance role and need no key at all.

The cleanest fit with the current architecture is route two, or route one with the pipeline owner holding the key
and landing the result as tables beside the other twenty one sources, which is how everything else arrived.

## Fixable by us, with no account and no purchase

| Blocker | The fix | Evidence it is fixable |
|---|---|---|
| Interconnection queue history | drive the operators' own portals with a browser instead of HTTP requests; the pages are scripted, not closed | we already carry a browser automation tool, and the national lab refusal looked like bot filtering, not a licence |
| The index and mandate flow | announcements, filed holdings and bars are all public; build the join and declare the test | nothing outside our reach is involved |
| The concentration join on the delivery tail | join filings, share counts and project records we already hold | the data is in the repo and in EDGAR |
| Historical volatility surface | the exchange operator publishes VIX and SKEW history back to 1990 as plain CSV files, both fetched successfully today, and the same site publishes term structure and futures files | two 200 responses, 473 KB and 203 KB |
| Option chains going forward | a live snapshot of the whole chain is available free through the market data library already installed: ninety eight call contracts for the front expiry of one large ETF, with strikes, open interest and implied volatility | fetched today |
| Executed compute rental going forward | the public index pages publish the daily print; history is private, forward is public | the same pattern as the tape |

## Fixable only with money

**Historical option chains.** No free source carries a usable history, and the historical archive is a paid
product. The honest substitute is a forward collection with the free snapshot, which turns the dealer hedging class
from a purchase into a matter of patience. The operator's public volatility indices cover the history at a lower
resolution, which supports a coarse version of the same mechanism.

## The pattern that fixes most of this

Two patterns, both already used in this repo:

1. **Forward collection when history is not purchasable.** The tape did this for the perpetual book. The same
   collector shape applies to option chains and to the public compute index: a snapshot a day, declared in advance,
   with the trigger or the statistic registered before the data arrives.
2. **A browser where the source is scripted.** The queue portals are built for humans in browsers. HTTP guessing
   failed, so the fix is to drive the page and read the table.

## What is actually left that nobody can fix

Only one thing: a historical option chain. It is a paid product and it stays paid. Everything else on the list is
either ours to build, ours to collect forward, or one small cloud credential away.
