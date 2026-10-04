#!/usr/bin/env python3
"""Offline tests for the Snowflake research sidecar; no credentials or network calls."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from snowflake.research_sidecar import CortexResearchSidecar, account_url_from_host  # noqa: E402


def main() -> int:
    failures: list[str] = []

    def check(name: str, condition: bool) -> None:
        if condition:
            print(f"ok   {name}")
        else:
            failures.append(name)
            print(f"FAIL {name}")

    def rejects(name: str, operation) -> None:
        try:
            operation()
        except ValueError:
            check(name, True)
        else:
            check(name, False)

    check("account host normalizes to HTTPS",
          account_url_from_host("account.snowflakecomputing.com/") ==
          "https://account.snowflakecomputing.com")
    rejects("account URL rejects paths",
            lambda: account_url_from_host("https://account.snowflakecomputing.com/path"))
    rejects("client rejects non-HTTPS", lambda: CortexResearchSidecar("http://host", "p", "m"))

    sidecar = CortexResearchSidecar("https://account.snowflakecomputing.com", "test-pat", "model")
    calls = []

    def fake_search_post(path, body):
        calls.append((path, body))
        return {"results": [{
            "TICKER": "PWR", "ACCESSION": "0001", "DOCUMENT_NAME": "ex99.htm",
            "DOCUMENT_URL": "https://sec.gov/filing", "MATCHED_TEXT_CONTEXTS": "Verbatim passage",
            "FILED_DATE": "2026-01-01", "AVAILABLE_AT": "2026-01-01T21:00:00Z",
            "DOCUMENT_SHA256": "abc",
        }]}

    sidecar._post = fake_search_post  # type: ignore[method-assign]
    sources = sidecar.search("project timing disclosure", ticker="pwr")
    check("search returns exact excerpt", len(sources) == 1 and sources[0].excerpt == "Verbatim passage")
    check("search uses separate Cortex Search endpoint",
          calls[0][0].endswith("/cortex-search-services/SEC_FILING_EVIDENCE:query"))
    check("search filters on selected ticker",
          calls[0][1]["filter"] == {"@eq": {"TICKER": "PWR"}})
    rejects("ticker allowlist blocks arbitrary symbols",
            lambda: sidecar.search("question", ticker="UNKNOWN"))
    rejects("retrieval limit is capped at five",
            lambda: sidecar.search("question", limit=6))

    answer_sidecar = CortexResearchSidecar("https://account.snowflakecomputing.com", "test-pat", "model")
    answer_sidecar.search = lambda question, ticker=None, limit=5: sources  # type: ignore[method-assign]
    inference_calls = []

    def fake_inference(path, body):
        inference_calls.append((path, body))
        return {"choices": [{"message": {"content": "The source discusses a timing change. [A]"}}]}

    answer_sidecar._post = fake_inference  # type: ignore[method-assign]
    response = answer_sidecar.answer("What does the filing discuss?", ticker="PWR")
    check("answer returns qualitative answer and intact citation source",
          not response.suppressed and response.sources[0].excerpt == "Verbatim passage" and "[A]" in response.answer)
    prompt = inference_calls[0][1]["messages"][0]["content"]
    check("prompt forbids outputting numeric text", "do not write any digits" in prompt)
    check("completion endpoint is Snowflake Cortex REST API",
          inference_calls[0][0].endswith("/api/v2/cortex/v1/chat/completions"))

    def numeric_inference(path, body):
        return {"choices": [{"message": {"content": "The filing reported 42 units. [A]"}}]}

    answer_sidecar._post = numeric_inference  # type: ignore[method-assign]
    suppressed = answer_sidecar.answer("What does the filing discuss?", ticker="PWR")
    check("numeric generated prose is suppressed instead of shown", suppressed.suppressed and "42" not in suppressed.answer)

    print(f"\n{12 - len(failures)}/12 passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
