# Advanced-method research retained from Aidan's discussion

Owner: aidanq06. Source review from 2026-10-02/03, not an independently reproduced benchmark.
This supplements the team's access audit; product documentation can change. Recheck before use.

## Jev and Laya

TypeSafeAI's Jev is a typed text-decision model. Laya is an independently developed open-source
alternative, not released Jev weights. They were identified in this conversation, contrary to the
other handoff's unresolved-name note. Candidate task: classify contractual conditions, changes in
deadlines, commitment versus aspiration and missing evidence. Keep arithmetic/date comparisons in
ordinary deterministic code. Fine-tuning and calibration need distinct chronological label sets.
Current model weights on old filings can carry later training knowledge; source-grounded extraction,
blinded human evaluation and genuinely forward evaluation are important limits, not a guarantee
that masking dates eliminates contamination. Neither cited text model is the satellite vision layer.

Sources: [Jev](https://docs.typesafe.ai/introduction), [model specifications](https://docs.typesafe.ai/models),
[limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13),
[Laya repository](https://github.com/NandhaKishorM/laya),
[model card](https://huggingface.co/convaiinnovations/laya).

## Compute-market evidence

The reviewed Ornn FAQ describes hourly H100 history from January 2025 and sparser earlier data;
B200 starts later. A benchmark price series is not a historical executable futures curve. Audit
methodology changes, publication timing, revisions, coverage and licensing. Reserved-contract
curves also reflect commitment, financing and product differences.

ICE's September 29 notice says planned H100/B200 contracts have no listing date yet; the upcoming
reference data include hypothetical settlements. That finding concerns these ICE contracts,
not every possible bilateral compute transaction or similarly named instrument.

Sources: [FAQ](https://data.ornn.com/faq), [methodology](https://data.ornn.com/methodology),
[forward curves](https://data.ornn.com/docs/forward-curves),
[ICE notice](https://www.ice.com/publicdocs/futures_us/exchange_notices/ICE_Futures_US_Exchange_Notice_ORNN_Compute_4Q2026_20260929.pdf).

## Quantum and distributions

Shared grid, hardware, financing and customers can make delays and losses dependent. Start with
transparent factor/dependency models and classical sampling. A bounded quantum generative model
can be compared on held-out joint distributions, tails and downstream risk decisions. Binning
and within-bin tails must be specified; coarse discrete states do not establish extreme-tail accuracy.

Superposition, interference and entanglement describe the model representation; the financial
observations remain classical. Entanglement or anticoncentration alone is not evidence of better
risk forecasts. GPU simulation is classical computation, not demonstrated quantum speedup.
QAOA is an optional constrained discrete hedge-selection experiment; compare against strong
classical solvers. VQE has no necessary task in the current strategy.

Sources: [financial generative modeling](https://arxiv.org/abs/2008.00691),
[quantum copula research](https://arxiv.org/abs/2109.06315),
[QAOA](https://arxiv.org/abs/1411.4028).

## SKR, optimal transport and volatility

The linked SKR paper concerns calibrated martingale models matching prescribed option-implied
marginals while remaining close to a reference process. That is a potential option-pricing/hedging
module, conditional on suitable surfaces and a relevant payoff. Risk-neutral calibration is not a
physical expected-return forecast. Matching marginals does not uniquely identify joint dependence.
Reported speed comparisons are paper-specific, not reproduced here. Keep this experiment separate
from a quantum generator so incremental benefit can be attributed.

Source: [SKR paper](https://arxiv.org/pdf/2609.39256).

## Execution, storage and mathematical scope

Hyperliquid L4 is a documented node-based order-book stream, not proof we possess continuous
historical queue replay. Validate listing periods, feed gaps, priorities, latency, funding and hedges.
The capacity signal and a standalone market-making strategy require different tests. q/kdb+ and
Tiger Data are candidate storage/query components, not evidence of a latency advantage.

Spectral methods may support factor attribution; harmonic methods may support seasonality or
numerical pricing. Langlands, affine Kac–Moody and grand-unification analogies currently have no
specified measurable job and remain outside the strategy.

Sources: [order-book reference implementation](https://github.com/hyperliquid-dex/order_book_server),
[historical archives](https://hyperliquid.gitbook.io/hyperliquid-docs/historical-data),
[UF access](https://docs.rc.ufl.edu/access/).
