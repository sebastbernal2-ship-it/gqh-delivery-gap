# Data priority, corrected

The earlier list ranked the four datasets by how much each unlocks. That ranking is wrong for sequencing, because
the top candidate needs no new dataset at all, and two of the items I called data are analysis. This is the order
that follows from the market map.

## Nothing new is needed for the first candidate

Forced liquidation on the perpetual venue. The payer is closed by the venue's own margin rule, the instrument is
the object the flow clears in, and the capacity is measured. What is missing is **time on the tape and the
measurement**, not a dataset. Two hours of tape gave zero triggers across four markets, which is a frequency
finding rather than a failure, and it says the test needs more hours or a wider set of markets. The only dataset
that would shorten this is the venue's own historical archive, and finding its path is a lookup, not a purchase.

## The order

| Rank | Item | Kind | Unlocks | Who |
|---|---|---|---|---|
| 1 | The venue's historical book and liquidation archive path | lookup | the first candidate's history in one pass, instead of forward tape over days | anyone, minutes of searching |
| 2 | Wider 8-K coverage through the shared pipeline | pull, already owned | the contract forced class, which cannot be tested on four firms and 202 rows | the pipeline owner |
| 3 | Historical option chains | entitlement | the dealer hedging class, the last concentrated instrument with a capital forced payer | a member with market data access |
| 4 | Interconnection queue history | acquisition, not reachable here | the procedural class, and the missing driver for the delivery tail | the pipeline owner, or a browser driven operator scrape |
| 5 | Executed compute rental series | commercial | reopens the compute candidate that closed on its instrument | optional, lowest value |

## Two things I called data that are analysis

**The index and mandate flow.** Everything needed is public: the provider's index announcements for effective
dates, fund holdings filed with the regulator for size, and daily bars for the flow itself. It needs code and a
declared test, not a purchase. This is the cheapest remaining measurement, and the instrument is the one other
place where the transfer stays whole.

**The concentration test on the delivery tail.** Which listed firms carry a single project as a material share of
their economics is a join over filings, share counts and project records. The data is held; the join has never
been built.

## What the sequencing means

The two datasets that need money or another party, option chains and the queue, are third and fourth. The first is
a lookup, the second is a pull the team already has the pipe for, and the next real measurement after the tape is
the index flow. Nobody should be buying anything before those are done.

## What runs while data is pulled

1. **Forced flow economics** on the running tape, with the trigger frequency and the conditional distribution
   after a trigger, against costs and capacity from the book.
2. **The index and mandate measurement**: effective dates, forced quantity, and what the flow does to the added
   name around the effective close.
3. **The concentration join** on the delivery tail, which decides whether any firm is a usable instrument for the
   mechanism we measured.
