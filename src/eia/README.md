# src/eia

Promised against realized generator delivery, from the monthly inventory vintages.

Each monthly EIA-860M file is a vintage: what the inventory said at that date. Two vintages together give
the two objects this study needs.

- **A revision**: the promised operation month for one generator moved between two vintages.
- **A realization**: the generator appears in a later vintage's operating sheet, carrying the month it
  actually ran, which compares against the last promise published for it.

`src/eia/xlsx.py` is a small spreadsheet reader. The environment has no `openpyxl` and installation is
locked down, and these files are ordinary zipped XML, so reading them directly is cheaper than a
dependency. It handles shared strings and inline strings, and nothing else.

## Owner

`sebastbernal2-ship-it` claims `src/eia/` in `OWNERS.md`.

## Use

```sh
python scripts/build_delivery_panel.py --years 2015-2023
```

## Availability rule, stated once

A file named `<month>_generator<year>.xlsx` is treated as public at the **end** of that month. The exact
publication day is not claimed, so nobody can say this study used a number before it existed. A vintage
whose availability falls on or after the sealed boundary is excluded and counted, never summarised.

## Two rules it will not break

1. **A moved promise is not an economic event.** It is a change in a published schedule. Whether it moves
   cash is a separate question with its own test.
2. **Months stay months.** A promised month is stored as year and month, never as a fabricated day.
