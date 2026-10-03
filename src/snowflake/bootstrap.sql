-- VECTOR / GQH Snowflake bootstrap
-- Review before running. No warehouse is created here.
-- Snowflake stays off the live order path; TigerData/q handle execution data.

CREATE DATABASE IF NOT EXISTS VECTOR_RESEARCH;
CREATE SCHEMA IF NOT EXISTS VECTOR_RESEARCH.RAW;
CREATE SCHEMA IF NOT EXISTS VECTOR_RESEARCH.NORMALIZED;
CREATE SCHEMA IF NOT EXISTS VECTOR_RESEARCH.FEATURES;
CREATE SCHEMA IF NOT EXISTS VECTOR_RESEARCH.RESEARCH;

CREATE TABLE IF NOT EXISTS VECTOR_RESEARCH.RAW.AWS_GPU_SPOT_PRICES (
  price_time TIMESTAMP_TZ NOT NULL,
  zone_id VARCHAR NOT NULL,
  instance_type VARCHAR NOT NULL,
  operating_system VARCHAR NOT NULL,
  usd_per_instance_hour NUMBER(24,9) NOT NULL,
  source_file VARCHAR NOT NULL,
  source_doi VARCHAR NOT NULL,
  source_md5 VARCHAR NOT NULL,
  license VARCHAR NOT NULL,
  ingested_at TIMESTAMP_TZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
  PRIMARY KEY (price_time, zone_id, instance_type, operating_system, source_file)
);
-- This source has a documented archive gap. Keep it explicit instead of filling it.
CREATE TABLE IF NOT EXISTS VECTOR_RESEARCH.RAW.AWS_GPU_SPOT_SOURCE_GAPS (
  source_doi VARCHAR NOT NULL,
  start_time TIMESTAMP_TZ NOT NULL,
  end_time_exclusive TIMESTAMP_TZ NOT NULL,
  reason VARCHAR NOT NULL,
  PRIMARY KEY (source_doi, start_time)
);

INSERT INTO VECTOR_RESEARCH.RAW.AWS_GPU_SPOT_SOURCE_GAPS
  (source_doi, start_time, end_time_exclusive, reason)
SELECT '10.5281/zenodo.23082767', '2026-03-01T00:00:00Z', '2026-07-01T00:00:00Z',
       'March through June absent from source archive; do not interpolate as observed prices'
WHERE NOT EXISTS (
  SELECT 1 FROM VECTOR_RESEARCH.RAW.AWS_GPU_SPOT_SOURCE_GAPS
  WHERE source_doi = '10.5281/zenodo.23082767'
    AND start_time = TO_TIMESTAMP_TZ('2026-03-01T00:00:00Z')
);

-- Descriptive daily rollup only. Historical collector availability is unknown, so this
-- view must not be joined as an available-at-the-time trading feature without new evidence.
CREATE VIEW IF NOT EXISTS VECTOR_RESEARCH.NORMALIZED.AWS_GPU_SPOT_DAILY AS
SELECT
  DATE_TRUNC('DAY', price_time) AS event_day,
  zone_id,
  instance_type,
  operating_system,
  COUNT(*) AS quote_count,
  MIN(usd_per_instance_hour) AS min_usd_per_instance_hour,
  MEDIAN(usd_per_instance_hour) AS median_usd_per_instance_hour,
  MAX(usd_per_instance_hour) AS max_usd_per_instance_hour,
  MIN(price_time) AS first_observation_at,
  MAX(price_time) AS last_observation_at
FROM VECTOR_RESEARCH.RAW.AWS_GPU_SPOT_PRICES
GROUP BY 1, 2, 3, 4;

CREATE TABLE IF NOT EXISTS VECTOR_RESEARCH.RAW.FILINGS_8K (
  filing_id VARCHAR NOT NULL,
  issuer_cik VARCHAR NOT NULL,
  ticker VARCHAR,
  filed_at TIMESTAMP_TZ NOT NULL,
  available_at TIMESTAMP_TZ NOT NULL,
  form_type VARCHAR NOT NULL,
  accession_number VARCHAR NOT NULL,
  item_codes ARRAY,
  filing_text VARCHAR,
  source_url VARCHAR,
  source_version VARCHAR,
  ingested_at TIMESTAMP_TZ NOT NULL,
  PRIMARY KEY (issuer_cik, accession_number)
);

CREATE TABLE IF NOT EXISTS VECTOR_RESEARCH.RAW.EQUITY_BARS (
  ticker VARCHAR NOT NULL,
  event_time TIMESTAMP_TZ NOT NULL,
  open NUMBER(24,9),
  high NUMBER(24,9),
  low NUMBER(24,9),
  close NUMBER(24,9),
  volume NUMBER(38,0),
  source VARCHAR NOT NULL,
  source_version VARCHAR,
  ingested_at TIMESTAMP_TZ NOT NULL,
  PRIMARY KEY (ticker, event_time, source)
);

CREATE TABLE IF NOT EXISTS VECTOR_RESEARCH.FEATURES.POINT_IN_TIME_PANEL (
  ticker VARCHAR NOT NULL,
  decision_time TIMESTAMP_TZ NOT NULL,
  compute_price NUMBER(24,9),
  compute_price_time TIMESTAMP_TZ,
  compute_age_seconds NUMBER(38,0),
  regional_spread NUMBER(24,9),
  filing_id VARCHAR,
  filing_available_at TIMESTAMP_TZ,
  return_1d NUMBER(24,12),
  volatility_20d NUMBER(24,12),
  feature_version VARCHAR NOT NULL,
  created_at TIMESTAMP_TZ NOT NULL
);

-- Post-load QA query. Expected for the current 2026-09 snapshot:
-- 1,592,024 rows, 31 source files, source period 2022-05-31 through 2026-09-30,
-- no null ingestion timestamps, and zero observations in the Mar-Jun 2026 gap.
SELECT
  COUNT(*) AS row_count,
  COUNT(DISTINCT source_file) AS source_file_count,
  MIN(price_time) AS min_price_time,
  TO_VARCHAR(MIN(price_time)) AS min_price_time_text,
  MAX(price_time) AS max_price_time,
  TO_VARCHAR(MAX(price_time)) AS max_price_time_text,
  COUNT_IF(ingested_at IS NULL) AS null_ingested_at_count,
  COUNT_IF(price_time >= TO_TIMESTAMP_TZ('2026-03-01T00:00:00Z')
       AND price_time < TO_TIMESTAMP_TZ('2026-07-01T00:00:00Z')) AS rows_in_source_gap
FROM VECTOR_RESEARCH.RAW.AWS_GPU_SPOT_PRICES;
