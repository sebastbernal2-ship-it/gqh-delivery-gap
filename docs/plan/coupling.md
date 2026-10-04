# Declared: the coupling layer

Status: development only. Owner: sebas. Date: 2026-10-04. Implementation:
`hpc/probabilistic-council/coupling.py`. Contracts: `tests/test_coupling.py`.

## Question

Given one calibrated marginal per dimension, a reference coupling, and an optional martingale
constraint along a price dimension, does a joint law exist that matches every marginal and the
constraint, and how much dependence does the constraint force?

## Construction

1. Start from a reference coupling, by default the product of the marginals.
2. Match every marginal exactly by iterative proportional fitting, the I-projection for the KL
   objective.
3. When a martingale constraint is declared, tilt each conditional slice so the conditional mean
   equals the price of the conditioning bin, solved per slice by bisection on a standardised value
   scale, then alternate with step 2 until both residuals are below the declared tolerances:
   marginal 1e-9 in probability units, martingale 1e-6 in price units.

## The honest facts this layer must state

1. With only marginal constraints and a product reference, the KL-minimal coupling is the product
   itself, so the layer would be a no-op. Dependence enters only through a reference that carries
   it, through an extra constraint, or through data. A test pins this.
2. A martingale constraint and fixed marginals can be mutually inconsistent. The tower property
   requires adjacent price marginals to share a mean; when they do not, the layer reports the mean
   gap as a proof of infeasibility instead of returning a wrong law. A test pins that too.
3. Residuals are always returned. A converged flag is a measurement.

## Entanglement

The dependence the constraint forces is measured as the KL divergence and the total-variation
distance between the fitted joint and the product of its marginals. With a martingale constraint and
a two-point price grid, the limit is the comonotone coupling with KL equal to the log of two, which
the contracts verify.

## First real target

The execution-risk cache: twelve marginal heads over (3, 2, 2, 3) with the 5, 15 and 60 second
horizons, where the martingale constraint ties the horizons together. That cache needs five whole
UTC dates, assigned by `scripts/build_live_risk_plan.py`. The equity analogue, a joint law across
horizons for a post-filing return target, is the second target and needs a declared return target
that the current disclosure-surprise panels do not yet provide.

## Ceiling

No world claim is made today. This is the machinery plus its contracts, with a synthetic
demonstration of exactness, feasibility and entanglement. The paper that inspired the transfer,
Stochastic Knothe-Rosenblatt calibration, is classical; no quantum component is involved.
