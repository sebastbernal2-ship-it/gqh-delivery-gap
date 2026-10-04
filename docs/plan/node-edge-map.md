# The node and edge map: what exists, what is connected, and what has been measured

The instruments in the terrain map are how we look. This is what we are looking at: the objects, and the
relations between them, typed and directional, with the measurement status of each relation.

An edge here is a claim of the form **A relates to B in this specific way**, with a direction and a semantic
type. Correlation between two series is not an edge in this sense: it is symmetric, it has no mechanism, and it
cannot be acted on. The scan we ran measured symmetric co-movement, which is a degenerate relation, and that is
one reason it found nothing usable.

## The nodes

Twenty two declared, each with a representation, a clock, an availability rule, and a written blocker where one
exists. Nineteen carry a live representation. Statuses are honest: a node without a representation we can reach
is recorded as blocked rather than quietly dropped.

| Node | Family | Clock | Status |
|---|---|---|---|
| promise:power:planned-capacity-revision | promise | monthly | populated |
| promise:power:realized-delivery | promise | monthly | populated |
| promise:power:cancellation | promise | monthly | populated |
| promise:power:interconnection-queue-position | promise | monthly | **blocked** |
| firm:obligation:remaining-performance | firm | quarterly | populated |
| firm:obligation:unapproved-change-orders | firm | quarterly | thin, ends 2017 |
| firm:capex:hyperscaler-commitments | firm | quarterly | populated |
| grid:demand:balancing-authority | grid | hourly | populated |
| grid:generation:balancing-authority | grid | hourly | populated |
| water:drought:severity | water | weekly | populated, no payer |
| price:compute:rental | price | monthly | populated |
| price:compute:executed-rental | price | daily | **blocked** |
| price:power:spot | price | hourly | **blocked** |
| price:commodity:gas, copper, uranium | price | daily | populated |
| rate:treasury:ten-year | rate | daily | populated |
| price:equity:buildout, scarcity | price | daily | populated |
| disclosure:8k:material-agreement | disclosure | event | thin, four firms |
| positioning:perp:funding-rate | positioning | hourly | **blocked** for the macro markets |
| price:options:implied-move | price | daily | **blocked** |

## The edges, by measurement status

### Measured and rejected

| Edge | Type | Evidence |
|---|---|---|
| firm obligation revision to the firm's own price | affects | 382 firms, 4,634 events, no association at 1 to 20 sessions; placebo produced more nominal hits than the real data |
| project promise revision to a listed owner's price | affects | blocked by attribution: only 6.2 percent of slipped capacity has a listed large owner |
| drought to promise revision | drives | no effect, coefficient points the wrong way |
| supply chain pressure to promise revision | drives | 1.269 equipment heavy against 1.186 light, small and does not generalise |
| construction spending to promise revision | drives | within a rounding error of one |
| delivery times to promise revision | drives | 0.956 interacted, no out-of-sample gain |
| compute family price to other family price | combines with | measured as **independent**: median pairwise correlation of daily changes minus 0.01 |
| buildout equity basket to scarcity equity basket | combines with | strong, but it is one risk viewed twice, not a relation |
| promise revision count to commodity and rate series | co-movement | scan survivors were all asset co-movement or known macro links |

### Measured and established

| Edge | Type | Evidence |
|---|---|---|
| planned vintage to revision size | derived from | the state variable is a vintage difference, definitional |
| disclosure to public availability | precedes | 33, 56 and 94 days by field, joined on acceptance timestamps |
| promise age to revision hazard | drives | 23 percent at six months rising to 44 percent at one to two years |
| slippage to whole year moves | pattern | modal annual revision exactly twelve months |
| promise to cancellation | precedes | 711 cancellations against 3,451 departures from the planned sheet |
| firm promises to generator realisations | measures | 721 generators promised in 2015 and running by 2023, 64 percent late |

### Declared and never tested

| Edge | Type | Blocked by |
|---|---|---|
| promise revision to firm revenue timing | drives | needs project to firm mapping, which is the attribution ceiling |
| revenue timing to abnormal return | affects | the same, plus the horizon decision |
| compute scarcity to energised capacity | measures | no executed rental series; only provider policy prices |
| perpetual funding to price reaction | conditions, indicates | macro market history too short; tape only two hours so far |
| option implied move to any event | affects | no entitlement |

## The shape of the graph, read honestly

Three things stand out.

1. **One hub and a lot of satellites.** Almost every measured edge touches the promise or the firm obligation.
That is because our exploration followed one thread, not because the world is shaped that way.
2. **The price family is a clique of co-movement, not a set of relations.** Six price nodes correlate with each
other and with nothing else that we trust. Correlation inside the family tells us about shared risk, not about
mechanism.
3. **The most valuable edges are the untested ones**, and each is blocked by a specific missing thing: the
project to firm mapping, an executed compute rental series, a longer history on the macro perpetual markets, or
an option entitlement.

## What this implies for the next piece of work

The edge that would carry the most, and is closest, is **delivery to compute price**: a promise slips, capacity
arrives later, and compute rents for more until it arrives. It is the one relation where our two best measured
objects meet, where a payer is obvious (whoever rents compute), where the clock is hourly on the price side, and
where the only missing piece is an *executed* rental series rather than provider list prices. Everything else is
either attribution, entitlement, or a data source we cannot reach.

The second, cheaper one is inside the promise family itself: **revision tail to cancellation**, which uses nodes
we already hold and has never been tested.
