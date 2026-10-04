"""Read-only Snowflake Cortex RAG sidecar for backtest research screens.

This module retrieves cited filing snippets for a selected ticker and asks Cortex
for a qualitative evidence summary. It deliberately accepts no prices, fills,
order-book arrays, strategy signals, or backtest metric values.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ALLOWED_TICKERS = frozenset({"PWR", "ETN", "EME", "DLR"})
SEARCH_COLUMNS = [
    "TICKER", "ACCESSION", "DOCUMENT_NAME", "DOCUMENT_URL", "MATCHED_TEXT_CONTEXTS",
    "FILED_DATE", "ACCEPTANCE_UTC", "AVAILABLE_AT", "DOCUMENT_SHA256",
]


class SnowflakeAPIError(RuntimeError):
    """Sanitized API failure; never includes request headers or credential values."""


@dataclass(frozen=True)
class EvidenceSource:
    ticker: str
    accession: str
    document_name: str
    document_url: str
    excerpt: str
    filed_date: str | None = None
    accepted_at: str | None = None
    available_at: str | None = None
    document_sha256: str | None = None


@dataclass(frozen=True)
class ResearchAnswer:
    answer: str
    sources: tuple[EvidenceSource, ...]
    model: str
    suppressed: bool = False


class CortexResearchSidecar:
    """Small synchronous client for the Snowflake Cortex Search and inference REST APIs.

    Configure with ``SNOWFLAKE_ACCOUNT_URL``, ``SNOWFLAKE_PAT`` and
    ``SNOWFLAKE_CORTEX_MODEL`` in the server environment. Never expose the PAT to a
    browser or commit it to source control.
    """

    def __init__(self, account_url: str, pat: str, model: str, timeout: float = 20.0):
        if not account_url.startswith("https://"):
            raise ValueError("SNOWFLAKE_ACCOUNT_URL must use https")
        if not pat:
            raise ValueError("Snowflake PAT is required")
        if not model:
            raise ValueError("A Cortex model available to this account is required")
        self._base = account_url.rstrip("/")
        self._pat = pat
        self.model = model
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> "CortexResearchSidecar":
        return cls(
            os.environ["SNOWFLAKE_ACCOUNT_URL"],
            os.environ["SNOWFLAKE_PAT"],
            os.environ["SNOWFLAKE_CORTEX_MODEL"],
        )

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            self._base + path,
            data=json.dumps(body, separators=(",", ":")).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._pat}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise SnowflakeAPIError(f"Snowflake API returned HTTP {exc.code}") from None
        except (URLError, TimeoutError) as exc:
            raise SnowflakeAPIError(f"Snowflake API request failed: {type(exc).__name__}") from None
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise SnowflakeAPIError("Snowflake API returned invalid JSON") from None
        if not isinstance(payload, dict):
            raise SnowflakeAPIError("Snowflake API returned an unexpected response shape")
        return payload

    def search(self, question: str, ticker: str | None = None, limit: int = 5) -> tuple[EvidenceSource, ...]:
        """Retrieve up to five filing snippets; ticker filter is optional but allowlisted."""
        question = question.strip()
        if not question or len(question) > 1000:
            raise ValueError("Question must contain 1–1000 characters")
        if not 1 <= limit <= 5:
            raise ValueError("Evidence retrieval limit must be between 1 and 5")
        ticker = ticker.upper() if ticker else None
        if ticker is not None and ticker not in ALLOWED_TICKERS:
            raise ValueError(f"Ticker must be one of {', '.join(sorted(ALLOWED_TICKERS))}")

        path = (
            "/api/v2/databases/VECTOR_RESEARCH/schemas/RESEARCH/"
            "cortex-search-services/SEC_FILING_EVIDENCE:query"
        )
        body: dict[str, Any] = {"query": question, "columns": SEARCH_COLUMNS, "limit": limit}
        if ticker:
            body["filter"] = {"@eq": {"TICKER": ticker}}
        response = self._post(path, body)
        records = response.get("results", [])
        if not isinstance(records, list):
            raise SnowflakeAPIError("Cortex Search response omitted a results list")

        sources = []
        for row in records[:limit]:
            if not isinstance(row, dict):
                continue
            sources.append(EvidenceSource(
                ticker=str(row.get("TICKER", "")),
                accession=str(row.get("ACCESSION", "")),
                document_name=str(row.get("DOCUMENT_NAME", "")),
                document_url=str(row.get("DOCUMENT_URL", "")),
                excerpt=str(row.get("MATCHED_TEXT_CONTEXTS", "")),
                filed_date=row.get("FILED_DATE"),
                accepted_at=row.get("ACCEPTANCE_UTC"),
                available_at=row.get("AVAILABLE_AT"),
                document_sha256=row.get("DOCUMENT_SHA256"),
            ))
        return tuple(sources)

    def answer(self, question: str, ticker: str | None = None, limit: int = 5) -> ResearchAnswer:
        """Return a qualitative, cited evidence note plus original retrieved excerpts.

        Only the question and filing snippets are sent to the model. Backtest metrics,
        prices, fills, and order-book observations are never accepted by this interface.
        """
        sources = self.search(question, ticker=ticker, limit=limit)
        if not sources:
            return ResearchAnswer("No matching filing evidence was returned.", (), self.model)

        evidence = [{
            "source_ref": chr(ord("A") + index),
            "ticker": item.ticker,
            "accession": item.accession,
            "document_name": item.document_name,
            "document_url": item.document_url,
            "filed_date": item.filed_date,
            "available_at": item.available_at,
            "verbatim_excerpt": item.excerpt,
        } for index, item in enumerate(sources)]
        system = (
            "You are a research assistant attached to a deterministic order-book backtester. "
            "You may describe only the filing evidence supplied below. Do not recommend trades, "
            "change backtest inputs or outputs, calculate or restate any numeric value, price, "
            "return, fill, or performance metric. Keep the answer qualitative and do not write "
            "any digits. Distinguish filing time from availability time. Every factual sentence "
            "must cite one or more source labels like [A] from the supplied evidence. State when "
            "evidence is insufficient."
        )
        user = (
            f"Research question: {question}\n\n"
            "Retrieved source snippets (display these verbatim in the UI separately from your answer):\n"
            + json.dumps(evidence, ensure_ascii=False)
        )
        response = self._post(
            "/api/v2/cortex/v1/chat/completions",
            {
                "model": self.model,
                "temperature": 0,
                "max_tokens": 700,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        try:
            answer = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise SnowflakeAPIError("Cortex inference response omitted assistant text") from None
        if not isinstance(answer, str):
            raise SnowflakeAPIError("Cortex inference returned a non-text answer")
        if re.search(r"\d", answer):
            return ResearchAnswer(
                answer="AI response hidden because it contained numeric text. Review the verbatim source cards.",
                sources=sources,
                model=self.model,
                suppressed=True,
            )
        return ResearchAnswer(answer=answer, sources=sources, model=self.model)


def account_url_from_host(host: str) -> str:
    """Normalize a Snowflake hostname/account URL without accepting arbitrary schemes."""
    value = host.strip().rstrip("/")
    if not value.startswith("https://"):
        value = "https://" + value
    if "/" in value.removeprefix("https://"):
        raise ValueError("Provide the Snowflake account host only, without a path")
    return value
