-- Read-only, pinned daily equity development input. Do not run through an artifact
-- channel until both raw-data egress and vendor/licensor rights are explicitly cleared.
-- Result columns are the minimum provenance and payload needed by panel.build.load_export.
-- Expected < 20,000 rows for the pinned 2016-01-04..2022-09-30 five-name window.
WITH selected AS (
    SELECT SOURCE_ID, BATCH_SHA256, ROW_INDEX, ROW_SHA256, LOADED_AT, PAYLOAD_JSON,
           TRY_PARSE_JSON(PAYLOAD_JSON) AS P
    FROM VECTOR_RESEARCH.RAW.SOURCE_RECORDS
    WHERE
      (SOURCE_ID = 'massive_bars'
       AND BATCH_SHA256 = 'bec91f7c380937d3d647ade8214968c13abd4bde032c9a7cf7741f0ee58306cd')
      OR (SOURCE_ID = 'massive_bars_unadjusted'
       AND BATCH_SHA256 = '17c538dd38a3ff939e78ee074934637efca91518db02048410ed088be603ff6c')
      OR (SOURCE_ID = 'massive_dividends'
       AND BATCH_SHA256 = 'ac84b5535b5bb86ef32acbba49877aca87d3ccf204318d329c8fe64854322e76')
      OR (SOURCE_ID = 'massive_splits'
       AND BATCH_SHA256 = '07c65ecbfac427f5b32e79329c4a4557501950e9268444536571ce95b3d28480')
), bounded AS (
    SELECT SOURCE_ID, BATCH_SHA256, ROW_INDEX, ROW_SHA256, LOADED_AT, PAYLOAD_JSON
    FROM selected
    WHERE
      (SOURCE_ID IN ('massive_bars', 'massive_bars_unadjusted')
       AND P:ticker::STRING IN ('PWR', 'ETN', 'EME', 'DLR', 'SPY')
       AND TRY_TO_DATE(LEFT(P:bar_time_utc::STRING, 10)) BETWEEN '2016-01-04' AND '2022-09-30')
      OR (SOURCE_ID = 'massive_dividends'
       AND P:ticker::STRING IN ('PWR', 'ETN', 'EME', 'DLR', 'SPY')
       AND TRY_TO_DATE(P:ex_dividend_date::STRING) BETWEEN '2016-01-04' AND '2022-09-30')
      OR (SOURCE_ID = 'massive_splits'
       AND P:ticker::STRING IN ('PWR', 'ETN', 'EME', 'DLR', 'SPY'))
)
SELECT SOURCE_ID, BATCH_SHA256, ROW_INDEX, ROW_SHA256, LOADED_AT, PAYLOAD_JSON
FROM bounded
ORDER BY SOURCE_ID, BATCH_SHA256, ROW_INDEX
