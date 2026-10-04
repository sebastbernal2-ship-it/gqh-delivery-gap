-- Proposed operational output schema for Quanthacks order-book engine telemetry.
-- Apply only after verifying live TigerData plan/quota and available disk headroom.
-- Snowflake remains the source/research archive and immutable report authority.
-- This schema stores report metadata and engine-derived scalar/event telemetry, not raw market depth.

CREATE TABLE IF NOT EXISTS engine_run_reports (
  run_key CHAR(64) PRIMARY KEY,
  fixture_sha256 CHAR(64) NOT NULL,
  config_sha256 CHAR(64) NOT NULL,
  simulator_build TEXT NOT NULL,
  report_sha256 CHAR(64) NOT NULL,
  report_uri TEXT NOT NULL,
  source_hashes JSONB NOT NULL,
  venue TEXT NOT NULL,
  symbol TEXT NOT NULL,
  run_status TEXT NOT NULL CHECK (run_status IN ('complete', 'rejected', 'failed')),
  generated_at TIMESTAMPTZ NOT NULL,
  event_count BIGINT NOT NULL CHECK (event_count >= 0),
  chain_gaps BIGINT NOT NULL CHECK (chain_gaps >= 0),
  book_mismatch BOOLEAN NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS engine_metric_points (
  metric_time TIMESTAMPTZ NOT NULL,
  emitted_at TIMESTAMPTZ NOT NULL,
  run_key CHAR(64) NOT NULL REFERENCES engine_run_reports(run_key),
  venue TEXT NOT NULL,
  symbol TEXT NOT NULL,
  liquidity_mode TEXT NOT NULL DEFAULT '',
  output_kind TEXT NOT NULL,
  metric_name TEXT NOT NULL,
  metric_value NUMERIC(38, 12) NOT NULL,
  unit TEXT NOT NULL,
  source_report_sha256 CHAR(64) NOT NULL,
  PRIMARY KEY (metric_time, run_key, symbol, liquidity_mode, output_kind, metric_name)
);

SELECT create_hypertable('engine_metric_points', 'metric_time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS engine_metric_points_run_idx
  ON engine_metric_points (run_key, metric_time DESC);
CREATE INDEX IF NOT EXISTS engine_metric_points_series_idx
  ON engine_metric_points (venue, symbol, metric_name, metric_time DESC);

-- Dashboard-friendly run-level rollup. Values are grouped by metric/unit/mode;
-- this is observational aggregation only and never changes simulator accounting.
CREATE MATERIALIZED VIEW IF NOT EXISTS engine_metrics_1h
WITH (timescaledb.continuous) AS
SELECT time_bucket(INTERVAL '1 hour', metric_time) AS bucket,
       venue, symbol, liquidity_mode, output_kind, metric_name, unit,
       COUNT(*) AS observations,
       AVG(metric_value) AS mean_value,
       MIN(metric_value) AS min_value,
       MAX(metric_value) AS max_value
FROM engine_metric_points
GROUP BY bucket, venue, symbol, liquidity_mode, output_kind, metric_name, unit
WITH NO DATA;

-- Idempotent refresh policy; enable only after applying and confirming the intended retention.
SELECT add_continuous_aggregate_policy('engine_metrics_1h',
  start_offset => INTERVAL '30 days',
  end_offset => INTERVAL '1 hour',
  schedule_interval => INTERVAL '1 hour',
  if_not_exists => TRUE);
