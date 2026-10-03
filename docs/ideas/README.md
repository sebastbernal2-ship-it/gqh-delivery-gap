# The idea graph

Abstract ideas, kept because they are worth keeping, with the connections between them and an
honest label on whether each one touches anything we measure. The graph is
`graph.jsonl`; this file is generated from it by `make ideas`, so do not edit it by hand.

**61 ideas, 62 links.** 51 name something in the study. 9 are kept without an attachment, each with a stated reason, because a graph of only useful things is not a graph of ideas.

## Directions: where an edge could actually live

An idea is a tool. A direction is a program, so each one carries who pays, why it persists, what it would run on, and what would kill it.

### Cascades as threshold processes

Model forced liquidation as many accounts accumulating loss until a margin threshold fires, and test the clustering and avalanche structure that follows.

- **status**: declared
- **rationale**: The flow is price insensitive by rule rather than by opinion, and the venue publishes the book. Speed is needed to be present, and the edge is the conditional distribution of what happens after the threshold, which is a modelling problem rather than a speed problem.
- **needs**: a high frequency forward tape of book, funding and open interest, collectable now through the public API; the historical book archive, which needs the correct path or credentials
- **capacity**: bounded by book depth, so a small book can matter and a large one cannot scale into it
- **falsifier**: after costs, post trigger reversion is absent once the trigger is conditioned on, or cascade paths are fully anticipated
- **next**: start forward collection and pre-register the trigger rule
- **uses**: `lif-model`, `hawkes`, `point-processes`, `jump-diffusion`, `extreme-value-theory`
- **measures**: `perp:funding-rate`

### Distributional mispricing as a transport distance

Measure the distance between our conditional distribution and the market implied one, and treat that distance as the mispricing signal.

- **status**: data-blocked
- **rationale**: A price is a point, an option surface is a distribution, and the difference between our distribution and the market's is measurable with monotone transport rather than with a point forecast. This is where the transport and fast calibration work attaches.
- **needs**: historical option chains, which need an entitlement we do not hold
- **capacity**: option liquidity concentrates in large names, so capacity would be large and the edge would need to be correspondingly strong
- **falsifier**: transport distance between model and market has no relation to subsequent outcomes once the market's own dynamics are controlled for
- **next**: decide on an entitlement; nothing else here can start
- **uses**: `optimal-transport`, `knothe-rosenblatt`, `martingale-optimal-transport`, `stochastic-local-vol`, `pomdp`, `hjb`
- **measures**: `options:implied-move`, `compute:rental`

### Physical construction progress from satellite imagery

Measure whether a project is actually being built from imagery, which is an independent read on delivery that depends on nobody's disclosure.

- **status**: running
- **rationale**: The attribution ceiling is 6.2 percent because exposure lives in documents nobody publishes. A physical measure sidesteps the disclosure question entirely: a site either has foundations, steel and switchgear or it does not. First probe, eight labelled sites at ten metre resolution: brightness change was noise, and texture change correlated +0.72 with months of slip, which is a reason for the next probe rather than a result, especially with four features tried on eight sites.
- **needs**: public satellite imagery, Sentinel and Landsat, free and global; a labelled sample of known delivery outcomes to calibrate the vision model
- **capacity**: site specific and labour heavy, so a small book is a natural fit and a large one cannot be built from it
- **falsifier**: imagery derived progress adds nothing over the published schedule, or it cannot be scored reliably against known outcomes
- **next**: pre-register the texture feature and run thirty to fifty labelled sites, because the first probe on eight sites pointed the right way and eight sites cannot settle it
- **uses**: `vlm`, `contrastive-learning`, `tda`, `neural-operator`
- **measures**: `power:planned-capacity-revision`, `power:realized-delivery`

### Promise survival as a hazard rate

Replace the modal twelve month slip with a survival curve: how long a published promise lives before it is revised, by technology, region and vintage.

