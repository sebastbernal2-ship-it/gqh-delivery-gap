# Research alignment proposal

Status: proposed content for `docs/alignment.md`, not a replacement for its shared-owner review.
Owner: Vishnu. The [thinking log](../../thinking/vishnu-2026-10-03.md) owns the historical revisions.

## The question before the tools

Can an unexpected, publicly observable revision to delivery or capacity change a company's
future economics in a way that is not fully reflected in its price, after controlling for
ordinary earnings news, demand, market/sector exposures and implementation costs?

That is a candidate hypothesis. "AI is growing" and "power is scarce" are context, not alpha.
We need an identifiable cash-flow channel: revenue timing, cost absorption, utilization,
contract obligations, pricing power or substitution. The sign is conditional on contracts and
exposure, not a permanent label attached to a ticker.

## How to think about a new idea

1. Name the economic mechanism and the simplest alternative explanation.
2. Identify who bears the risk and why the price may fail to incorporate the information.
3. Find original dated observations of forecasts and revisions, not just today's facts.
4. Define a measurable variable, its units and what information existed at each decision time.
5. Audit independent events, comparable exposures and an executable instrument.
6. Write a falsifier, simple baseline and cost/risk specification before looking at returns.
7. Add complexity only when a development-period comparison justifies it; keep the OOS closed.

If one step fails, document the failure and narrow the question. More APIs or model parameters
do not repair missing identification. Do not demand artificial certainty; abstention is a valid
system output when the event is ambiguous or economically immaterial.

## Quantities that could express the mechanism

- Months by which a named project's forecast commissioning date changed, as of a public release.
- MW or contractual revenue attached to that schedule change, relative to firm scale.
- Revision to forecast revenue/margin for the same horizon, measured against prior public guidance.
- Share of backlog expected within twelve months, reconciled for acquisitions and scope changes.
- Signed-but-not-commenced lease commitments and their contractual timing, without calling all
  future starts delays.

These are not interchangeable. Backlog ratios can proxy expected conversion, but are also moved
by order mix and demand. A longer backlog can indicate success, not failed execution. A revision
against management's guidance is not automatically a surprise relative to market consensus.

## What earns confidence

Confidence accumulates through independently checkable gates: real observations; faithful
extraction; valid availability times; stable definitions; sufficient event coverage; a plausible
cash-flow transmission; results not explained by common factors; conservative costs/capacity;
and an honest chronological test. Report where confidence ends.

A language model may extract fields and quote provenance, but cannot certify its own labels or
manufacture missing values. An appealing distribution, a multimodal histogram or one strong
backtest is not an economic explanation. If a conditional distribution is modeled, assess
calibration, uncertainty and portfolio tails rather than just accuracy of the mean.

## Small first does not mean cherry-pick until profitable

The base case is for testing parsing, availability, accounting and reproducibility. Fix the
expansion rule using economic eligibility/data quality, not the returns from the pilot. Keep a
record of excluded companies/events and every tried variation, including negative results.

Moving from one company to a larger panel is an engineering scaling process, not a mathematical
proof by induction that the economic edge generalizes. New firms and regimes introduce new
assumptions which need their own tests.

## Advanced methods must have a job

- Typed extraction: reproducible fields plus provenance and semantic review.
- Optimal transport: compare matched delays to distribution distances; define censoring,
  cancellations, mass and project identity before using it.
- Fine-tuning: only after naming a real model, task, training rights, labels and held-out quality
  evaluation. Benchmark a simpler extractor first. Separate label evaluation from return tuning.
- Quantum/HPC: a bounded optimization or sampling problem with a classical baseline, meaningful
  objective and measured cost/quality. Simulator access is not access to quantum hardware.

Do not use hardware capacity as an argument for model necessity. Do not promise extreme HFT
performance from a quarterly signal or a generic cloud/database architecture.

## How disagreements are handled

State the claim, evidence, alternative and what would change your mind. Reopen decisions with a
reason rather than silently changing assumptions. Negative results should change the research,
not disappear from it. A coherent, falsifiable modest result is preferable to an unverified
system combining many unrelated ideas.
