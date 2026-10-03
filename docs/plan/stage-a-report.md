# Stage A report: what the factors do to delivery, and what the data supports

The question was whether the factors that decide building move the object of study. Three factor sets were
tested on the same object, the same panel and the same fitted hazard, and all three failed. This report records
the failures, the one structural finding, and what the data can and cannot carry.

## The object

The promise on a generator, tracked month by month. 6,407 generators, 27,069 project months, 2,190 of them
revision months. One row per project month at risk, the outcome being whether the promise moved that month.

## Factor set one: environment

Drought, precipitation, fuel, rates, market lead time and the state congestion proxies.

| Model | train AUC | test AUC |
|---|---|---|
| controls only | 0.6493 | **0.6290** |
| controls plus factors | 0.6646 | **0.6223** |
| placebo factors | 0.6424 | 0.6083 |

Factors made out of sample discrimination worse. Drought 0.93 [0.88, 0.96] and pipeline momentum 0.92
[0.87, 0.96] point the wrong way against the declared signs. The largest coefficients were the missingness
flags, so the small surviving effects are confounded with coverage.

And this set should never have been built: drought has no payer. It was chosen because it was fetchable. The
relevance gate in `edge-search.md` exists because of it.

## Factor set two: bottlenecks

Data centre, power and equipment construction spending, supply chain pressure, delivery times, congestion.
Every one of these names a payer.

| Model | train AUC | test AUC |
|---|---|---|
| controls only | 0.6515 | **0.6254** |
| controls plus factors | 0.6691 | **0.5681** |
| placebo factors | 0.6534 | 0.5528 |

Worse again, and the test likelihood degrades by half, which is overfitting rather than signal.

## Factor set three: differential exposure

Market wide monthly factors are identical for every project in a month, so a time trend absorbs them and a time
split cannot validate them. With month effects the identification moves to differential exposure: do longer
waits hurt equipment heavy technologies more than equipment light ones.

| Interaction with the equipment heavy group | odds ratio |
|---|---|
| delivery times | 0.956 [0.937, 0.986] |
| pipeline momentum | 0.898 [0.866, 0.916], wrong sign |
| supply chain pressure | 0.884 [0.786, 1.083] |
| construction spending, all three | within a rounding error of one |

Out of sample the factor model still loses to controls, 0.5560 against 0.6082, with 118 features against about
1,300 training events. The specificity check gives supply chain pressure 1.269 in equipment heavy against 1.186
in equipment light, which matches the mechanism, is small, and does not generalise. A hint, not a finding.

## What the failure means

The delivery object is close to unpredictable from market wide factors once technology, size, age and the
calendar are accounted for. Three factor sets failed on it. The likely reasons are structural: the object is
coarse, with a third of first revisions being one month nudges, and the drivers that matter are project, contract
and queue specific, none of which this data contains. The queue request in `docs/inbox/` is aimed exactly at
that gap.

## The one structural finding: compute is not one market

From the archive, daily median prices by instance family across the compute era development window, ten families
and 5,423 family days.

| family | days | median $ per instance hour | range |
|---|---|---|---|
| g5g | 670 | 0.35 | 0.16 to 1.35 |
| g3s | 556 | 0.28 | 0.23 to 0.40 |
| g4ad | 670 | 0.49 | 0.19 to 0.86 |
| g3 | 670 | 0.94 | 0.35 to 1.95 |
| g4dn | 670 | 1.23 | 0.27 to 2.36 |
| g5 | 670 | 1.46 | 0.78 to 2.71 |
| p3 | 522 | 4.31 | 3.67 to 15.02 |
| p3dn | 366 | 11.04 | 3.29 to 31.21 |
| p4d | 439 | 11.05 | 4.47 to 32.77 |
| p5 | 190 | 70.65 | 36.78 to 78.69 |

**The median pairwise correlation of daily price changes between families is minus 0.01.** Forty five family
pairs have overlapping history and they do not move together. Compute rental is not one market with one price;
it is ten markets with separate inventories, and each family's price moves on its own.

Two cautions, both material. The prices are per **instance hour**, not per GPU hour, so a p5 instance carrying
eight accelerators is not comparable in level to a single-accelerator family. And the archive is
provider-listed spot pricing, so it reads as provider pricing policy under inventory conditions rather than as
observed clearing prices between strangers.

**Why that is not yet an edge.** Dispersion plus independence is the raw material of relative value, and the
expression is the problem: there is no instrument on GPU rental we can hold. The edge would have to be taken
through the equities of compute owners and suppliers, and that is where the firm level tests already came back
null with a placebo that over produced. So the honest position is that compute pricing is a real object with
real structure and no direct way for us to hold it yet.

## What the data supports, and what it does not

Supports: the mechanism measurement, the survival and hazard structure of promises, the information lag, the
attribution ceiling, the compute price structure, and honest nulls on every association tested, each with a
control.

Does not support: any factor model of delivery, any firm level return association, any scan survivor that
belongs to the mechanism.

## What is needed next, in order

1. **Interconnection queue history**, requested in `docs/inbox/data-request-queue-2026-10-03.md`. It is the one
   factor with an obvious payer that we cannot reach.
2. **Wider 8-K coverage.** The loaded disclosures cover only four firms, 201 rows from 2022, of which fifteen
   are strategic transactions, and most of the window falls inside a frozen holdout. A deal family needs the
   wider chain, which is a pull through Vishnu's pipeline.
3. **An instrument for compute.** Until GPU rental has something holdable, the compute price can inform equity
   ideas but cannot be traded directly.
4. **A finer object for delivery.** Revisions of six months or more, or cancellations, on the same panel.
