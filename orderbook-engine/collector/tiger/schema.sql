-- LEGACY input-capture schema for Tiger Cloud / TimescaleDB.
-- Existing rows were sourced from Binance BTCUSDT and are quarantined. Do not add
-- strategy data here or treat these rows as Hyperliquid. New TigerData project
-- writes should use engine_output_schema.sql after quota approval.
-- Apply this file only after reviewing the target Tiger service.

CREATE TABLE IF NOT EXISTS source_manifests (
  source_id UUID PRIMARY KEY,
  source_kind TEXT NOT NULL,
  source_uri TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  captured_at TIMESTAMPTZ,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS depth_events (
  event_key TEXT NOT NULL,
  received_time TIMESTAMPTZ NOT NULL,
  event_time_ms BIGINT NOT NULL,
  symbol TEXT NOT NULL,
  segment BIGINT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('snapshot', 'update')),
  applied BOOLEAN NOT NULL,
  last_update_id BIGINT,
  first_update_id BIGINT,
  final_update_id BIGINT,
  previous_update_id BIGINT,
  bids JSONB NOT NULL,
  asks JSONB NOT NULL,
  source_path TEXT NOT NULL,
  source_sha256 TEXT NOT NULL,
  PRIMARY KEY (received_time, event_key)
);

SELECT create_hypertable('depth_events', 'received_time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS depth_events_symbol_time_idx
  ON depth_events (symbol, received_time);
CREATE INDEX IF NOT EXISTS depth_events_source_idx
  ON depth_events (source_sha256);

CREATE TABLE IF NOT EXISTS trade_events (
  event_key TEXT NOT NULL,
  received_time TIMESTAMPTZ NOT NULL,
  trade_time_ms BIGINT NOT NULL,
  symbol TEXT NOT NULL,
  trade_id TEXT NOT NULL,
  price NUMERIC NOT NULL,
  quantity NUMERIC NOT NULL,
  buyer_is_maker BOOLEAN,
  source_path TEXT NOT NULL,
  source_sha256 TEXT NOT NULL,
  PRIMARY KEY (received_time, event_key)
);

SELECT create_hypertable('trade_events', 'received_time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS trade_events_symbol_time_idx
  ON trade_events (symbol, received_time);

CREATE TABLE IF NOT EXISTS observations (
  observed_at TIMESTAMPTZ NOT NULL,
  data_type TEXT NOT NULL,
  source TEXT NOT NULL,
  symbol TEXT,
  payload JSONB NOT NULL,
  source_sha256 TEXT
);

SELECT create_hypertable('observations', 'observed_at', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS observations_type_time_idx
  ON observations (data_type, observed_at);
