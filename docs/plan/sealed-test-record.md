# Sealed test record

## Authorization, written before anything was run

The captain authorized opening and redoing the sealed tests on 2026-10-03. Owner of the decision: the captain.
Executed by this session. Both holdouts are opened **once**, in the declared way, with the designs frozen in
`docs/variants.md` and the protocol files. Nothing may be re-opened for a second look, and an unwelcome result is
still the result.

Three declared tests are run, and all three are reported:

1. Study one, the aggregate capacity strategy, holdout 2022-10 to 2024-09, in sample 1,070 monthly vintages.
   Command: `python scripts/run_capacity_strategy.py --open-sealed`.
2. Study one, the association scan, holdout 2022-10 to 2024-09.
   Command: `python scripts/run_association_scan.py --window mechanism-and-strategy --open-sealed`.
3. Study two, the compute era, holdout 2024-04 to 2024-09.
   Command: `python scripts/run_association_scan.py --window compute-era --open-sealed`.

## What was already true before opening, stated in advance

Both development passes were null. The aggregate strategy produced a gross 0.29 percent a month and a net minus
0.15 percent at doubled costs, with a Sharpe of 0.04, and the signal was one signed in 89 percent of months. The
association scan produced six survivors against 5.5 expected, and its control over produced. So the honest
expectation is that an opened holdout on a null candidate stays null, or becomes a candidate that would need a
fresh holdout, which it cannot have.

## The missing switch, added as the protocol promised

The scan's window module already supported opening its holdout, and the scan never exposed the switch. The
protocol file said the flag would be added when the test ran. It is added now, and it changes no threshold, no
horizon, no pair and no statistic: it only lets the declared months into the measurement.

## Results, reported in the order the method requires

### 1. Study one, the aggregate capacity strategy

**Mechanism statement.** The candidate says that a published promise for new capacity is revised, that the
revision changes when revenue arrives for the firm that made the promise, and that the firm's price should move
when the revision becomes public. Its counterparty claim is that the firm's own investors underreact to a
revision published in a monthly inventory.

**Identification statement.** What the holdout can support: the revision series is a valid point in time panel
built from monthly vintages, its label is the promise moving, and both were fixed before this test. What it
cannot support: any claim about who was forced to trade. No constrained counterparty is measured in this design.
The transfer is assumed, not observed, so the test can only falsify a return claim, never confirm a mechanism.

**Falsifier, baseline and costs, stated before the returns.** The falsifier is no net return after costs in an
unopened window. The baseline is the same signal in development, which was null. Costs are charged on both legs
at ten and at twenty basis points per leg, with turnover measured from position flips.

**The numbers, as the tradability gate.** Returns table, last on purpose:

| signal | n | gross | net 10bp | net 20bp | annualised | max drawdown | hit rate |
|---|---|---|---|---|---|---|---|
| next_year | 98 | +0.38% | +0.16% | -0.05% | +2.0% | -37.8% | 51% |
| current_and_next | 98 | -0.06% | -0.29% | -0.52% | -3.4% | -48.2% | 45% |
| three_year | 98 | +0.12% | -0.10% | -0.33% | -1.2% | -42.9% | 47% |

**Verdict at the tradability gate: failed.** The best signal clears single digit costs by sixteen basis points a
month and fails at double that cost, with a thirty eight percent drawdown. The one subset that clears both cost
assumptions, the largest third of revisions, is thirty three months chosen by magnitude and was already visible
in development, so it needs a fresh holdout this study cannot give it. It stays a hypothesis with no evidence.

### 2. Study one, the association scan

**Mechanism statement.** The scan claims nothing about a counterparty. It measures whether two series move
together more than a generated null, which is a relation and not an edge, and it is reported only because the
protocol declared it.

**Identification statement.** A survivor is a candidate for a mechanism conversation. The line that matters is
the cross family count, because two legs inside one family share constituents and are one risk viewed twice.

**Falsifier, baseline and costs.** Falsifier: no cross family survivor beyond the expected count. Baseline: the
same scan in development only.

| run | pairs | nominal survivors | expected by chance | within one family | across families |
|---|---|---|---|---|---|
| development only | 51 | 8 | 2.6 | 4 (expected 0.5) | 0 (expected 0.9) |
| holdout opened | 62 | 12 | 3.1 | 6 (expected 0.8) | 2 (expected 1.1) |

**Verdict: no cross family association beyond the null.** The headline count rises with the opened months and
every survivor is a commodity or basket pair whose legs share constituents.

### 3. Study two, the compute era

**Mechanism statement.** Same as above, a relation rather than an edge, measured separately because the compute
archive defines its own history.

**Falsifier, baseline and costs.** Falsifier: no cross family survivor beyond the expected count. Baseline: the
same scan in that study's development window.

| run | pairs | nominal survivors | expected by chance | within one family | across families |
|---|---|---|---|---|---|
| development only | 62 | 6 | 3.1 | 1 (expected 0.8) | 3 (expected 1.1) |
| holdout opened | 62 | 7 | 3.1 | 3 (expected 0.8) | 2 (expected 1.1) |

**Verdict: no cross family association beyond the null.** The three development survivors do not hold up.

## What the sealed test establishes, in mechanism terms

Both holdouts are now spent. Three declared tests are null. The mechanism and its measurement stand. The tradable
link does not exist in this data, and the missing piece is the counterparty: no design tested here measured a
forced payer, so nothing here could have found the edge even if one exists.

## Record

| field | value |
|---|---|
| owner of the decision | the captain |
| authorization | 2026-10-03 |
| tests run | three, as declared above |
| holdouts spent | study one 2022-10 to 2024-09, study two 2024-04 to 2024-09 |
| result | null in all three, reported with the mechanism first and the returns last |
| further openings | none permitted |
