# Jev style probabilistic decision council on HiPerGator

Status: user supplied architecture direction, captured as a research and engineering proposal on
2026-10-03. This is not an approved trading thesis, an implemented system, a compute allocation,
or evidence of predictive value. It does not open or define an out-of-sample window.

## Objective

Explore a modular decision system built from independently trained open-weight specialists. Each
specialist should return a distribution over outcomes or actions, with uncertainty and calibration
information, rather than only a hard label. A council combines those outputs into a joint,
multidimensional distribution and supplies it to a separately defined decision policy.

The system should be judged by out-of-sample decision quality, proper scoring rules, calibration,
robustness, tail behavior, and end-to-end latency. Added model or compute complexity earns a place
only when it improves a declared objective over a strong baseline at comparable data and compute
budgets.

## Model foundation and specialist registry

Laya is the proposed open-weight starting point for a Jev-style System One model; Jev itself is
closed. The user identifies Laya as Apache-2.0. Before using or modifying it, verify the repository,
model-card, weight, architecture, and dataset licenses independently. Treat the code and weights as
a baseline to reproduce and extend, not as a fixed capability or a validated forecaster.

Investigate reproducing and extending its RLCD-style calibrated probabilistic training. Every
specialist must have a versioned record of its data, modality, information cutoff, horizon, regime,
features, target, objective, training recipe, calibration method, and supported decision type.
Candidate specialists can include text, time series, tabular, image/remote sensing, and classical
statistical models. Train independently where that helps isolate evidence and failure modes; avoid
assuming a larger ensemble is automatically better.

Specialist outputs should declare a common contract: event/outcome space and units, forecast time,
validity horizon, probability mass or density representation, conditional variables, missingness,
aleatoric and epistemic uncertainty where estimated, calibration metadata, model/data versions,
and a provenance reference. Retain dependence information when the specialist models joint outcomes.

## Council and downstream policy

The candidate flow is:

1. Run eligible specialists and statistical models in parallel.
2. Validate output schemas and information cutoffs; estimate uncertainty and calibration on separate,
   chronologically valid data.
3. Gate or weight specialists conditional on context, regime, coverage, uncertainty, and measured
   reliability. Include abstention when the evidence is weak or out of support.
4. Fuse evidence with benchmarked probabilistic methods. Preserve dependencies rather than treating
   correlated specialists as independent votes.
5. Produce calibrated joint and marginal distributions, including relevant correlations,
   conditional tails, and scenario sets.
6. Pass those distributions to an explicit downstream decision/portfolio/action optimizer with
   declared constraints, costs, risk limits, and utility. Keep forecasts and preferences distinct.

Bayesian models, factor and regime models, latent-variable/state-space models, Monte Carlo and
scenario simulation, dependence models, and branching decision trees are candidates. Select their
scope from the decision problem and compute budget. A tree's breadth or depth is not evidence of
better decisions; validate pruning, approximation, and calibration against bounded classical
searches.

## Hybrid quantum-classical research

Quantum methods are optional candidate specialists or feature generators. They do not replace the
classical council and are not presumed to improve accuracy. Start with simulators and equal-budget
classical comparisons; use a QPU only when access, queue/runtime, and a testable encoding are
available.

- Parameterized circuits and QGM/QCBM-style generators: test whether they improve held-out joint
  distribution fit, tail/scenario quality, or downstream decisions over classical generators.
- QAOA: investigate constrained discrete action, hedge, or portfolio choices against strong
  classical optimization methods using identical constraints and inputs.
- VQE: use only when the task is genuinely an appropriate Hamiltonian/eigenvalue problem.
- Quantum feature maps/kernels and variational classifiers: compare as alternative specialists,
  including data encoding cost and classical kernel baselines.
- Amplitude estimation or sampling: test only where its assumptions, oracle/loading costs, shot
  requirements, and end-to-end resource accounting make the method applicable.
- Quantum-assisted branching/search: define the search objective, solution quality, and stopping
  rule, then compare against classical simulation/search at matched budgets.

The experiment framework should record problem-to-formulation rationale; encoding, circuit,
depth, ansatz, parameters, measurements and shots; simulator/QPU backend and noise; trainability;
error mitigation; sampling error; runtime including data loading and queue where available;
resource usage; and results against equal-budget baselines. Search over circuit design only within
declared development data. Evaluate held-out distributions, calibration, tails, robustness and
downstream utility. An attractive simulator result alone is not evidence of quantum advantage.

## HiPerGator role and scaling gates

Potential separate workloads are specialist training, classical statistical fitting, calibration
and fusion comparison, hyperparameter/architecture search, large parallel scenario simulation, and
quantum simulation/benchmarking. Build small CPU fixtures first, then measure the bottleneck before
requesting GPU or distributed resources. Batched inference latency is an experiment to measure,
including model loading, data movement, council overhead, and fallback behavior; do not imply a
cluster queue supports an ultra-low-latency live path.

Reuse the contract, provenance, checkpoint and output rules in [Aidan's implementation proposal](../aidan-2026-10-03/implementation.md),
the HiPerGator status in [setup](../../hpc/setup/README.md), and the experimental method boundaries
in [Aidan's methods note](../aidan-2026-10-03/methods.md). These documents retain their existing
owners. This proposal does not establish that account access, storage, model downloads, or quantum
hardware access is available for a particular job.

## Evaluation gates

For every specialist, fusion method, and ablation, freeze the task definition and compare on the
same eligible chronological splits and inputs against simple, strong classical baselines. Keep
training, model selection, calibration, and final evaluation distinct. Follow the track's OOS rule
in [the brief](../brief.md); the OOS owner must be named before any OOS run is opened.

Report, as applicable:

- log loss, Brier score, CRPS or another justified proper score for the output type;
- reliability diagrams and calibration error, with binning/estimation uncertainty stated;
- decision utility after declared costs/constraints, alongside forecast scores;
- joint distribution and dependence quality, tail coverage/severity, and scenario diagnostics;
- regime, subgroup, missing-input and distribution-shift robustness;
- ablations for individual specialists, gating, fusion, uncertainty, and quantum additions;
- end-to-end latency, throughput, memory/compute use, and failure/abstention rates;
- normal and doubled costs wherever a trading decision is evaluated.

Do not select on accuracy alone or accept ECE without proper scores and reliability diagnostics.
Count and document every tried variant. Keep outputs reproducible from versioned configs and
input/model hashes; results quoted in the note must be generated under `results/` ownership rules.

## Decisions needed before implementation

1. Name the concrete decision target, outcome space, unit of analysis, horizon, and user of the
   forecast. The current competition study must first settle its financial hypothesis and scope.
2. Verify Laya artifacts, license coverage, training recipe, hardware needs, and permitted data.
3. Specify a minimum useful specialist and distribution interface, then claim each component path
   in `OWNERS.md` before creating code or HiPerGator jobs.
4. Establish data rights, point-in-time labels, chronological training/calibration/evaluation
   splits, and an OOS owner without examining OOS results.
5. Define baseline set, proper scores, calibration procedure, tail target, decision utility,
   ablations, and compute/latency budgets before a sweep.
6. Choose one small quantum question with a valid encoding and equal-budget classical comparator;
   defer broader method search until that pilot passes its formulation and reproducibility gates.

This proposal records an architecture to investigate. It makes no claim that Laya, an ensemble,
Bayesian fusion, massive search, or a quantum method will improve the team's trading result.