- **status**: declared
- **rationale**: A hazard rate is a strictly better object than a mean, and it is measurable on data we already hold. It also states the mechanism in the form a model can consume.
- **needs**: the existing monthly vintages, already downloaded
- **capacity**: not a trade by itself: it sharpens the mechanism section and the state variable
- **falsifier**: survival times are memoryless within technology and region, so there is no schedule structure worth modelling
- **next**: build the per generator promise series across vintages and estimate the hazard
- **uses**: `persistence-theory`, `point-processes`, `extreme-value-theory`, `active-learning`
- **measures**: `power:planned-capacity-revision`, `power:cancellation`

### Protocol formalisation with checked invariants

Write the execution and risk protocol as a specification whose invariants are checked, covering exposure limits and holdout discipline.

- **status**: declared
- **rationale**: The invariants that matter are not about alpha. They are that the exposure bound is never exceeded, the holdout is never touched before the sealed test, and a signal is never acted on twice. Those are the failures that would invalidate the whole record.
- **needs**: the engine interface, which is being built separately
- **capacity**: not a trade: it protects every other direction from a silent violation
- **falsifier**: a specification that never catches a real violation is overhead, so it must be tested by injecting one
- **next**: specify the holdout guard and prove it rejects a seeded violation
- **uses**: `tla-plus`, `decision-theory`, `dec-pomdp`
- **measures**: `obligation:remaining-performance`, `treasury:ten-year`

## Mathematics

### Affine Kac-Moody algebras

Infinite dimensional symmetry algebras with central extensions. *kept without an attachment.*

- kept without an attachment: nothing in this problem is a representation of an affine Kac-Moody algebra
- combines with `langlands`

### Delay differential equations

Dynamics whose present rate depends on a past state. *attached.*

- touches: `power:realized-delivery`

### Extreme value theory

Models the tails rather than the body of a distribution. *attached.*

- touches: `power:spot`
- combines with `hawkes`
- combines with `random-matrix-theory`

### Harmonic analysis

Represents functions as superpositions of waves, and studies what that preserves. *attached.*

- touches: `power:planned-capacity-revision`

### Hawkes processes

Self exciting arrivals, where each event raises the chance of the next. *attached.*

- touches: `demand:balancing-authority`
- combines with `extreme-value-theory`
- combines with `jump-diffusion`
- combines with `lif-model`

### Information theory

Quantifies dependence, transfer and coding cost, beyond linear correlation. *attached.*

- touches: `obligation:remaining-performance`
- combines with `tda`

### Jump diffusions

Continuous drift with discontinuous arrivals, the classical cascade formalism. *attached.*

- touches: `power:spot`
- combines with `hawkes`

### Knothe-Rosenblatt rearrangement

The monotone transport map between distributions, in one dimension or by triangular composition. *attached.*

- touches: `compute:rental`
- supplies a method for `stochastic-local-vol`

### Langlands program

Conjectural bridges between number theory, representation theory and geometry. *kept without an attachment.*

- kept without an attachment: nothing here is a modular form, and no measurement depends on one
- combines with `kac-moody`

### Martingale optimal transport

Transport constrained by a martingale condition, which prices model free bounds. *plausible, gated.*

- touches: `options:implied-move`
- supplies a method for `stochastic-local-vol`

### Optimal transport

Moves one distribution onto another at least cost, and that cost measures their difference. *attached.*

- touches: `compute:rental`
- combines with `tensor-networks`
- specialises `knothe-rosenblatt`
- specialises `martingale-optimal-transport`

### Persistence theory

Summarises the shape of data across scales by the birth and death of features. *attached.*

- touches: `power:cancellation`
- combines with `point-processes`

### Point processes

Models event arrivals in continuous time, including self excitation. *attached.*

- touches: `demand:balancing-authority`
- combines with `persistence-theory`
- is inspired by `lif-model`
- specialises `hawkes`

### Quantum amplitude estimation

Quadratic speedups for estimating expectations, in theory. *kept without an attachment.*

- kept without an attachment: it needs quantum hardware to mean anything
- combines with `mcmc`
- combines with `tensor-networks`

### Random matrix theory

Describes the eigenvalue statistics of large noisy matrices, such as covariance estimates. *kept without an attachment.*

- kept without an attachment: our covariance estimates are too small to have interesting spectra
- combines with `extreme-value-theory`
- combines with `spectral-theory`

### Rough volatility

