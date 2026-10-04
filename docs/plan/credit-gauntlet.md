# The credit gauntlet: pre-registration, written before any association number exists

Owner: sebastbernal2-ship-it. Status: declared, not yet measured. Nothing in this file may be revised after
the first statistic is printed, except by adding a dated correction that leaves the original text standing.

Why this file exists: the method bans measuring before declaring. The delivery chain taught that lesson once
already, when the strategy was built before an edge was found. Credit is the observable of the constraint
itself, so it deserves the same discipline as everything else.

## 1. The mechanism under test

A data center is financed per site or per deal, not at the parent's balance sheet. The debt for one campus
sits in its own issuer with its own covenants, completion tests, debt service thresholds and cash traps. The
yield on that debt is the market's own price of the constraint that the six gates ask us to name. If the
yield moves when the site's delivery prospects move, then credit is a cleaner read on the constrained
counterparty than any equity we hold.

Two distinct claims live inside that idea, and they are not the same claim:

- **C1, the aggregate claim.** Credit conditions in the data center complex move with the complex's equity.
  This is testable today with landable data and it is a weak claim. If it holds it is most likely beta, not
  an edge.
- **C2, the per-site claim.** The yield of one site's bond reprices when that site's delivery or counterparty
  news changes, and the repricing is not yet in the equity. This is the claim with value. It is **blocked at
  data access** (section 4) and cannot be tested from this environment today.

This document pre-registers C1 because it is the only one reachable. It records C2 as the target and its
blocker as a finding, not as a reason to test something else.

## 2. What was verified about the data, before declaring

All verified by running the route, on 2026-10-03.

| Route | Result |
|---|---|
| FRED CSV export `https://fred.stlouisfed.org/graph/fredgraph.csv?id=<ID>` | works with no key for every corporate credit series tried |
| `BAMLH0A0HYM2` US high yield OAS | 795 daily rows, 2023-10-03 to 2026-10-01 |
| `BAMLC0A0CM` investment grade OAS | 795 rows, same window |
| `BAMLC0A4CBBB` BBB OAS | 795 rows, same window |
| `BAMLH0A3HYC` CCC OAS | 795 rows, same window |
| `BAMLH0A0HYM2EY` high yield effective yield | 795 rows, same window |
| `DAAA`, `BAA10Y` Moody's corporate yields | 11,415 and 10,632 rows, full history |
| The same request with `cosd=1996-12-31` on an ICE series | ignored, still 795 rows |
| The same request with `cosd=1996-12-31` on `DGS10` | honoured, 7,764 rows from 1996 |
| Landed FRED rows in `public.gqh_source_records` | keys `DGS10`, `DGS2`, `FEDFUNDS`, `IPG3344S`, `NASDAQCOM`, `VIXCLS` only. Zero credit series |
| `api.finra.org/data/group/fixedIncomeMarket/name/corporateBondTrade` | 401, needs an OAuth token |
| Per-site price anywhere free | not found. TRACE needs registration, the deals are 144A, the tranches are ABS |

So the credit window is **fixed by the vendor's keyless limit**, not chosen from results. It starts 2023-10-03
and ends 2026-10-01, 795 daily observations. This is stated here because choosing a window from the data is
the specific sin the window file warns about, and the only defence is that the constraint came from the
source and is recorded before measurement.

## 3. The declared test, and its numbers, frozen now

**Frequency.** Daily. The monthly scan grid cannot see this series: both declared monthly studies close their
development windows before the credit series begins. Study one develops to 2022-09 and study two to 2024-03,
while keyless credit starts 2023-10. A monthly credit test would have six usable observations inside study
two and none inside study one. Daily frequency is not a preference here, it is the only frequency with data.

**Window.** History 2023-10-03 to 2026-10-01. Development 2023-10-03 to 2026-02-24. Holdout 2026-02-25 to
2026-10-01. The holdout is **not opened** by this work. Opening it is the captain's decision, as it is for
every holdout in this repo. The split is the house rule (most recent fifth) applied to a span the vendor set.

