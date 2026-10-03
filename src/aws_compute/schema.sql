CREATE TABLE IF NOT EXISTS public.aws_gpu_spot_prices (
  price_time timestamptz NOT NULL,
  zone_id text NOT NULL,
  instance_type text NOT NULL,
  operating_system text NOT NULL CHECK (operating_system = 'Linux/UNIX'),
  usd_per_instance_hour numeric(24,9) NOT NULL CHECK (usd_per_instance_hour >= 0),
  source_file text NOT NULL,
  source_doi text NOT NULL,
  source_md5 text NOT NULL,
  license text NOT NULL,
  ingested_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (price_time, zone_id, instance_type, operating_system, source_file)
);
CREATE INDEX IF NOT EXISTS aws_gpu_spot_series_time
  ON public.aws_gpu_spot_prices (instance_type, zone_id, price_time);
CREATE TABLE IF NOT EXISTS public.aws_gpu_spot_source_gaps (
  source_doi text NOT NULL,
  start_time timestamptz NOT NULL,
  end_time_exclusive timestamptz NOT NULL,
  reason text NOT NULL,
  PRIMARY KEY (source_doi, start_time)
);
INSERT INTO public.aws_gpu_spot_source_gaps VALUES
 ('10.5281/zenodo.23082767', '2026-03-01T00:00:00Z', '2026-07-01T00:00:00Z',
  'March through June absent from source archive; do not interpolate as observed prices')
ON CONFLICT DO NOTHING;
