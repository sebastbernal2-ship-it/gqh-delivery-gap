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
