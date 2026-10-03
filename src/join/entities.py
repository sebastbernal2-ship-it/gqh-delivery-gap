"""Match an EIA entity name against SEC registrant names, and show the evidence.

Why this is not a lookup: EIA names the entity that developed or operates a plant, and most of them are
project companies, not registrants. "Rye Development" and "Castleman Power Development LLC" have no
equity. A match therefore needs a score and an audit trail, and there are three honest outcomes:

- **matched**: one registrant dominates and the first significant token agrees
- **ambiguous**: two registrants score within a hair, so no attribution is claimed
- **unmatched**: nothing clears the bar, which is the common and important case

Nothing here guesses a parent company. A subsidiary whose name does not carry the parent's is unmatched,
and the coverage report says how much capacity that leaves unattributed.
"""
from __future__ import annotations

import re

# Legal forms carry no identity, so they are removed before matching.
SUFFIXES = {
    "inc", "incorporated", "corp", "corporation", "co", "company", "llc", "llp", "lp", "lllp", "ltd",
    "limited", "plc", "sa", "nv", "ag", "gmbh", "pty", "holdings", "holding", "group", "the",
    "of", "and", "&",
}

MIN_SCORE = 0.5
AMBIGUITY_MARGIN = 0.1
MIN_TOKEN = 3
# The SEC ticker map is not a security master: it carries funds, preferreds and warrants, and a
# loose matcher happily attributes a power plant to a freight broker. A candidate may therefore
# introduce no significant word the entity does not already carry.
STOPWORD_TITLES = ("fund", "trust", "etf", "income", "portfolio", "index", "shares", "warrant",
                   "rights", "unit", "depositary", "notes", "bond")


def tokens(name: str) -> list[str]:
    """Significant words in a company name, in order, with single letters and legal forms removed."""
    cleaned = re.sub(r"[^a-z0-9& ]+", " ", (name or "").lower())
    return [t for t in cleaned.split() if t not in SUFFIXES and len(t) >= MIN_TOKEN]


def normalize(name: str) -> str:
    return " ".join(tokens(name))


def score(entity_tokens: list[str], candidate_tokens: list[str]) -> float:
    """Share of the entity's significant words that the candidate also carries."""
    if not entity_tokens or not candidate_tokens:
        return 0.0
    shared = len(set(entity_tokens) & set(candidate_tokens))
    return shared / len(set(entity_tokens))


def best_match(entity: str, candidates: list[tuple[str, int, str]]) -> dict:
    """The best registrant for one entity, with the runner up so ambiguity is visible.

    ``candidates`` is a list of (title, cik, ticker).
    """
    entity_tokens = tokens(entity)
    scored: list[tuple[float, tuple[str, int, str]]] = []
    entity_set = set(entity_tokens)
    for candidate in candidates:
        title = (candidate[0] or "").lower()
        if any(word in title for word in STOPWORD_TITLES):
            continue
        candidate_tokens = tokens(candidate[0])
        if not candidate_tokens:
            continue
        # The first significant word must agree, otherwise "Energy Transfer" would match everything.
        if entity_tokens and entity_tokens[0] not in candidate_tokens:
            continue
        # And the candidate must bring no new significant word of its own.
        if not set(candidate_tokens) <= entity_set:
            continue
        value = score(entity_tokens, candidate_tokens)
        if value > 0:
            scored.append((value, candidate))
    scored.sort(key=lambda pair: (-pair[0], pair[1][0]))
    if not scored:
        return {"status": "unmatched", "score": 0.0, "runner_up": 0.0,
                "title": "", "cik": "", "ticker": ""}
    value, candidate = scored[0]
    runner_up = scored[1][0] if len(scored) > 1 else 0.0
    if value < MIN_SCORE:
        return {"status": "unmatched", "score": value, "runner_up": runner_up,
                "title": "", "cik": "", "ticker": ""}
    if runner_up and (value - runner_up) < AMBIGUITY_MARGIN:
        return {"status": "ambiguous", "score": value, "runner_up": runner_up,
                "title": candidate[0], "cik": "", "ticker": ""}
    return {"status": "matched", "score": value, "runner_up": runner_up,
            "title": candidate[0], "cik": candidate[1], "ticker": candidate[2]}


def match_entities(entities: list[str], candidates: list[tuple[str, int, str]]) -> dict[str, dict]:
    return {entity: best_match(entity, candidates) for entity in entities}


def coverage(rows: list[dict]) -> dict:
    """How much slipped capacity attributes to a registrant, and to whom."""
    by_status: dict[str, float] = {}
    by_ticker: dict[str, float] = {}
    for row in rows:
        try:
            mw = float(row.get("capacity_mw") or 0)
        except ValueError:
            mw = 0.0
        status = row.get("match_status") or "unmatched"
        by_status[status] = by_status.get(status, 0.0) + mw
        # Only a verified row puts capacity against a ticker. A proposal stays a proposal.
        if status == "verified":
            ticker = row.get("ticker") or "?"
            by_ticker[ticker] = by_ticker.get(ticker, 0.0) + mw
    return {"by_status": by_status, "by_ticker": by_ticker}
