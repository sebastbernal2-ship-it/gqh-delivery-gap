"""SEC EDGAR filings as timestamped observations.

The audit of 2026-10-03 found fifteen annual-filing observations across PWR, ETN and DLR and not one
resolved first-public timestamp, so nothing was eligible for a timed test. This module fixes that one
gap: enumerate a firm's filings, keep the acceptance timestamp EDGAR records, and state the earliest
defensible public availability as that time plus a declared processing lag.

Three rules it encodes, because they are easy to get wrong by hand:

1. Availability is field-specific. Acceptance is when EDGAR took the filing, not when anyone could act
   on it. A later number never becomes an earlier input.
2. A real timestamp is not a day. A filing date is not a time, and a date without a zone is refused.
3. The sealed window is fenced. The most recent fifth of history or two years, whichever is shorter,
   belongs to the sealed test. The builder counts those rows separately and will not summarise them
   without an explicit flag.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

# Measured on 2026-10-03: that host refuses an agent string containing a URL or an unreachable domain,
# answering with an HTML 403 that looks exactly like throttling. A plain "<project> <contact address>"
# is accepted. Set EDGAR_USER_AGENT to a real address of your own; the default is a placeholder.
DEFAULT_USER_AGENT = "gqh-delivery-gap research research@example.com"
AGENT_HELP = ("the SEC refused this agent string. It refuses a URL or an unreachable domain, so set "
              "EDGAR_USER_AGENT to \"<project name> <your contact address>\"")
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
OLD_SUBMISSIONS_URL = "https://data.sec.gov/submissions/{name}"
DOCUMENT_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}"

ET = ZoneInfo("America/New_York")

# 8-K items that can carry a project or schedule disclosure. They are search routes, not categories
# that guarantee a delay: the Form 8-K instructions do not make every project delay reportable.
CANDIDATE_8K_ITEMS = {"1.01", "1.02", "2.02", "7.01", "8.01"}
CANDIDATE_FORMS = ("8-K", "10-K", "10-Q")


def user_agent() -> str:
    return os.environ.get("EDGAR_USER_AGENT") or DEFAULT_USER_AGENT


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": user_agent(), "Accept-Encoding": "gzip, deflate"})
    return s


# The SEC serves this host from a shared address and throttles in short bursts. A refusal with 403
# here means "slow down", not "forbidden", so the client backs off and retries instead of giving up.
RETRY_STATUS = {403, 429, 500, 502, 503, 504}
DEFAULT_CACHE = Path(__file__).resolve().parents[2] / "results" / "edgar-cache"


def _agent_refused(response) -> bool:
    """A 403 with an HTML body is a refused agent string, not a throttle: retrying cannot help."""
    if response.status_code != 403:
        return False
    kind = (response.headers.get("Content-Type") or "").lower()
    return "html" in kind or "<html" in (response.text or "")[:200].lower()


def _cache_path(cache_dir: Path, url: str) -> Path:
    return cache_dir / (hashlib.sha256(url.encode()).hexdigest()[:24] + ".json")


def get_json(s: requests.Session, url: str, tries: int = 5,
             sleeper=time.sleep, cache_dir: Path | None = None,
             cache_name: str | None = None) -> dict:
    """Fetch JSON with backoff and a local cache. The cache exists because throttling is normal."""
    cache_dir = cache_dir if cache_dir is not None else DEFAULT_CACHE
    cached = cache_dir / cache_name if cache_name else _cache_path(cache_dir, url)
    if cached.exists():
        try:
            return json.loads(cached.read_text())
        except (OSError, ValueError):
            pass  # a damaged cache must never be fatal
    delay = 20
    last: Exception | None = None
    for attempt in range(tries):
        try:
            response = s.get(url, timeout=30)
        except requests.RequestException as exc:
            last = exc
        else:
            if response.status_code == 200:
                payload = response.json()
                cache_dir.mkdir(parents=True, exist_ok=True)
                cached.write_text(json.dumps(payload))
                sleeper(0.4)  # the SEC asks for fewer than ten requests a second
                return payload
            if _agent_refused(response):
                raise requests.HTTPError(f"{response.status_code} for {url}: {AGENT_HELP}")
            if response.status_code not in RETRY_STATUS:
                response.raise_for_status()
            last = requests.HTTPError(f"{response.status_code} for {url}")
        if attempt < tries - 1:
            sleeper(delay)
            delay = min(delay * 2, 120)
    raise last if last is not None else RuntimeError(f"no attempt made for {url}")


def parse_acceptance(value) -> dt.datetime | None:
    """EDGAR acceptance timestamps look like 2024-02-15T16:05:31.000Z."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None  # a timestamp without a zone is not a timestamp
    return parsed.astimezone(dt.timezone.utc)


