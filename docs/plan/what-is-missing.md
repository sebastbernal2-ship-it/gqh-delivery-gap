# What is missing between the measurement and an edge

Short answer: it is not mainly data. Three of the four missing pieces are analysis we can do with what is already
in this repo. One piece needs data, and only four specific datasets matter.

## The four missing pieces

| Missing piece | Kind | Status |
|---|---|---|
| A named forced payer, one sentence, per candidate | analysis | never done for any candidate |
| A concentrated instrument, with dilution checked | analysis over data we hold | partially, and it killed two candidates |
| A barrier statement, and what removes it | analysis | never written |
| The flow's economics measured from the book | code, plus history if available | running for one candidate |

Every candidate so far failed at piece one or piece two. The rank ordering matters: a relation with no forced
payer cannot be fixed by any amount of data.

## What each piece means in practice

**The forced payer.** Not who trades it, but who must, and why they cannot stop: a margin rule, an index rule, a
mandate, a contract, a capital limit, a queue, or the cost of doing the reading. If that sentence cannot be
written, the candidate is closed, and no dataset changes that.

**The concentrated instrument.** The transfer has to land on something holdable where it is not diluted by
everything else the issuer does. This is an identification job over data we already reach: segment revenue in
XBRL tells us which issuer's economics are dominated by one product line, fund holdings in EDGAR tell us who is
forced to buy, and share counts and float tell us whether a small book can matter.

**The barrier.** Why the transfer survives. Capacity ceiling, structural rule, capital charge, data or inference
cost, or the payer's inability to change behaviour. Without it we cannot tell an edge from a one time gap, and we
cannot date its death.

**The economics.** The flow's size against book depth and costs. The forward tape measures this directly for the
one candidate where the instrument is the object the flow clears in.

## The candidate classes, ordered by how forced the payer is

1. **Rule forced, instrument identical.** Perpetual liquidation. The payer is closed by the venue's own margin
   rule, and the instrument is the same object the flow clears in, so dilution is zero. Reachable today with the
   public API. Only the economics gate is open, and the forward tape answers it.
2. **Rule forced, instrument direct.** Index and mandate flows. Passive funds must buy at reconstitution and on
   inclusion, whatever the price. Reachable today: index announcement calendars are public, fund holdings are in
   EDGAR on N-PORT, and share counts and float are public. This class has never been examined in this project.
3. **Contract forced.** Whoever holds schedule risk under a fixed price obligation, and whoever has a completion
   covenant. Data is reachable in EDGAR exhibits and 8-K, and the missing capability is a document linking model,
   not a dataset.
4. **Capital forced.** Dealer inventory limits around a known event. Everything except the data exists. The
   dataset is historical option chains, an entitlement we do not hold.
5. **Procedural.** Interconnection queue position. The mechanism is measured and real. The dataset is the queue
   history, which is not reachable from this host.

## The data that is genuinely binding, and only this

| Dataset | Which class it unlocks | Who can get it |
|---|---|---|
| Historical option chains | capital forced, dealer hedging | an entitlement purchase, or a team member with market data access |
| Interconnection queue history | procedural, capacity timing | the pipeline owner, or a browser driven operator scrape |
| Historical perpetual book and liquidation print | rule forced, with history rather than forward only | the venue's public archive path, not yet found |
| Executed compute rental | relative value across compute inventories | a commercial dataset, or a physical counterparty |

## What can start today, with no permission and no purchase

1. **The index and mandate class.** Constituent and weights history from public announcements, holders from EDGAR
   N-PORT, and the forced flow is mechanical. Capacity is large, which is a poor fit for a small book, so this is
   a control candidate rather than a target.
2. **The compute instrument question.** The candidate failed gate four because the only expression looked like
   diversified provider equity. XBRL segment revenue can tell us which issuer, if any, carries one family's rental
   economics in its reported segments. If such an issuer exists, the gate reopens; if none exists, the candidate
   is closed on evidence rather than on assumption.
3. **Forced flow economics.** The tape continues, and the measurement is the conditional distribution after a
   liquidation trigger, against costs and capacity from the book.
4. **The concentration test for the delivery tail.** Which listed firms, if any, carry a single project as a
   material share of their economics. That is a join over filings and share counts, not new data.

## The honest possible outcome

If the constraint step is completed for these five classes and no forced payer can be named in one sentence for
any of them, then the answer is that no edge exists in this dataset at this capital scale. That is a result, not
a failure, and it is reportable with the same machinery that measured everything else. Stating that possibility
now is what keeps the search honest.
