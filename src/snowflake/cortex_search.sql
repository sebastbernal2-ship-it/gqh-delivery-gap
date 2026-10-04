-- Optional, cost-bearing RAG index for immutable SEC filing snippets.
-- Run only after RAW.SEC_FILING_DOCUMENTS is populated and the team accepts Cortex
-- Search serving/refresh consumption. Static 2016-present filings do not need a
-- near-real-time refresh, so this starts at a one-day target lag.
-- This creates a separate search service; it does not edit source tables.

CREATE CORTEX SEARCH SERVICE IF NOT EXISTS VECTOR_RESEARCH.RESEARCH.SEC_FILING_EVIDENCE
  ON MATCHED_TEXT_CONTEXTS
  PRIMARY KEY (ACCESSION, DOCUMENT_NAME, DOCUMENT_SHA256)
  ATTRIBUTES TICKER, ACCESSION, DOCUMENT_NAME, DOCUMENT_URL, FILED_DATE,
             ACCEPTANCE_UTC, AVAILABLE_AT, DOCUMENT_SHA256
  WAREHOUSE = COMPUTE_WH
  TARGET_LAG = '1 day'
  AS (
    SELECT
      MATCHED_TEXT_CONTEXTS,
      TICKER,
      ACCESSION,
      DOCUMENT_NAME,
      DOCUMENT_URL,
      FILED_DATE,
      ACCEPTANCE_UTC,
      AVAILABLE_AT,
      DOCUMENT_SHA256
    FROM VECTOR_RESEARCH.RAW.SEC_FILING_DOCUMENTS
    WHERE MATCHED_TEXT_CONTEXTS IS NOT NULL
      AND LENGTH(MATCHED_TEXT_CONTEXTS) > 2
  );

-- Confirm indexing/serving status before wiring an application to the REST endpoint.
SHOW CORTEX SEARCH SERVICES IN SCHEMA VECTOR_RESEARCH.RESEARCH;
