# From nodes to an edge: the process, and the gates

This is the method, written before the next search rather than after it. It exists because the first
searches here were done in the wrong shape: they measured co-movement between series and called it a search
for an edge. A sorted, gated process is the difference between exploring and data mining.

The unit of work is not a pair of series. It is a **decision**: a rule that maps observable state to a
position, evaluated against the distribution the rule would have faced, net of costs, on data it could not
have seen.

## Stage 0: declare the decision, not the correlation

Before touching returns, write down four things:

1. **The signal**: which observable, computed from which representations, using only information available at
   the decision moment.
2. **The horizon**: how long the position is held. Fixed in advance. Never chosen from a chart.
3. **The decision rule**: what position follows from the signal, including the sign and the sizing rule.
4. **The null**: what the same decision would earn with no signal at all, **within the same state**. The null
   is the comparison that matters, and an unconditional average is not it.

**Gate**: if any of the four is missing, nothing downstream is interpretable.

## Stage 1: nodes must earn their place

For every node in the space, answer one question in one sentence: **what decision would change if I knew
this node?** A node that changes no decision is inventory, not input, and it stays out of the search. This is
how the space stays small enough to have power.

**Gate**: every node in a search carries a written decision, or it is excluded and counted as excluded.

## Stage 2: the transfer comes first

Write, in three sentences, who pays, why they cannot avoid it, and what observable reveals it. This orders
the search and is the only thing that justifies reading a survivor as more than noise.

**Gate**: no pair is measured before its transfer is written. Otherwise multiplicity has no discipline and
every survivor is a coincidence with a story attached.

## Stage 3: design for power before measuring

Three design choices decide whether a real effect is visible at all:

- **Cross-section over time series.** A signal that ranks many assets on a date supports a sorted test:
  sort into quantiles, hold, and measure the spread between extremes. That uses the whole panel and does not
  rest on twenty monthly observations of one pair.
- **Frequency.** Match the clock to the information. Daily bars on monthly signals waste nothing and turn
  22 observations into hundreds.
- **Panel structure.** Firm by date, with industry and size controls, rather than one firm's own history.

**Gate**: the design's minimum detectable effect is computed before the test, and if it is larger than the
effect the mechanism predicts, the design is changed or the search is abandoned.

## Stage 4: measure with a null that shares the state

The null for a signal is **the same signal, permuted within the state it is conditioned on**: within
industry and month, not across the whole sample. Otherwise the null absorbs nothing and every seasonal or
sector-wide move looks like signal.

Reported alongside every measurement: the false discovery rate across the declared grid, the family
correction where two results are views of one risk, and a specificity test, meaning the same measurement on
firms the mechanism does not implicate.

**Gates**: a survivor must beat its own state-conditioned null, survive rate control across the whole
declared grid, and appear where the mechanism says it should and not where it says it should not.

## Stage 5: identification, or say you cannot

An association is not a cause, and the study must say which it has. The cheap options, in order:

1. **Placebo signals** built the same way from the same data, which should show nothing.
2. **Matched controls**, firms that look alike but lack the exposure.
3. **Difference in differences** around the moment the information became public.
4. **Within firm** comparisons, where a firm is its own control.
5. **Exogenous variation**, the only route to causal language.

**Gate**: causal words require 1 through 4 plus a written argument for 5. Otherwise the finding is labelled
descriptive, and stays that way in the note.

## Stage 6: magnitude against costs and capacity

Convert the measured conditional difference into basis points per unit of risk, subtract spread, impact,
borrow and financing, and state the break-even cost. Then measure capacity from depth and average volume,
not from assumption.

**Gate**: if the effect does not exceed costs by a stated multiple, or capacity is below the size the
strategy needs to matter, the finding stays descriptive.

## Stage 7: the plateau and the stability checks

Show that nearby parameters also work, that the effect is not one sub-period, and that a revision to the
underlying data does not remove it. A single peak is a warning, not a result.

## Stage 8: the sealed test, once

One holdout, opened once, by a named person, reported as it is. Nothing about the study changes afterwards.

## Stage 9: only now, the strategy

Expression, sizing, hedges, portfolio construction and risk limits. The strategy is the last stage, because
it is the cheapest one once an edge exists, and the most misleading one when it does not.

---

# Where this process went wrong in this repo

Recorded so the next session does not repeat it.

1. **Co-movement was mistaken for edge.** The scan measured correlation between series pairs. Correlation of
   two time series is a census, not a decision. No edge can be read from it directly.
2. **No cross-sectional test was ever run.** The standard design for a signal, sorting a panel into
   quantiles, was never built. Every test here was a time series or event study on few observations.
3. **Signals were not de-noised before testing.** Thirty six percent of promise revisions turned out to be
   one month nudges. That was discovered after the firm level tests, not before, and it is the kind of thing
   stage 0 exists to prevent.
4. **Power was never computed in advance.** Twenty two monthly observations cannot detect an effect below
   0.54. A published statistic was compared against a design that could not have found it.
5. **The null was unconditional.** The placebo permuted dates across the sample, which left sector and
   seasonal moves inside the null. A state conditioned null would have been stricter.
6. **Nodes entered the search without a decision attached.** The space was built from what data existed
   rather than from what a decision could use.
7. **The strategy was built before an edge was found.** The capacity pair was a test of the machinery and was
   described as if it were a test of a hypothesis.
8. **Identification was attempted as one specificity check, late.** It should be a stage, not a patch.

---

# Applied here: the next test, in this order

Using only nodes that are populated today.

1. **Signal.** Firm level revision surprise in reported obligations, excluding revisions smaller than two
   months, measured against the firm's own typical change, stamped at the moment it became public.
2. **Design.** Panel of firms by month, daily returns aggregated to the holding window, sorted into
   quintiles within industry, spread measured between the top and bottom quintile. Never one firm alone.
3. **Null.** The same sort with the signal permuted within industry and month. Rate control across every
   grid point declared in advance, with the grid size printed before any result.
4. **Specificity.** Contractors and equipment makers against unrelated filers, because the mechanism says the
   first group bears schedule risk and the second does not.
5. **Then, and only then**, the mechanism conversation, costs and capacity.

If that design also finds nothing, the honest report is that the mechanism is real, measurable, and not
tradable through the instruments in this space, which is a stronger statement than any of the searches so far
could support.
