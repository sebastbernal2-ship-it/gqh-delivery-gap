-- READ ONLY. Run each platform's block on that platform, using an authorized profile.
-- Keep dated query receipts privately; nothing here grants an entitlement or proves PIT data.

-- Snowflake: exact source/batch inventories (counts, not payloads/returns).
SELECT SOURCE_ID, BATCH_SHA256, COUNT(*) AS ROW_COUNT,
       COUNT(DISTINCT ROW_INDEX) AS DISTINCT_ROW_INDEX_COUNT,
       MIN(EVENT_TIME_TEXT) AS FIRST_EVENT, MAX(EVENT_TIME_TEXT) AS LAST_EVENT
FROM VECTOR_RESEARCH.RAW.SOURCE_RECORDS
GROUP BY SOURCE_ID, BATCH_SHA256;

SELECT VINTAGE_MONTH, SOURCE_FILE_SHA256, PLANNED_ROWS, OPERATING_ROWS,
       CANCELED_ROWS, STAGE_PATH, RETRIEVED_AT
FROM VECTOR_RESEARCH.RAW.EIA860M_FILE_MANIFESTS
ORDER BY VINTAGE_MONTH, SOURCE_FILE_SHA256;

-- Count reconciliation is necessary, not sufficient for original XLSX integrity/publication time.
SELECT VINTAGE_MONTH, SOURCE_FILE_SHA256, SHEET, COUNT(*) AS ROW_COUNT
FROM VECTOR_RESEARCH.RAW.EIA860M_GENERATOR_VINTAGES
GROUP BY VINTAGE_MONTH, SOURCE_FILE_SHA256, SHEET;

-- TigerData/PostgreSQL: no INSERT/DELETE/DROP. Limit/plan must be verified with service metadata.
SELECT pg_database_size(current_database()) AS DATABASE_BYTES;
SELECT source_id, batch_sha256, COUNT(*) AS row_count,
       COUNT(DISTINCT row_index) AS distinct_row_index_count,
       MIN(event_time_text) AS first_event, MAX(event_time_text) AS last_event
FROM public.gqh_source_records
GROUP BY source_id, batch_sha256;

SELECT source_id, batch_sha256, row_count, retrieved_at
FROM public.gqh_ingestion_manifests;
SELECT relname, pg_total_relation_size(relid) AS total_bytes
FROM pg_catalog.pg_statio_user_tables
ORDER BY total_bytes DESC;
