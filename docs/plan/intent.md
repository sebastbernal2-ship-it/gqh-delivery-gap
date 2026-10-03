# What this work is for, and how it must be reported

This is the owner of the working intent for this project. It comes from the captain's standing preferences, the
project's own alignment document, and the corrections given across sessions. Where it conflicts with anything
else in the repo, this file wins, and the fix is to change the other file.

## The vision, in one sentence

We trade the gap between a promise and a delivery, measured as a revision against an earlier public expectation.
Every tool is subordinate to that sentence.

## The order of work

1. **Factors.** What could move the gap, and who pays for it.
2. **Object.** What exactly is measured, in what units, with what clock, and with what availability time.
3. **Market implication.** Which holdable instrument expresses it, and how much dilution sits between the
   transfer and the price.
4. **Implementation.** Only now: code, execution, costs.

Strategy comes last. A strategy built before the first three steps is a guess with infrastructure.

## The method, seven steps

State the mechanism and its simplest rival. Name the counterparty. Name the earlier expectation. Define the
measurable quantity and its units. Audit the evidence. State the falsifier, the baseline and the costs **before
any returns**. Add complexity only when development evidence demands it.

Every arrow in a chain of reasoning is tagged observed, inferred, or untested. The tag is not decoration.

## The confidence ladder, never skipped

Documentation says capable, then entitlement, then downloaded, then a valid point in time panel, then a correct
label, then a calibrated forecast, then correct joint tails, then trades after costs. A claim can only be
reported at the rung actually reached, and never one rung higher. Realized outcomes are labels and never inputs.
Availability times bind. Identity must survive aggregation. Adequacy is independent shocks, not calendar length.
No advanced method is mandatory. Infrastructure is never an argument.

## How results are reported, in this order

1. The mechanism statement: what moved, who was forced, and what the transfer is.
2. The identification statement: what the measurement can support and what it cannot.
3. The falsifier, the baseline, and the costs.
4. The numbers, with the returns table **last**, and only ever as the tradability gate.

**A performance table is never the headline.** A Sharpe ratio answers one question, whether a candidate trades
after costs, and that question is only meaningful after the first three sections exist. Reporting a Sharpe first
inverts the whole method and is treated as an error of the same class as an untested claim.

## Standing bans

- No em dashes. Not in replies, docs, commits, or code comments.
- No process narration. No "let me", no "now I will", no announcing a tool call. Take the action, then report
  the outcome or the blocker.
- No filler, no repeated framing, no restating a point already made.
- No availability arguments. "It was already on disk" and "it has an API" are reasons to reject, never to choose.
- No persona. No nautical flavor, no roleplay, no honorific preamble. Plain speech only.
- No correlation presented as a cause. A noticed pattern is a lead, not a finding.

## What an edge is, in this project

Correlation, association and causation are relations. None of them is an edge. An edge is a repeatable,
cost-surviving transfer from a counterparty who cannot avoid paying. Six gates check it: the constrained
counterparty, the price-insensitive flow, the transfer and its concentration, the instrument without dilution,
the economics and capacity, and the barrier that explains why it survives. Relations tell you where to look.

The edge must be compatible with speed without speed being the edge itself, and its capacity shape must be one a
small book can matter in and a large book cannot scale into.

## Why the sealed test was reported wrongly

The sealed test ran correctly and was reported in the wrong order. It led with a returns table and a Sharpe
ratio, which puts a tradability number ahead of the mechanism, the identification, and the falsifier. The result
is the same either way, three nulls, but the presentation broke the order above. The record has been reordered so
the mechanism statements come first and the returns appear last as the tradability gate.