**Measures.** Credit enters as a **change**, never as a level, because both credit spreads and equity prices
trend and a level regression would recover that trend rather than a relation. Six credit measures, each as a
daily change: high yield OAS, investment grade OAS, BBB OAS, CCC OAS, the BBB minus CCC gap (the tier gap, the
weakest-link reading), and the high yield effective yield.

**Outcomes.** Four mechanism-implicated names, all landed and adjusted: DLR (data center REIT), EME, ETN, PWR
(electrical and mechanical buildout). Market-adjusted: each name's return minus SPY's return, so the market
factor is stripped before anything is compared.

**Horizons.** Forward returns at 1 trading day and 5 trading days. Fixed in advance, not chosen from a chart.

**The tests.** Market-adjusted forward return regressed on the credit change, per measure, per name, per
horizon. Frozen grid: **6 measures x 4 names x 2 horizons = 48 tests.** The grid size is printed by the
runner before any statistic, and it is not changed afterwards.

**The null.** Each pair is measured against **its own block-shuffled null**, credit changes permuted in blocks
of 20 trading days, 500 draws. The block preserves the autocorrelation and the regime clustering that a
day-by-day shuffle would destroy and thereby absorb. A survivor must beat its own placebo, not a textbook
p-value.

**Rate control.** False discovery across the whole declared grid of 48, reported alongside every survivor.

**Effective breadth.** The four names are one cluster, not four bets. All four are load-growth and data center
exposure and they move together. Effective breadth is reported next to the raw grid count, and it is close to
one.

**The ceiling.** **Descriptive only.** No identification design is declared here, so no causal word is
permitted in any report of these numbers. Per the association contract, the causal status ceiling for a
descriptive method is `descriptive_only`.

**Specificity.** SPY is the market control and enters only through the adjustment. The mechanism claims DLR
most directly and the buildout names indirectly, so a result that is equal across all four names reads as one
cluster effect and is reported as such. A true negative control, a listed name the mechanism does not
implicate, is **not landed** and is recorded in section 4 as a gap rather than quietly dropped.

**Falsifiers, stated before the run.**

1. If the market-adjusted relation is inside the placebo band for every one of the 48 tests, C1 is false at
   this frequency and this window.
2. If the relation is strong raw and vanishes after the SPY adjustment, it is market beta and not credit.
3. If the credit measure that carries the relation is the high yield index and not the BBB minus CCC gap, the
   weakest-link reading is not what the market is pricing.
4. If the four names disagree in sign, the cluster reading is wrong and the result is not a complex-wide
   relation.

## 4. What this design cannot reach, recorded as blockers

| Item | Blocker | The one line fix |
|---|---|---|
| Per-site yields (C2) | 144A deals, no free price surface, and FINRA reaches aggregates only | the FINRA route is an entitlement, not a signup: public credential free, Organization credential 1,650 dollars a month behind a signed Entitlement Agreement. EDGAR reaches deal level disclosure for free, see docs/plan/per-deal-credit-sources.md |
| Credit history before 2023-10 | the keyless CSV caps the ICE series at 795 rows | a FRED API key, which this repo already documents as working |
| Tranche level ABS prices | no free surface, institutional minimums | decide whether to buy, or read ratings actions instead |
| A true negative control name | not landed | widen the ticker set through `ingest.yml`, proved working |
| Issuer level coupons, covenants, maturities | reachable, not yet wired | EDGAR, which this repo already pulls |

Every row above is a finding about coverage. None of them is a reason to declare the test passed.

## 5. The six gates, pre-filled, blanks admitted

Filled before measurement so that the gates are not written to fit the result.

