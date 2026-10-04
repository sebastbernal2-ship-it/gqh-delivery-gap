-- Pinned public BTC market-book projection, no account fills or full raw manifests.
-- Run using the existing snowflake-query workflow; limit_rows=5000.
-- A 5000-row result is treated as potentially truncated by book_panel.py.
WITH r AS (
  SELECT ROW_INDEX, ROW_SHA256, TRY_PARSE_JSON(PAYLOAD_JSON) AS p
  FROM VECTOR_RESEARCH.RAW.RESEARCH_ACQUISITION_ROWS
  WHERE RUN_ID='27a69e4024235408eaff54876c781d0b9135713bb71780a386e16ce6db46fb2a'
)
SELECT ROW_INDEX, ROW_SHA256, p:data AS BOOK,
       p:source_sha256::VARCHAR AS SOURCE_SHA256,
       p:quality_flags AS QUALITY_FLAGS
FROM r
WHERE p:record_type::VARCHAR='hyperliquid_l2_snapshot'
  AND p:data:coin::VARCHAR='BTC'
ORDER BY ROW_INDEX
LIMIT 5000