Volatility whose paths are rougher than Brownian, with a fractional driver. *kept without an attachment.*

- kept without an attachment: no roughness evidence has been established in our series, so it is unfalsified decoration
- combines with `neural-operator`
- combines with `stochastic-local-vol`

### Spectral graph theory

Reads a graph's connectivity from the spectrum of its Laplacian. *attached.*

- touches: `equity:buildout`
- combines with `tda`

### Spectral theory

Decomposes a series or an operator into frequencies or eigenmodes. *attached.*

- touches: `power:planned-capacity-revision`
- combines with `random-matrix-theory`
- generalises `harmonic-analysis`
- specialises `spectral-graph-theory`

### Stochastic local volatility

Combines a local vol surface with a stochastic driver to fit both smiles and dynamics. *plausible, gated.*

- touches: `options:implied-move`
- combines with `rough-volatility`

### Tensor networks

Compressed representations of high dimensional states or distributions. *kept without an attachment.*

- kept without an attachment: no distribution here is high dimensional enough to need compression
- combines with `amplitude-estimation`
- combines with `optimal-transport`

### Topological data analysis

Studies shape and connectivity of data sets as invariants. *attached.*

- touches: `power:planned-capacity-revision`
- combines with `information-theory`
- combines with `renormalisation`
- combines with `spectral-graph-theory`
- combines with `vlm`

## Methods

### Active learning

Chooses the next observation to reduce uncertainty fastest. *attached.*

- touches: `capex:hyperscaler-commitments`
- specialises `design-of-experiments`

### Bayesian model comparison

Posterior odds or inclusion probabilities over competing structures. *attached.*

- touches: `obligation:remaining-performance`
- combines with `fdr`

### Causal inference

Identification of effects rather than associations, with explicit assumptions. *attached.*

- touches: `power:realized-delivery`
- requires `do-calculus`
- requires `scm`
- specialises `difference-in-differences`
- specialises `instrumental-variables`
- specialises `synthetic-control`

### Contrastive learning

Learns a representation by pulling similar pairs together and pushing others apart. *plausible, gated.*

- touches: `8k:material-agreement`
- combines with `vlm`

### Control theory

Feedback, stability and delay in dynamical systems. *attached.*

- touches: `power:realized-delivery`
- requires `state-space`
- specialises `delay-differential`

### Design of experiments

Chooses observations so that effects are identifiable. *attached.*

- touches: `power:planned-capacity-revision`
- combines with `fdr`

### Difference in differences

Compares changes across treated and control groups under a parallel trends assumption. *attached.*

- touches: `capex:hyperscaler-commitments`

### Do calculus

Rules for turning interventional queries into estimable expressions. *plausible, gated.*

- requires `scm`

### False discovery rate control

Bounds the expected share of false positives among the accepted set. *attached.*

- touches: `power:planned-capacity-revision`
- combines with `bayesian-model-comparison`
- combines with `design-of-experiments`

### Finite expression method

Learns dynamics as a finite expression, with complexity controlled. *attached.*

- touches: `demand:balancing-authority`

### Instrumental variables

Isolates variation in a cause that is plausibly unrelated to the outcome error. *attached.*

- touches: `commodity:copper`

### Kalman filtering

Optimal linear filtering of a latent state. *attached.*

- touches: `commodity:gas`

### Kolmogorov-Arnold networks

Networks whose edges carry learnable univariate functions. *attached.*

- touches: `compute:rental`
- combines with `mixture-of-experts`
- combines with `neural-operator`
- combines with `symbolic-regression`

### Markov chain Monte Carlo

Samples from a posterior that cannot be written in closed form. *attached.*

- touches: `obligation:remaining-performance`
- combines with `amplitude-estimation`
- combines with `variational-inference`
- supplies a method for `bayesian-model-comparison`

### Mixture of experts

Routes inputs to specialised sub-models. *plausible, gated.*

- touches: `compute:rental`
- combines with `kan`

### Neural correction operator

A learned correction on top of a structural solver, as used in impedance tomography. *attached.*

- touches: `obligation:remaining-performance`

### Neural operators

Learns a map between function spaces rather than between points. *plausible, gated.*