def to_date(value) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def earliest_availability(acceptance: dt.datetime | None,
                          lag_minutes: int = 15) -> dt.datetime | None:
    """Acceptance is when EDGAR took the filing, not when anyone could act on it."""
    if acceptance is None:
        return None
    return acceptance + dt.timedelta(minutes=lag_minutes)


def classify(form: str, items: str) -> tuple[bool, str]:
    """Is this filing a candidate disclosure surface, and why."""
    form = (form or "").strip().upper()
    base = form[:-2] if form.endswith("/A") else form
    item_set = {i.strip() for i in (items or "").split(",") if i.strip()}
    if base in ("10-K", "10-Q"):
        return True, "periodic report"
    if base == "8-K":
        matched = sorted(item_set & CANDIDATE_8K_ITEMS)
        if matched:
            return True, "8-K items " + ", ".join(matched)
        return False, "8-K item not on the candidate list"
    return False, "form not on the candidate list" if form else "no form"


def sealed_start(history_start: dt.date, history_end: dt.date) -> dt.date:
    """The shorter of the most recent fifth of history or the most recent two years."""
    span_days = (history_end - history_start).days
    return max(history_end - dt.timedelta(days=int(span_days * 0.2)),
               history_end - dt.timedelta(days=365 * 2))


def ticker_map(s: requests.Session) -> dict[str, int]:
    # Named cache: this file is large, static for days, and expensive to re-fetch under throttling.
    payload = get_json(s, TICKERS_URL, cache_name="company_tickers.json")
    return {row["ticker"].upper(): int(row["cik_str"]) for row in payload.values()}


def entries_for_cik(s: requests.Session, cik: int, older_files: int = 6):
    """Every recent filing, then the older submissions files, newest first."""
    payload = get_json(s, SUBMISSIONS_URL.format(cik=cik))
    recent = payload.get("filings", {}).get("recent", {})
    keys = list(recent)
    for i in range(len(recent.get("accessionNumber", []))):
        yield {k: recent[k][i] for k in keys}
    for extra in payload.get("filings", {}).get("files", [])[:older_files]:
        name = extra.get("name")
        if not name:
            continue
        older = get_json(s, OLD_SUBMISSIONS_URL.format(name=name))
        older_keys = list(older)
        for i in range(len(older.get("accessionNumber", []))):
            yield {k: older[k][i] for k in older_keys}


def record(cik: int, ticker: str, entry: dict, lag_minutes: int,
           sealed_from: dt.date) -> dict:
    """One filing as a row. Every unresolved field is labelled, not guessed."""
    form = (entry.get("form") or "").strip()
    accepted = parse_acceptance(entry.get("acceptanceDateTime"))
    usable = earliest_availability(accepted, lag_minutes)
    filed = to_date(entry.get("filingDate"))
    candidate, reason = classify(form, entry.get("items", ""))
    accession = (entry.get("accessionNumber") or "").replace("-", "")
    document = entry.get("primaryDocument") or ""
    return {
        "ticker": ticker,
        "cik": cik,
        "form": form,
        "filed_date": filed.isoformat() if filed else "",
        "acceptance_utc": accepted.isoformat() if accepted else "",
        "acceptance_et": accepted.astimezone(ET).isoformat(sep=" ", timespec="seconds") if accepted else "",
        "earliest_availability_utc": usable.isoformat() if usable else "",
        "processing_lag_minutes": lag_minutes,
        "timestamp_status": "acceptance recorded" if accepted else "no acceptance timestamp",
        "period": entry.get("reportDate") or "",
        "items": entry.get("items") or "",
        "candidate_surface": candidate,
        "surface_reason": reason,
        "in_sealed_window": bool(filed and filed >= sealed_from),
        "press_release_unchecked": True,
        "document_url": DOCUMENT_URL.format(cik=cik, accession=accession, doc=document) if document else "",
        "source_receipt": SUBMISSIONS_URL.format(cik=cik),
    }


def build_rows(tickers: list[str], history_start: dt.date, history_end: dt.date,
               lag_minutes: int = 15, session_factory=session) -> list[dict]:
    """Rows for the candidate surfaces of every requested firm, dev and sealed alike."""
    s = session_factory()
    lookup = ticker_map(s)
    sealed_from = sealed_start(history_start, history_end)
    rows: list[dict] = []
    for ticker in tickers:
        cik = lookup.get(ticker.upper())
        if cik is None:
            rows.append({"ticker": ticker, "cik": 0, "form": "",
                         "timestamp_status": "ticker not found in the EDGAR ticker map",
                         "source_receipt": TICKERS_URL})
            continue
        for entry in entries_for_cik(s, cik):
            filed = to_date(entry.get("filingDate"))
            if filed is None or not (history_start <= filed <= history_end):
                continue
            form = (entry.get("form") or "").strip().upper()
            base = form[:-2] if form.endswith("/A") else form
            if base not in CANDIDATE_FORMS:
                continue
            rows.append(record(cik, ticker, entry, lag_minutes, sealed_from))
    return rows
