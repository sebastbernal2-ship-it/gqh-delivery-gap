# src/edgar

SEC filings as timestamped observations.

The filings audit of 2026-10-03 found fifteen annual-filing observations across PWR, ETN and DLR and
**not one resolved first-public timestamp**, so nothing was eligible for a timed test. This closes that
gap: it enumerates a firm's filings from the EDGAR submissions API, keeps the acceptance timestamp EDGAR
records, and states the earliest defensible availability as that time plus a declared processing lag.

Three rules it encodes, because they are easy to get wrong by hand:

1. **Availability is field-specific.** Acceptance is when EDGAR took the filing, not when anyone could
   act on it. A later number never becomes an earlier input.
2. **A real timestamp is not a day.** A filing date is not a time, and a date without a zone is refused.
3. **The sealed window is fenced.** The most recent fifth of history or two years, whichever is shorter,
   belongs to the sealed test. The builder counts those rows separately and will not summarise them
   without an explicit flag.

## Owner

`sebastbernal2-ship-it` claims `src/edgar/` in `OWNERS.md`.

## Use

```sh
python scripts/build_filings_register.py --tickers PWR,ETN,EME,DLR --out results/filings-register.csv
python scripts/build_filings_register.py --tickers PWR --summary
```

## What it cost to find out

**The SEC refuses an agent string that contains a URL.** On 2026-10-03, `User-Agent: <project>
github.com/<owner>/<repo>` earned an HTML 403 that looks exactly like throttling, and
`...@users.noreply.github.com` earned the same, while `<project> research@example.com` was accepted.
That is the likely reason direct retrieval failed in the earlier audit session. Set
`EDGAR_USER_AGENT="<project name> <your contact address>"`, with no URL in it.

A refused agent string now fails fast with that instruction instead of retrying, and ordinary refusals
retry with backoff, because that host also throttles in short bursts. Responses are cached under
`results/edgar-cache/`, which is gitignored.

## Limits it does not pretend to solve

- The acceptance timestamp is not proof that no press release or call came first. Every row carries
  `press_release_unchecked` until someone resolves that field.
- Filings enumerate disclosure; they do not label a delay. A backlog increase is not a missed deadline,
  which is why rows carry item numbers and document links rather than a delay flag.
