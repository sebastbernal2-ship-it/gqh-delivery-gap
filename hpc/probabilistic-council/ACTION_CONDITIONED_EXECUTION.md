# Action-conditioned Jev execution prototype

The primary implementation now uses [movement risk with analytical costs](EXECUTION_RISK.md).
It learns uncertain future movement and adds currently known snapshot/fee costs
exactly. The scaffold below is retained for later action-conditioned fill/impact
research; it has no valid realized-cost training dataset. Its candidate-axis
indexing is corrected and tested against per-action inference. This change does
not make current midpoint labels into realized execution cost.

## Intended prediction

Given a proposed order and the market state known at decision time, predict the
distribution of that order's realized net execution cost. The strategy proposes
the trade; this model estimates execution risk and can support a later decision
to size, wait, reprice, or reject it. It does not generate alpha or choose an
order policy by itself.

The first prototype consumes the existing `16 x 24` market-state sequence plus
one action vector with the following stable feature order:

| Feature | Meaning |
|---|---|
| `side_buy`, `side_sell` | One-hot order direction |
| `order_marketable`, `order_passive` | One-hot order style |
| `log_size_over_top5_depth` | Log order size relative to displayed top-five depth |
| `aggressiveness_bps_scaled` | Signed distance from same-side touch; positive means more marketable |
| `urgency_0_to_1` | Declared urgency score in `[0, 1]` |
| `log_horizon_seconds_scaled` | Log-scaled intended completion/markout horizon |

The model emits ordered 10th, 50th, and 90th conditional quantiles. A training
dataset must define the scalar target precisely, including reference price,
fees, fill policy, completion horizon and sign convention. The recommended
target is net implementation shortfall in basis points from the decision-time
midpoint through the declared completion and markout window. Quantile loss is
used to avoid imposing arbitrary bins on a continuous cost outcome.

## Data gate before training

The existing BTC cache cannot train this model: it has no action vectors or
order-conditioned execution-cost labels. Its current observed midpoint
excursions remain useful as a state-only baseline, but must not be relabeled as
realized execution cost. Do not train or publish action-conditioned metrics
until the following inputs can be reproduced from timestamped data:

1. A precise decision-time book and the proposed order (side, size, type, price,
   urgency and horizon).
2. For marketable orders, a deterministic book-walk replay for executable VWAP,
   with fees and the policy's latency assumption stated explicitly.
3. For passive orders, defensible fill/queue observations and cancellation rules.
   L2 snapshots alone do not identify queue position or individual fills.
4. A future markout path after execution, with stale/gapped intervals rejected
   rather than filled or treated as zero.
5. Exchange and receive clocks, source completeness checks, and a point-in-time
   availability rule. Current retrospective timestamps are not verified live
   receipt clocks.
6. Whole-session chronological roles, purged label maturity, and an untouched
   final evaluation block with multiple sessions.

## Prototype status and next experiment

`execution_action_model.py` implements a compact shared temporal encoder, an
explicit action encoder, and an ordered quantile head. It can score a set of
candidate actions against one state in one forward call, so the state is
encoded once and action alternatives are evaluated as a batch. Its tests check
the interface, quantile ordering, action dependence, finite gradients and
invalid input rejection. This is a model-contract prototype only; there is no
trainer, action dataset, execution replay or performance claim yet.

Once the data gate is met, compare the action-conditioned model with a
training-prevalence reference, a depth/OFI regression baseline, and a compact
causal neural baseline under identical session splits and label definitions.
Report quantile loss and interval coverage alongside cost calibration and
policy utility after fees and latency stress. Keep model selection on earlier
validation sessions; do not use the final block to tune thresholds or variants.

The current two-second resampled BTC inputs and 5/15/60-second proxy horizons
are seconds-scale research. They do not demonstrate millisecond HFT latency.
HiPerGator remains the offline model-training environment; serving latency must
be measured on the intended execution host. Quantum methods and large councils
remain deferred until this small classical model shows stable incremental value.
