# Mathematics and methods we might use, honestly sorted

A registry, not a reading list. Every entry says what it is, **what it attaches to in this study**, whether
that attachment is real, and what test or representation it would produce. The point of the sorting is that
a method with no attachment is decoration, and decoration costs days.

Status meanings:

- **attached**: it attaches to a measured object here, and the attachment names a concrete test, series or
  invariant
- **plausible**: the attachment is real but gated on something we do not hold yet, such as an entitlement
- **decorative**: no honest attachment to this problem. Kept so nobody re-litigates it.

| Idea | What it is | Attaches to | Status | What it would produce |
|---|---|---|---|---|
| Spectral theory, harmonic analysis | Decomposition into periodic components | The modal twelve month slip is a period. Slip revisions should be tested for 12 and 24 month harmonics | attached | A harmonic regression on slip revisions, and a periodogram of the revision series |
| Joint energy and variance models | Joint dynamics of a price and its variance | The compute price node and the fuel nodes: our scan read levels and changes but never level and variance jointly | attached | A two dimensional representation of the compute node, scarcity measured as a level plus a variance state |
| Stochastic Knothe-Rosenblatt, light speed calibration of stochastic local volatility | Monotone transport that maps one distribution onto another, used to calibrate fast | Two places: dealer hedging flow needs a vol surface that updates fast, and the transport distance between our forecast distribution and the market implied one is itself a mispricing measure | plausible | A distributional mispricing signal, measured as a transport distance. Gated on options data |
| Optimal stopping, Bermudan and Asian option machinery | Values the right to exercise at chosen dates | A delayed project is a real option exercised later: milestones are the exercise dates and the deferral is the option. Also our own exit rule under inventory risk | attached | The deferral value framing of a slipped promise, and an optimal stopping rule for exits |
| Arnold networks, KANs | Networks whose edges are learnable univariate functions | Our regime is small n and low dimension, where an interpretable shape beats a black box. Fits the plateau requirement | attached | Conditional response curves with visible shape, fitted on 22 to 86 observations |
| Finite Expression Method, symbolic regression | Discovers an explicit equation instead of a fitted function | The core question is which relations exist, and an equation can be judged and falsified where a model cannot | attached | Sparse closed form relations across the node space, with a null calibration |
| Neural correction operator (from the EIT paper) | A learned correction on top of a structural solver | Our MW to cash flow mapping is a structural operator; the learned part is the correction | attached | A structural model with a learned residual, rather than a learned model wearing a story |
| TLA+ | Formal specification with machine checked invariants | The execution and risk protocol: invariants like never exceed the exposure bound, never trade in the holdout, never reuse a signal | attached | A specification whose invariants are checked, for the engine rather than for the alpha |
| Persistence theory, topological data analysis | Summarises shape across scales | Promise survival: how long a published promise lives before being revised is a duration problem. And order book structure for the cascade direction | attached, and plausible for the book | Hazard rates for promises, replacing a mean with a survival curve |
| Decision theory | Optimal choice under uncertainty | Already the frame: loss function, sealed test, expected value under constraints | attached | Nothing new to build, but it is the frame the rest sits in |
| POMDP, Dec-POMDP | Decision making with partial observability, alone and among agents | Execution under inventory risk is a POMDP. Cascades and dealer hedging are Dec-POMDPs: dealers, liquidators and arbitrageurs each act on partial views | attached | Policy formulations for the execution layer, and a game structure for cascade participants |
| MCMC and Bayesian model comparison | Posterior over models rather than a threshold on one | Our multiplicity problem: replace "beat your own null at 95 percent" with posterior inclusion probabilities over the whole node space | attached | A principled multiplicity statement in place of a threshold count |
| Contrastive learning | Learns a representation from similar and dissimilar pairs | State representation for the decision model: which market states are the same regime | plausible | An embedding of book and flow states for Jevlike to consume |
| VLMs and vision models | Reading images and documents | Two attachments: filings, permits and exhibits as documents, and physical construction progress from satellite imagery | attached | Entity linking beyond the 6.2 percent ceiling, and an independent physical measure of delay |
| Control theory, linear and nonlinear dynamical systems | Feedback systems, delays, stability | The delivery pipeline is a plant with a transport delay, which is our measured 33 to 94 days. Promise is input, delivery is output, price is the observer | attached | System identification of the delivery chain, with the delay estimated rather than assumed |
| Leaky integrate and fire, spiking models | Threshold units that accumulate and fire | A liquidation cascade is a threshold phenomenon: accounts accumulate loss until maintenance margin is crossed and they fire together | attached, gated on tape | A generative model of cascades with clustering and refractory period, testable against observed avalanche sizes |
| Quantum optics | Open quantum systems, master equations, photon counting | Only the formalism transfers: master equations and counting processes are the same mathematics as jump and point process models | decorative as physics, attached as formalism | Nothing beyond what Hawkes style point process models already give |
| Affine Kac-Moody algebras | Infinite dimensional symmetry algebras | Nothing in this problem is a representation of one | decorative | Nothing |
| Langlands program | Deep connections between number theory and representation theory | Nothing here is a modular form | decorative | Nothing |
| Swaptions, Bermudan and Asian options | Interest rate and path dependent derivatives | The rate node enters project economics, and the option to refinance is real for utilities. Otherwise the transferable part is the stopping machinery above | plausible | Rate path modelling for project IRRs if an instrument ever expresses it |
| Electrical impedance tomography | Inverse problem from boundary measurements | Transfers only as a pattern: invert a badly posed problem with a learned correction, which is the neural correction operator row | decorative | Nothing |
| Dynamics on complex networks, FEM | Equation discovery for network dynamics | The node space is a graph, and its dynamics are the object | attached | Equations of motion for a small subset of nodes, with the graph as the coupling structure |
