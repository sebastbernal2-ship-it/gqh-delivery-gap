# Deep connections: how a chain is built, graded and killed

This is the method for connecting distant nodes, the way the salmon example works: sea temperature to
harvest to restaurant demand to price. The graph already carries the spine for it. Every edge in
`docs/scan/quantgraph.jsonl` has a `condition` (the assumption under which the link holds) and a
`falsifier` (the observation that would kill it), so a chain of edges is a chain of stated assumptions
the moment it is walked.

The discipline exists because a chain of plausible links always looks like insight and almost never is.
The failure mode is never the reasoning step that is obviously wrong. It is the link everyone nods at,
and the chain is usually sold on that link.

## The unit: a chain, never a correlation

A chain is an ordered set of links from an observable physical or institutional fact to a payer's cash
flow. It is not a correlation. A correlation between two series has no links, so it has no assumption to
test and no reason to survive out of sample. A chain earns attention only because each link can be named
and killed.

Every chain states: the anchor node it starts at, the outcome node it ends at, who pays, and why now.

## Link anatomy

Each link carries five fields, and the grader writes all five:

| Field | Meaning |
|---|---|
| `claim` | The link in one sentence. |
| `kind` | `constraint`, `causal`, `accounting`, `behavioral`, or `associative`. Associative links are allowed only as the last resort and are load-capped at `low`. |
| `evidence` | `E1` measured in this repo, `E2` measured outside with a named source, `E3` estimated from one observable, `E4` analogy or prior. |
| `load` | How much of the chain collapses if the link is false: `high`, `medium`, `low`. Load is about the chain, not the confidence. |
| `kill` | The cheapest observation that would show the link wrong. Not a restatement of the assumption, an actual test. |

A link with no `kill` is not a link, it is a belief, and the chain is rejected.

## The greatest assumption

A chain's **greatest assumption** is the highest-load link with the weakest evidence class. Ties break
toward the earlier link, because early failures kill more of the chain.

Everything else is commentary. The point of grading every link is so the chain can be spoken about in
one sentence: this works if the greatest assumption holds, and here is the test that decides it.

## The testability gate

A chain with a testable greatest assumption becomes a **candidate**: its kill test is named, its data
source is named, and the cost is stated in hours or days.

A chain whose greatest assumption cannot be tested with accessible data is a **watch item**. It is kept,
labelled, and never promoted. Watch items are not failures, they are honest parking, and they are
revisited when a data source opens.

A chain where the kill test is a priced-in claim about the market, such as "the market underreacts", is
automatically capped: our own event studies already returned null on the pricing side of delivery
revisions, so any chain that leans on that link inherits the null and must find its payer elsewhere,
usually on the supply side. This repo has learned that the payer question is the hard one.

## Forbidden moves

- Chaining association to causation without a link that names the mechanism.
- Two links that are the same cause wearing different hats: that is one link, and counting it twice
  inflates the chain.
- Using an `assumption:` node as evidence. Assumption nodes mark what must hold, never what is known.
- Reading the chain as a strategy before the expression step. The chain ends at a payer, not at a
  position.
- Dropping a chain link because it fails while keeping the conclusion. The chain dies whole, and the
  death is recorded, because a dead chain blocks the same idea from returning as new.

## Promotion ladder

1. **Chain**: graded links, greatest assumption, kill test. Lives in `docs/scan/connection-chains.jsonl`.
2. **Candidate**: greatest assumption testable with named data and bounded cost.
3. **Declared study**: own protocol, committed before the run, with its own null. The kill test becomes
   the study's primary test.
4. **Survivor**: the study holds, and the survivor still needs a fresh holdout before it is called out
   of sample, because both sealed windows here are spent.
5. **Expression**: the payer's instrument, net of costs, with the doubled-cost case reported.

## Artifacts and how to run them

- Method owner: this file.
- Surfacer, structural candidates from the graph:

      python3 scripts/analyze_connection_chains.py --manifest docs/scan/quantgraph.jsonl

  Writes `docs/scan/connection-chain-candidates.json`: short paths across layers between the complex's
  anchor nodes and everything else, with each edge's condition and falsifier attached.
- Graded chains: `docs/scan/connection-chains.jsonl`, one chain per line, schema enforced by the
  renderer.
- Renderer:

      python3 scripts/render_connection_chains.py

  Writes `docs/scan/connection-chains.md` and `.html`.

## What this method cannot do

It cannot turn a watch item into a trade, and it cannot verify an external link by wishing. When a link
is `E4`, the chain's job is to say exactly that and name the cheapest test, so nobody downstream mistakes
a familiar story for a measured fact.
