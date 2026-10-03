# Review request: the note, before submission

Owner of the writing surface: Vishnu. Requested by: sebastbernal2-ship-it. Status: open.

## What to review

`docs/note.html`, which prints to `docs/note.pdf` at five pages, the limit for the track.

## The four questions worth a reviewer's time

1. **Does every claim have an artifact behind it?** Each number in the note should be reproducibly traceable
   to a command in `README.md` and a file under `results/`. If a sentence cannot be traced, it should go.
2. **Is the language plain, per `docs/writing/style.md`?** No em dashes, active voice, short sentences, one
   meaning per term.
3. **Does the honest framing read as honest rather than as apology?** The note reports four calibrated nulls
   and a measured mechanism. A reviewer should say whether that reads as a contribution or as a defence.
4. **Is anything overstated?** Three specific places to check: the claim that revisions are large and slow,
   the claim that the crowded expression is efficient, and the claim that the compute price clears its null
   against everything tested.

## What is deliberately absent, and should not be added back

- No working edge is claimed, because none survived calibration.
- No intraday or option result, because no entitlement was held.
- No causal language about revisions and prices, because no identification design was run.

## How to respond

Reply in this repo, either by editing `docs/note.html` directly under your own ownership, or by leaving a
review file beside this one. The PDF is regenerated with:

```sh
chrome-headless-shell --headless --print-to-pdf=docs/note.pdf file://$PWD/docs/note.html
```

or, if that binary is unavailable, print the HTML from any browser at letter size with default margins.
