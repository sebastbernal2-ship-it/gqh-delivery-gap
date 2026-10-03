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
  ingested_at TIMESTAMP_TZ NOT NULL,
  PRIMARY KEY (price_time, zone_id, instance_type, operating_system, source_file)
);

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

-- First load: tiny AWS/equity/filing sample; validate timestamps before scaling.