| Gate | Value | State |
|---|---|---|
| 1. Constrained counterparty | the project issuer that must service its debt after the completion test, and the lender that must hold it | nameable in one sentence, per site |
| 2. Price insensitive flow | insurance, pension and CLO mandates hold rated paper on mandate; refinancing is a calendar event | plausible, **not measured** |
| 3. Transfer and concentration | the spread paid over the risk free rate, concentrated per deal | a number is available once C2 data exists. **Blank** |
| 4. Instrument without dilution | per site: the tranche, which a small book may not be able to hold at stated minimums. Aggregate: parent bonds and credit ETFs, which reintroduce exactly the dilution this repo already rejected for compute relative value | **fails as stated.** This is the gate that decides the candidate |
| 5. Economics and capacity | unknown until 4 is answered | **blank** |
| 6. Barrier | the payer cannot reprice a completed deal and the loan documentation takes work to read | plausible, not measured |

Read the table as it is: gate 4 is where this candidate lives or dies, and it is the same gate that killed
compute relative value.

## 6. The run

Appended 2026-10-03 after `python scripts/run_credit_gauntlet.py --draws 500 --block 20`. Artifacts:
`results/credit-gauntlet.csv`, `results/credit-gauntlet.json`, `results/credit-panel.csv`,
`results/credit-panel.json`. Nothing above was edited to fit the result.

### 6.1 The mechanism statement

The declared mechanism was C1: credit conditions in the data center complex move with the complex's equity.
The measurements say what direction and how much, and nothing more. **Falsifier 1 is the one that decided.**
Across the declared grid the design found **no survivor after rate control**, so C1 is **not supported** at
daily frequency on the 2023-10 to 2026-02 window.

| Number | Value |
|---|---|
| Declared grid, printed before any statistic | 6 measures x 4 names x 2 horizons = **48** |
| Measured grid | 48 |
| Development window | 2023-10-03 to 2026-02-24, 627 trading days |
| Observations per test | 566 to 573 |
| Median absolute correlation across the grid | 0.0498 |
| Nominal hits at p at most 0.05 | **7** |
| Expected by chance at p at most 0.05 | 2.40 |
| Benjamini-Hochberg survivors across the 48 | **0** |

### 6.2 The identification statement

This is a descriptive measurement with a declared ceiling of `descriptive_only`. It can say a spread change
and a forward excess return moved together over this window. It cannot say credit caused anything, and no
causal word appears in this section.

Three honest readings of the seven nominal hits:

1. **They are one horizon and one bet.** All seven sit at the 5 day horizon, five of them on PWR and two on
   EME, and the four names are one cluster: average pairwise correlation 0.37, **effective breadth 0.47 bets
   from four names**. Seven nominal hits with an effective breadth below one is not seven findings.
2. **The sign is backwards for the mechanism.** Six of the seven are positive: wider spreads, higher forward
   excess return. The constraint story predicts the opposite, that the constrained party gets worse when its
   credit worsens. What the data shows is the stress rebound pattern, which is a mean reversion relation, not
   a credit impairment one.
3. **The tier gap is the exception and it is the wrong sign too.** The one negative hit is `credit:tier-gap`
   against PWR, at minus 0.082. So the weakest link reading did not carry the relation. **Falsifier 3 fires:**
   the measure that carried the nominal hits was the level family, not the tier gap.

### 6.3 The falsifiers, judged

| Falsifier | Verdict |
|---|---|
| 1. Every test inside the placebo band | **Not literally met, and it decided anyway.** Seven tests were nominal, zero survived rate control. The claim is unsupported either way |
| 2. Strong raw, vanishing after the SPY adjustment | **Did not fire, and it fired in reverse.** Market adjusted correlations were higher than raw ones: median raw minus adjusted is **minus 0.035**. The SPY adjustment strengthened the relation rather than absorbing it, which rules out plain market beta as the explanation and leaves the rebound reading above |
| 3. The level family carries it, not the tier gap | **Fired.** Five measures produced the nominal hits, the tier gap produced one with the opposite sign |
| 4. The four names disagree in sign | **Fired.** DLR produced no nominal hit at all, PWR produced five, EME two. The cluster reading is wrong and there is no complex wide relation here |

### 6.4 Costs and capacity

