# Vishnu's research and implementation handoff

Captured 2026-10-03 from the conversation supplied to this agent. Owner: Vishnu via his
documentation agent. Status: conversation context and design proposals; no promoted trading
thesis, live implementation or measured alpha is asserted here.

## Read this in ten minutes

**Taking over from another computer?** Start with the [ultimate continuation handoff](ultimate-handoff.md).
It consolidates the current state, prior revisions, verified data receipts, architecture, blockers,
and an ordered continuation plan. It is a dated snapshot, not a live cloud check; re-verify jobs,
quotas, and warehouse receipts before acting. It intentionally contains no credentials.

For the **current cloud data and Massive connectivity**, start with
[central ingestion handoff](central-ingest-handoff.md). The list below captures the earlier
research conversation; older load-status statements there are not the latest operational receipt.

1. [Thinking history](../../thinking/vishnu-2026-10-03.md): how the idea changed and why.
2. [Research alignment proposal](alignment-proposal.md): intuition, economic mechanism and evidence gates.
3. [Instrument and data plan](data-plan.md): what each candidate needs, and what depth buys us.
4. [Source audit](source-audit.md): access status, source receipts and unverified claims.
5. [Technical boundaries](technical-boundaries.md): proposed components, numerical contracts and compute separation.
6. [Next steps](next-steps.md): the small base case and the gate before scaling.
7. [Writing style](../../writing/style.md): how to express uncertainty and results.
8. [Snowflake path](snowflake-path.md): the adopted research/data boundary and first integration slice.
9. [Central ingestion handoff](central-ingest-handoff.md): verified shared tables, Massive API,
   source counts, operator workflow, and remaining gaps.
10. [Strategy feature contract](strategy-feature-contract.md): current feature readiness, the
    minimum point-in-time event/market schema, and gates before strategy claims.

Each topic has one owner document. Link instead of copying it into another summary. The source
audit owns provider/access details; the data plan owns what to collect; the technical proposal
owns component boundaries; the thinking log owns the conversation's evolution.

## What is genuinely the current direction

The user repeatedly asks for an equity-first, economically grounded, quantifiable strategy tied
to physical delivery/capacity constraints and the AI infrastructure ecosystem. Historical
expectations and revisions matter as much as price history. Innovation must be in the mechanism
and measurement, not in an ornamental collection of advanced methods.

PWR is the suggested first pipeline test, SPY a benchmark or possible hedge. Neither an approved
universe nor a long/short pair has been chosen. The candidate universe is documented in the data
plan. A quarterly/monthly economic signal and an execution engine operate on different clocks;
needing precise execution does not make the signal HFT.

## What this push does not do

- It does not implement connectors, backtests, fine-tuning or cluster jobs.
- It does not verify any participant credential, paid dataset entitlement or available credit.
- It does not open OOS data or assert the strategy works.
- It does not reactivate `archive/w0-delivery-gap` or modify the frozen track brief.
- It does not approve the whole original IDEA.md. Corrections are in the thinking log.
- It is not a complete verbatim transcript. Earlier assistant responses are absent from the
  supplied conversation; reasoning is reconstructed from user prompts, user-pasted context and
  recent visible responses. No missing response is fabricated.

## Repository status at capture

Main contains a collaboration shell, tests of that shell, and an empty thesis ledger. The
archive branch contains the earlier attempt. Some `memory/SHARED.md` entries describe its code,
cohort results and OOS dates; these are historical records, not main-branch capabilities or an
approved split for this revised equity study. Hippo was unavailable on the capturing device;
`make sync` succeeded with its documented fallback to reading committed memory.

To promote a research proposal, use the existing thesis ledger and regenerate CURRENT. To
adopt a costly design/universe/split decision, append the rationale to the decision ledger.
Do not edit generated CURRENT or historical proposals to make them look retrospectively correct.
