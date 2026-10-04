# Declared study: maker entry at the dislocation extreme

**Status: development only, declared before the run.** Both sealed windows are spent. T20 found the cost
hurdle to be the binding constraint in the cascade family, and this study tests the declared fix: resting
at the extreme instead of taking the reversion.

## The question

Does a resting entry at the dislocation extreme improve net reversion relative to the taker entry that
T20 measured, and does it fill often enough to matter?

## Data and levels

Same recorded tape, same condition ladder (L1 the frozen conjunction, L2 top one percent moves, L3 top
five percent, L6 thin book), same direction rule (reversion against the move), same horizons in bars of
one, five and fifteen minutes.

## Entry model, declared

- For a reversion long after a down move: rest a limit buy at the best bid observed at the condition bar.
- For a reversion short after an up move: rest a limit sell at the best ask observed at the condition bar.
- Fill rule: filled when, within the next four bars, some sample crosses the limit (best ask at or below
  the buy limit, best bid at or above the sell limit). Entry price is the limit.
- No fill inside the window means the event is dropped, and the fill rate is reported per level.
- Exit is a taker exit at the mid of the horizon bar. Cost is the maker fee at entry and the taker fee
  plus half the measured spread at exit. Maker fee declared at 1.5 basis points, taker at 4.5. Any maker
  rebate is upside and is not assumed.

## Comparison and null

Paired against the T20 taker entry on the same events, plus the random-time null for the maker variant.
Reported per level and horizon: fill rate, mean and median net basis points, the paired difference against
taker, and the null p.

## Falsifier

Maker entry does not improve net reversion, or the fill rate is too low for the level's gross to matter.

## Ceiling

Entries and fills are read from fifteen second best bid and ask snapshots. Queue position, partial fills
and adverse selection are not modelled, so every maker result here is an upper bound.

## Reproduce

    python3 scripts/build_maker_entry_study.py

## Pass two, declared after pass one and before its run

Two follow ups from the pass one result.

1. **Filled against unfilled.** For every level and horizon, split the events by whether the resting
   order filled, and report the taker convention forward result for each side. The declared question is
   whether the unfilled events carry the reversion, which would say entry is taken immediately and the
   resting order is a size tool.
2. **Penetration ladder.** Queue position is not observable in this tape, so fill is made stricter in
   declared steps: the opposite side must cross the limit by zero, half the spread at that sample, or one
   full spread. Fill rate and net are reported at each step, which turns the unknown queue position into
   a visible sensitivity rather than an assumption.

Both passes are reported either way.

## Result, pass one, 2026-10-04

Fill rates from the recorded book: 33 percent at the frozen conjunction (2 of 6 events), 47 percent at
the top one percent level, 42 percent at the top five percent and at the thin book level.

The paired result is positive everywhere, between +4.6 and +17.3 basis points against the taker entry on
the same events, which is roughly the saved fee and spread plus a better entry price.

The absolute result is not. Every cell is at or below zero except two: +0.83 basis points at the top one
percent level and +2.64 at the thin book level, both at fifteen minutes, and both inside their nulls
(p 0.2).

The frozen conjunction shows why the fix is not free. Its taker entry nets +6.9 basis points at fifteen
minutes from six events, and its maker variant nets -8.5, because the two events that filled are the two
that kept moving. Waiting for a better price selects the adverse events and misses the reversion.

The fact this leaves: the cost fix works in paired terms and fails in absolute terms. The binding
constraint shifts from the cost hurdle to fill selection. The next object is a fill model with queue
position, and a declared test of whether the unfilled events are the reversion, which would say that the
reversion is taken immediately and maker entry is a size tool rather than a source of edge.

## Result, pass two, 2026-10-04

**Filled against unfilled.** At the frozen conjunction and fifteen minutes, the two filled events net
-13.2 basis points under the taker convention and the four unfilled events net +17.0. The reversion lives
in the events that never came back to a resting price. At the percentile levels the split is milder and
both sides are negative: filled -7.0 against unfilled -9.0 at the top one percent level, -8.9 against
-7.1 at the top five percent, and -14.3 against -4.7 at the thin book level. Filled events are worse than
unfilled at every level and horizon, which is adverse selection in the plainest form.

**Penetration ladder.** Making the fill stricter, as a proxy for queue position, removes the good fills
and keeps the bad ones. At the top one percent level the fill count falls from 48 to 36 to 29 as the
required penetration rises from zero to half a spread to a full spread, and the net falls from +0.83 to
-1.84 to -3.02 basis points. The thin book level repeats it: 17 fills and +2.64 basis points at zero
penetration, 12 fills and -0.56 at half a spread.

The fact this leaves: the positive maker cells are an artifact of optimistic fills. Under any queue aware
fill rule the maker entry nets negative, and the reversion that does exist is captured by taking the
event immediately. Maker entry is a size tool, not a source of edge, on this window.
