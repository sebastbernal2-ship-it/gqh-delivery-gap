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

## Results

Filled in below, then committed with the raw output alongside.

### 1. Study one, the aggregate capacity strategy, 24 month holdout

`python scripts/run_capacity_strategy.py --open-sealed`, raw output in `results/sealed-strategy.txt`.

| signal | n | gross | net 10bp | net 20bp | annualised | Sharpe | max drawdown | hit rate |
|---|---|---|---|---|---|---|---|---|
| next_year | 98 | +0.38% | +0.16% | -0.05% | +2.0% | 0.10 | -37.8% | 51% |
| current_and_next | 98 | -0.06% | -0.29% | -0.52% | -3.4% | -0.17 | -48.2% | 45% |
| three_year | 98 | +0.12% | -0.10% | -0.33% | -1.2% | -0.06 | -42.9% | 47% |

The pre-declared threshold plateau, on the balanced signal: trading only the largest third of revisions gives
gross +1.11%, net +0.85% at ten basis points and +0.58% at twenty, with a Sharpe of 0.43 over 33 months.

**Verdict: null, as declared.** The best full-history signal earns +0.16% a month net at the low cost assumption
and loses money at the high one, with a Sharpe of 0.10 and a 38% drawdown. The one cell that looks alive is a
subset of 33 months chosen by revision magnitude, it was visible in development before the holdout was opened,
and a subset cell cannot be promoted on 33 observations. It would need a fresh holdout, which this study cannot
provide. It is recorded as a hypothesis with no evidence behind it, nothing more.

### 2. Study one, the association scan, same holdout

Raw output `results/scan-mechanism-sealed.txt`, against the development only run in `results/scan-mechanism-dev.txt`.

| run | pairs | nominal survivors | expected by chance | within one family | across families |
|---|---|---|---|---|---|
| development only | 51 | 8 | 2.6 | 4 (expected 0.5) | **0 (expected 0.9)** |
| holdout opened | 62 | 12 | 3.1 | 6 (expected 0.8) | **2 (expected 1.1)** |

**Verdict: null on the line that matters.** The headline count rises with the opened months, but the
cross-family count is 2 against 1.1 expected, and every survivor in the list is a commodity or basket pair whose
legs share constituents: buildout against scarcity, copper against uranium, gas against the promise level. Those
are two views of one risk, which the scan's own family split already separates out.

### 3. Study two, the compute era, six month holdout

Raw output `results/scan-compute-sealed.txt`, against `results/scan-compute-dev.txt`.

| run | pairs | nominal survivors | expected by chance | within one family | across families |
|---|---|---|---|---|---|
| development only | 62 | 6 | 3.1 | 1 (expected 0.8) | **3 (expected 1.1)** |
| holdout opened | 62 | 7 | 3.1 | 3 (expected 0.8) | **2 (expected 1.1)** |

**Verdict: null.** The compute era development run's three cross-family survivors do not survive the holdout as
a group: two remain, against 1.1 expected, and the within-family count rises instead.

## What the sealed test establishes

Three declared tests, opened once, with the designs frozen and the expectation stated before they ran. All three
are null. The strategy does not clear costs in its own holdout, and neither study produces cross-family
association beyond what the null produces.

The honest consequence is also the useful one: the mechanism and its measurement stand, the tradable link does
not exist in this data, and the one cell that looks alive is a subset that would need a holdout this project
cannot grant it. Both holdouts are now spent and are closed permanently. Nothing here can be re-run for a second
look, and nothing was tuned after the fact.

## Record

| field | value |
|---|---|
| owner of the decision | the captain |
| authorization | 2026-10-03 |
| tests run | three, as declared above |
| holdouts spent | study one 2022-10 to 2024-09, study two 2024-04 to 2024-09 |
| result | null in all three |
| further openings | none permitted |