Not reached. Costs and capacity are assessed at the tradability gate, and gate 4 in section 5 already fails
before them. An aggregate credit measure is not holdable without dilution, and the per site instrument that
would not be diluted is blocked at data access. There is no performance number to report, because a grid with
zero rate controlled survivors has no strategy to size.

### 6.5 What this run actually bought

Three things, none of them a trade.

1. **A blocked claim with a named fix.** C2, the per site claim, is the claim with value, and it is blocked by
   one thing: no per site price series. The fix is one registration and one landing.
2. **A closed aggregate door.** C1 is dead at daily frequency on this window. The next person does not have to
   test it again, and the two remaining doors are C2 and the wider window.
3. **A measured power statement.** The smallest correlation reaching p at most 0.05 on this design is about
   0.08 at n around 568. The design could see a small relation and found nothing that survives, so this is a
   statement about the window and the aggregate level, not about a lack of power.

### 6.7 Dated correction, 2026-10-03: the FRED API key was tried, and the cap is a licence and not a key

The API route was tried with a valid 32 character
`FRED_API_KEY`, read in process from the algoterminal data loader and never printed. The official
`api.stlouisfed.org/fred/series/observations` route returns **786 observations, 2023-10-03 to 2026-10-01** for
every ICE BofA series, with `observation_start=1990-01-01`. The requested start is ignored. So the three year
window is **ICE licensing on FRED**, not a limit of the keyless CSV export, and no key lifts it. The fix
recorded in section 4 is corrected: a key does not widen the credit window, only a different source does.

The key does unlock the **Moody's family**, which FRED serves in full:

| Series | What it is | Observations | Window |
|---|---|---|---|
| `BAA10Y` | Moody's Baa corporate yield minus 10 year Treasury, the aggregate credit spread | 10,188 | 1986-01-02 to 2026-10-01 |
| `AAA10Y` | Moody's Aaa corporate yield minus 10 year Treasury | 10,935 | 1983-01-03 to 2026-10-01 |
| `DAAA`, `DBAA` | Aaa and Baa corporate yields, whose difference is the quality or tier gap | 10,983, 10,224 | 1983, 1986 to 2026-10-01 |

The equity panel is the binding constraint on the other side: the landed adjusted bars begin **2016-01-04**.
So the long window is 2016-01-04 to 2026-02-24 for development, holdout 2026-02-25 to 2026-10-01, unopened, and
it covers the whole 2015 to 2022 delivery mechanism window that the short credit window could not reach.

### 6.8 The long window grid, declared before it is run

Declared now, before any long window statistic exists.

- **Measures, three, chosen by history and not by result:** `BAA10Y`, the aggregate credit spread; `AAA10Y`,
  the highest grade spread; and `DBAA` minus `DAAA`, the quality and tier gap, which is the long history
  analogue of the BBB minus CCC reading.
- **Names and horizons, unchanged:** DLR, EME, ETN, PWR at 1 and 5 trading days, market adjusted against SPY.
- **Frozen grid: 3 measures x 4 names x 2 horizons = 24 tests.**
- **Null, rate control, ceiling, breadth: identical to section 3.** Block shuffle, block 20, 500 draws,
  Benjamini-Hochberg across the 24, `descriptive_only`, effective breadth reported next to the raw count.
- **Why the measure set differs:** ICE licensing removed the high yield and tier spread families from the long
  window. That is a coverage fact, declared before the run, not a choice made after seeing a number.
- **The same four falsifiers apply unchanged.**

### 6.9 The long window run, appended 2026-10-03

Command: `python scripts/run_credit_gauntlet.py --set long --draws 500 --block 20`. Artifacts:
`results/credit-gauntlet-long.csv`, `results/credit-gauntlet-long.json`.

| Number | Value |
|---|---|
| Declared grid, printed before any statistic | 3 measures x 4 names x 2 horizons = **24** |
| Development window | 2016-01-04 to 2026-02-24, 2,462 to 2,470 observations per test |
| Median absolute correlation | 0.0522 |
| Nominal hits at p at most 0.05 | **9** |
| Expected by chance | 1.20 |
| **Benjamini-Hochberg survivors** | **6** |
| Effective breadth | **0.62 bets** from 4 names, average pairwise correlation 0.20 |

