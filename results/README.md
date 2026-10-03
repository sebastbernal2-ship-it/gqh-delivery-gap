# Results contract

Every number the note quotes comes from a file in this folder. One writer per file.

The assembler will refuse to quote a number that is not here, and `make check` validates the shape.

## Files

| File | Writer | Engine |
|---|---|---|
| `e1.json` | W1 | Event vol on rule-dated disclosure |
| `e2.json` | W2 | Coupling residual |
| `e3.json` | W3 | Carry, liquidation provision, execution |
| `e4.json` | W4 | Quantum and compute scaling |
| `costs.json` | W3 | The cost model every engine charges |

## Envelope, frozen

Every file is a JSON object with these keys.

```json
{
  "engine": "e1",
  "generated_at": "2026-10-03T04:12:00Z",
  "git_commit": "<40 char sha of the code that produced this>",
  "universe": "description of what was traded",
  "in_sample": { "start": "YYYY-MM-DD", "end": "YYYY-MM-DD" },
  "out_of_sample": { "start": "YYYY-MM-DD", "end": "YYYY-MM-DD" },
  "costs_bps": 5,
  "variants_tried": 12,
  "metrics": {
    "is":  { "sharpe": 0.0, "max_drawdown": 0.0, "turnover": 0.0, "n_obs": 0 },
    "oos": { "sharpe": 0.0, "max_drawdown": 0.0, "turnover": 0.0, "n_obs": 0 }
  },
  "controls": {},
  "falsifiers_triggered": [],
  "notes": "one paragraph a judge could read"
}
```

## Rules

1. `git_commit` is the commit that produced the file. The note quotes builds, not edits.
2. `variants_tried` is honest. The Deflated Sharpe Ratio uses it.
3. `falsifiers_triggered` is never empty by accident. If a declared falsifier fired, it is listed and
   the note says so.
4. Never overwrite a result file by hand. Regenerate it from code.
