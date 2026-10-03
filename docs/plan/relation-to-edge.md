# From a relation to an edge: the missing bridge

Correlation, association and causation are all relations. None of them is an edge. Confusing the two is why
several weeks of good measurement produced no trade. This states what each relation actually gives, and the six
steps that turn a relation into a rationale and then into a position.

## What each relation gives, and what it does not

| Relation | What it provides | Why it is not yet an edge |
|---|---|---|
| Association or correlation | a candidate, and a place to look | symmetric, no direction, no mechanism, nothing to act on |
| Causation | direction and a counterfactual: if A moves, B moves | may already be priced, may have no instrument, may be too small, and may not survive others acting on it |
| An **edge** | a repeatable, cost-surviving transfer from a counterparty who cannot avoid it | this is a different kind of object, and it needs a constraint, an instrument, a magnitude and a barrier |

The pattern is that relations tell you **where**; the edge lives in **who cannot avoid paying**.

## The six steps, in order, each with its gate

### 1. Mechanism: name the constrained counterparty

Not "who trades this" but "who **must**, and why can they not stop". Every durable edge in the literature and in
practice has one of these constraints behind it:

| Constraint type | Example | Why it produces a transfer |
|---|---|---|
| Rule or mandate | margin call, index membership, solvency requirement | the trade happens regardless of price |
| Contract | fixed-price obligation, take-or-pay, liquidated damages | one side absorbs a shock it cannot reprice |
| Capital or balance sheet | dealer inventory limits, capital charges | someone must hand risk to someone else |
| Procedure | scheduled rebalancing, funding resets, vesting | the flow is on a calendar, not on a view |
| Attention or processing | burying a fact in a filing or a monthly inventory | the price adjusts only when someone does the work |
| Latency or availability | the flow clears in seconds on one venue | only those present capture it |

**Gate**: if no constrained counterparty can be named in one sentence, there is no mechanism and the relation is
not worth another hour.

### 2. Flow: say whether the flow is price insensitive, scheduled, or mechanical

An edge lives in flow that does not respond to price. If the counterparty would decline the trade at a better
price, it is not forced, and the effect will be arbitraged.

**Gate**: describe the flow in one line, and state what would make it price sensitive.

### 3. Transfer and concentration

Say what moves between whom, in what unit: basis points of margin, a rent differential, a liquidation slippage, a
spread. Then say whether the transfer is **concentrated** on a few instruments or diffused across thousands. A
diffuse transfer cannot be captured.

**Gate**: a number, and a concentration statement.

### 4. Instrument: what do we actually hold

The relation must map onto something holdable, with the linkage stated: the equity of the party bearing the
constraint, the venue where the forced flow clears, an option that pays when a hedging mandate bites, or a
contract. If the only expression is "the equity of a large diversified firm", the transfer is diluted by
everything else that firm does, and the edge is usually gone.

**Gate**: name the instrument and the mechanism that links it to the transfer, and check the dilution.

### 5. Economics and capacity

Magnitude net of spread, impact, borrow, financing and fees, at a declared multiple of costs. Capacity from
depth and average volume, not from hope. Turnover, because a capacity-constrained edge dies from trading costs.

**Gate**: net magnitude, break-even cost, and the size at which the edge decays.

### 6. Barrier: why it survives

Name why nobody else takes it: capacity ceiling, structural rule, capital charge, data or inference cost, or the
payer's inability to change behaviour. Then name what would remove the barrier, because that is the falsifier.

**Gate**: one sentence of barrier and one sentence of what breaks it.

After those six, and only after, the test design applies: declared signal, declared horizon, state-conditioned
null, rate control across the full grid, specificity, and a sealed holdout with a named owner.

## Where our own work stopped

We built steps 0 and part of 1: relations, some of them measured well. We never ran steps 1 through 6 for any
candidate. Concretely, for the delivery chain we measured that revisions happen and that the disclosing firm's
price does not respond, and we never asked the question the mechanism demands: **which agent is forced to bear
the schedule risk, and what instrument is mechanically levered to it.** That is why the chain produced truths and
no rationale.

The same gap explains the compute finding. Ten independent inventories is a relation. It becomes a candidate only
when we can name a provider or lessor whose economics are concentrated in one family's scarcity, which is an
instrument question, and a reason that scarcity is not already reflected in its price, which is a barrier
question.

## The artifact this implies

A **constraint ledger**: one row per candidate relation, with the constrained counterparty, the constraint type,
the flow description, the transfer unit and its concentration, the instrument and its dilution, the economics,
the barrier, the falsifier, and the data needed. Relations we hold feed it. Candidates leave it when they fail a
gate, with the gate named.

That ledger is the missing middle between the node and edge map, which says what is connected, and the strategy,
which says what we hold. It is also what stops us building models of relations that have no payer.