The six survivors, all at rank 1 to 6 of 24:

| Measure | Name | Horizon | r | beta |
|---|---|---|---|---|
| `credit:aaa:10y` | PWR | 1 | -0.0922 | -0.0415 |
| `credit:quality-gap` | ETN | 1 | +0.1118 | +0.0581 |
| `credit:quality-gap` | PWR | 1 | +0.0883 | +0.0583 |
| `credit:aaa:10y` | ETN | 1 | -0.0802 | -0.0284 |
| `credit:quality-gap` | DLR | 1 | +0.0594 | +0.0368 |
| `credit:quality-gap` | DLR | 5 | +0.0481 | +0.0666 |

**Falsifier 3 now answers differently on the long window than on the short one.** The tier gap analogue,
Baa minus Aaa, carries four of the six survivors. That is the weakest link reading, and it did survive rate
control at this window. It is the one thing the short window could not see.

**Falsifier 4 fires again.** EME flips sign on the quality gap (minus 0.048), so the four names do not agree.

### 6.10 The stability and cost gates, declared after the grid on purpose

Six survivors on a 24 test grid is exactly the shape a single regime or ten extreme days can make. These four
checks were therefore declared **after** the long grid ran, and they carry the label: **they can only weaken a
result, never upgrade one.** Command: `python scripts/check_credit_stability.py`. Artifacts:
`results/credit-stability.csv`, `results/credit-stability.json`.

| Check | Result |
|---|---|
| Sign stable across development halves | **5 of 6** |
| Survives dropping the ten largest credit change days | **3 of 6** |
| Clears a 10 bps round trip cost, single leg | **3 of 6** |
| Largest implied gross edge | **16.7 bps**, and that figure is over five days for the 5 day row |
| Sign agreement within each measure | holds for both measures |

Three findings from the gates, and they decide the candidate.

1. **Half of it lives in ten days.** ETN on the quality gap falls from plus 0.112 to plus 0.022 once the ten
   largest spread moves are removed. DLR at the 5 day horizon flips sign in the second half.
2. **The two measures that carry it are mechanically related and load with opposite signs on the same names.**
   `BAA10Y = quality-gap + AAA10Y` by construction. One component predicts higher returns and the other
   predicts lower, on the same names, over the same days. The combined `BAA10Y` effect is therefore small and
   it did not survive (rank 8, p 0.042). What the grid found is a decomposition of one credit complex into
   three views, not three independent facts.
3. **The cost gate is marginal at one leg and fails at two.** The signal is a market adjusted excess return,
   so expressing it means a long leg and a short leg. The declared 10 bps round trip covers one leg. At 20 bps
   for the pair, **none of the six clear**, and the largest gross figure was over five days rather than one.

**Verdict on the long window: no edge, and now for a stated reason.** The relation is real enough to beat a
block shuffled null on 24 declared tests, it is not a pure market beta story, and it dies where the method
says a candidate must: it sits on one cluster of 0.62 effective bets, it depends on a handful of days, and it
does not clear costs once the expression is two legged. This is a descriptive candidate that failed gates 5
and 7, not a discovery.

**The firewall.** This study's development window overlaps the mechanism study's holdout. Nothing measured
here may change the design of the mechanism and strategy study, and nothing did: the credit work touched no
delivery event, no revision definition and no window of that study.

### 6.6 The next test, in order, and what each needs

1. **C2, per site credit.** Needs the FINRA API registration, a deal name set, and TRACE prints. This is the
   only route to the instrument gate.
2. **C1 on a wider window.** Needs a FRED API key to lift the 795 row cap. This is a rerun of the same
   declared test, not a new study, and the declaration stays frozen.
3. **The indenture layer.** Needs EDGAR wiring, no entitlement. It reads the covenant, the completion test and
   the debt service threshold, which is the constraint the six gates ask for in writing. This is the cheapest
   and most mechanism relevant next step after the credit series themselves.
