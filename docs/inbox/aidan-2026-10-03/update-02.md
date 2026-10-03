# Discussion update 02 — 2026-10-03

Owner: aidanq06. Source: expanded speaker-labeled discussion supplied by Aidan. This is a
research handoff, not a verified market-data report or approval of every remark in the transcript.
Speaker numbers are not reliably mapped to people; no individual assignments are inferred.

## Changes to carry forward

**Horizon:** The later discussion favors intraday holding and avoiding a five-second strategy.
This revises the earlier ten-session candidate, but does not specify entry, exit or an approved
horizon. Retain both in the reasoning history; do not silently present ten sessions as current
consensus. Intraday trading still needs a reason information survives ingestion and execution costs.
The next specification must choose one primary horizon before examining its performance.

**Data planning:** Start with the information needed, then map providers to it. The team wants a
source-by-source view of intended retrievals and alternatives, without allowing one vendor's catalog
to define the strategy. Link the existing provider audit; do not treat credentials as proof of coverage.

**Sizing:** A proposed smooth accumulation curve would increase exposure as a signal strengthens,
rather than use a single all-or-nothing threshold. This is a research candidate. Define what the
residual measures, its benchmark, horizon and past-only scale before translating it into a position.
A large residual may be noise, a structural break or omitted news; it is not guaranteed undervaluation.
No universal one-sigma boundary avoids HFT competition, and no residual licenses an unlimited bet.

**Work allocation:** The discussion wants filings, market data, strategy analysis and HiPerGator
work separated. Existing OWNERS.md remains authoritative. Do not assign people from ambiguous
speaker labels or create duplicate implementations while other contributors work.

## Required information before vendor selection

This is a requirements checklist, not a claim that the feeds have been downloaded.

| Information | Why needed | Acceptance evidence |
|---|---|---|
| Original filing, exhibit or announcement | Establish the economic event and prior expectation | Source passage, identifier, publication timezone/time, revisions and earlier comparable statement |
| Historical security identity and corporate actions | Map exposure to an actually tradable security | Listing eligibility, identifier mapping, splits/dividends and missing/delisted handling |
| Equity prices and volume | Measure outcomes at the chosen horizon | Feed/schema, actual time coverage, bar convention and adjustment policy |
| Appropriate benchmark returns | Separate common movement from the candidate signal | Matching calendar/horizon and past-only exposure estimation |
| Bid/ask and trades | Measure spread, price response and executable entry/exit assumptions | Venue/consolidation scope, event/receive times, quote freshness and trade-condition handling |
| Depth or order events, only if needed | Test a specific depth/replay question | Known schema, continuity and reconstruction checks; no claim of queue precision from aggregate depth |
| Financing, borrow and cost assumptions | Translate candidate returns to implementation economics | Sources, timing, conservative assumptions and sensitivity where data are absent |
| Contract/project quantities | Establish materiality and cash-flow exposure | Comparable units, ownership, effective dates and uncertainty; distinguish generation MW from compute capacity |

For every planned retrieval record provider, endpoint/dataset/schema, symbols, range, expected
rows/size/cost, entitlement status, alternative source, purpose and named owner. After retrieval
record actual coverage, pagination, hash, cost and defects. Review Massive and Databento together;
options coverage does not establish equity depth coverage. Bloomberg access at UF was discussed,
not checked here; reservation, product coverage, extraction and redistribution rights remain open.

## Reported pilot and timestamp problem

Participants described a small Databento request with an estimate around $0.20 and later charges
around $0.36. Neither receipt nor downloaded artifact was supplied to this update. These amounts
are conversation reports, not verified costs or a budget for the full study.

The proposed example concerned a Google/space-TPU announcement and related equities. Several dates
were debated; the discussion eventually mentioned September 24, 2026 at 3:45, without an established
timezone or original source receipt. Do not turn that into a verified event timestamp. A remembered
positive or negative daily return cannot establish the correct announcement date. Verify the first
public source, earlier dissemination and available trading session before requesting a narrow window.
Verify every candidate issuer's listing and economic exposure; a company mentioned in the story
need not have a directly tradable equity. No return or announcement claim is validated by this note.

The pilot's purpose is to inspect fields, clocks and download feasibility. A one-day chart is not
evidence of an event effect. Pair market data with the original disclosure and matched comparison
periods under an eligibility rule that does not depend on the observed price move.

## Risk and modeling clarification

Beta is not simply correlation: in a single-factor model it is covariance of asset and benchmark
returns divided by benchmark variance. Its estimate depends on horizon, window and information
available at the time. A benchmark suitable for equities need not explain a physical commodity.
Neither a beta hedge nor a smooth entry curve eliminates joint-tail, basis or liquidity risk.

For a sizing experiment, compare a simple capped baseline with a prespecified gradual policy using
the same signal and execution assumptions. Evaluate costs, turnover, adverse selection and joint
losses. More extreme residuals can justify abstention when uncertainty or liquidity worsens. Define
exit and invalidation as explicitly as entry. Do not adopt the transcript's casual all-in examples.

Precomputed event scenarios are a candidate classical decision framework, not inherently quantum.
Claims about what specific trading firms do were speculative. Keep the bounded quantum benchmarks
in methods.md separate from an unverified description of industry practice.

A MW materiality filter was suggested late in the conversation. No threshold was agreed and the
number of very large data centers was not verified. Capacity must be scaled to the affected firm's
exposure and available at the decision time; unit size alone does not identify a tradable shock.

## Compute and technical status

The team now reports successful HiPerGator access. The authoritative setup handoff is
[hpc/setup](../../../hpc/setup/README.md), which distinguishes owner-verified login from unverified
storage/job/API capabilities. This update does not claim a training job or quantum run succeeded.

The discussion maps typed schemas/signal/risk/accounting, market queries/replay and optional fast
parsing to different technical roles, and mentions Python positively. Preserve the existing
technical proposal; no definitive language-stack decision or new runtime implementation is recorded.
The deterministic reference and shared interfaces remain the integration boundary.

## Immediate decisions to make

1. Choose the event family and primary holding horizon; state the hypothesized pricing delay.
2. Complete the information-to-provider matrix and bound the first retrieval's cost.
3. Verify the pilot event's original timestamp and instrument eligibility before interpreting charts.
4. Retrieve filings alongside market data and publish manifests/results through their owners.
5. Define residual, risk cap, sizing comparator and invalidation before strategy testing.

Unrelated personal conversation, social posts, promotional stock claims and account details are
omitted. They are neither strategy instructions nor evidence.
