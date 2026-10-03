-- Operational checks for the AWS compute archive loaded into TigerData.
-- Run after imports; these are diagnostic queries, not strategy definitions.

SELECT count(*) AS rows,
       min(price_time) AS first_price,
       max(price_time) AS last_price,
       count(DISTINCT instance_type) AS instance_types,
       count(DISTINCT source_file) AS source_files
FROM public.aws_gpu_spot_prices;

-- Confirm the documented source gap is still explicit.
SELECT source_doi, start_time, end_time_exclusive, reason
FROM public.aws_gpu_spot_source_gaps
ORDER BY start_time;

-- Counts by source file make partial or duplicate uploads visible.
SELECT source_file, count(*) AS rows,
       min(price_time) AS first_price,
       max(price_time) AS last_price
FROM public.aws_gpu_spot_prices
GROUP BY source_file
ORDER BY source_file;

-- Useful first diagnostic for price-change intervals. This does not claim
-- that every record is a provider quote at a uniform cadence.
WITH ordered AS (
  SELECT instance_type, zone_id, price_time, usd_per_instance_hour,
         lag(price_time) OVER (
           PARTITION BY instance_type, zone_id ORDER BY price_time
         ) AS prior_time,
         lag(usd_per_instance_hour) OVER (
           PARTITION BY instance_type, zone_id ORDER BY price_time
         ) AS prior_price
  FROM public.aws_gpu_spot_prices
)
SELECT instance_type, zone_id,
       count(*) FILTER (WHERE usd_per_instance_hour <> prior_price) AS price_changes,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY price_time - prior_time)
         FILTER (WHERE usd_per_instance_hour <> prior_price AND prior_time IS NOT NULL)
         AS median_change_interval
FROM ordered
GROUP BY instance_type, zone_id
ORDER BY price_changes DESC;