- touches: `demand:balancing-authority`
- combines with `kan`
- combines with `rough-volatility`
- specialises `neural-correction-operator`

### Particle filtering

Sequential Monte Carlo for nonlinear, non Gaussian state estimation. *attached.*

- touches: `compute:rental`
- requires `mcmc`

### State space models

Latent state evolving with noisy observations, and filtering of it. *attached.*

- touches: `obligation:remaining-performance`
- specialises `kalman`
- specialises `particle-filter`

### Symbolic regression

Searches for an explicit equation rather than a fitted function. *attached.*

- touches: `compute:rental`
- combines with `kan`
- specialises `finite-expression-method`

### Synthetic control

Builds a counterfactual from a weighted combination of untreated units. *attached.*

- touches: `equity:scarcity`

### Variational inference

Turns inference into optimisation over a tractable family. *attached.*

- touches: `compute:rental`
- combines with `mcmc`

### Vision language models

Read images and documents jointly, as text conditioned on pixels. *attached.*

- touches: `8k:material-agreement`
- combines with `contrastive-learning`
- combines with `tda`

## Systems

### TLA+

A specification language with machine checked temporal invariants. *attached.*

- touches: `treasury:ten-year`
- combines with `dec-pomdp`

## Theory

### Avellaneda-Stoikov

Market making with inventory risk, giving reservation prices and spreads. *attached.*

- touches: `perp:funding-rate`
- combines with `pomdp`
- requires `hjb`

### Dec-POMDP

Decision making among several agents, each with a partial view. *attached.*

- touches: `perp:funding-rate`
- combines with `mean-field-games`
- combines with `tla-plus`

### Decision theory

Choice under uncertainty with an explicit loss and constraints. *attached.*

- touches: `obligation:remaining-performance`

### Free energy principle

Perception and action as minimisation of a variational bound. *kept without an attachment.*

- kept without an attachment: it is a unifying story rather than a testable mechanism for this data
- specialises `variational-inference`

### Glosten-Milgrom

Quote setting as Bayesian updating about the counterparty. *attached.*

- touches: `8k:material-agreement`

### Hamilton-Jacobi-Bellman

Optimal control in continuous time, as a partial differential equation. *plausible, gated.*

- touches: `options:implied-move`
- combines with `optimal-stopping`

### Kyle model

Informed trading against a competitive market maker, with linear pricing. *attached.*

- touches: `perp:funding-rate`
- requires `information-theory`

### Leaky integrate and fire

Units that accumulate input and fire on crossing a threshold. *attached.*

- touches: `perp:funding-rate`
- combines with `hawkes`

### Market microstructure

Price formation from order flow, inventory and information. *attached.*

- touches: `perp:funding-rate`
- specialises `avellaneda-stoikov`
- specialises `glosten-milgrom`
- specialises `kyle-model`

### Mean field games

Many small agents whose interaction is through an aggregate state. *plausible, gated.*

- touches: `perp:funding-rate`
- combines with `dec-pomdp`

### Optimal stopping

When to exercise, including at discrete dates as in Bermudan options. *attached.*

- touches: `equity:scarcity`
- combines with `hjb`
- combines with `pomdp`
- supplies a method for `real-options`

### POMDP

Decision making with partial observability of state. *attached.*

- touches: `options:implied-move`
- combines with `avellaneda-stoikov`
- combines with `optimal-stopping`
- generalises `dec-pomdp`
- requires `decision-theory`

### Quantum optics

Open quantum systems, master equations and counting processes. *kept without an attachment.*

- kept without an attachment: the physics does not transfer; only the counting and jump formalism does, and that already exists in classical form
- supplies a method for `jump-diffusion`

### Real options

Capital projects as options whose exercise can be deferred. *attached.*

- touches: `power:planned-capacity-revision`

### Renormalisation group

Flow of effective descriptions as scale changes. *kept without an attachment.*

- kept without an attachment: scale structure here is simple enough to see directly
- combines with `tda`
- is inspired by `mixture-of-experts`

### Structural causal models

The data generating process written as mechanisms with interventions. *plausible, gated.*

- touches: `power:realized-delivery`
