# AWS compute ingestion

Owner: vshnu1. This is data infrastructure, not a promoted signal or OOS result.

`normalize.cpp` converts Pauley's five-column TSV to CSV without floating-point
arithmetic. Scope: Linux/UNIX P3/P4/P5/P6 and G3/G4/G5/G6 GPU families, US East 1
and US West 2. Zone IDs are retained. Other EC2 products are deliberately excluded.
Prices remain exact decimal strings, USD per whole instance-hour, not GPU-hour.

Compile with `clang++ -std=c++17 -O2 normalize.cpp -o <ignored-data-path>/normalize`.
Run `<binary> --test` before ingestion. For each checksum-verified archive file:
`zstd -dc <archive> | <binary> <filename> <md5> > <ignored-data-path>/<filename>.csv`.
Header is always included. Normalization fails on malformed TSV or invalid retained
prices/timestamps; output is not ready for upload until the process exits successfully.

`bash src/aws_compute/fetch.sh` resumes interrupted archive downloads, verifies each
provider MD5, and publishes each CSV only after successful normalization. It does not
upload data or claim that TigerData contains it. It requires curl, zstd and clang++;
Python's standard library is used only to read provider JSON metadata.

Source: https://zenodo.org/records/23082767, DOI 10.5281/zenodo.23082767,
version 2026-09, CC BY 4.0. Origin: AWS DescribeSpotPriceHistory. Raw originals,
checksums and generated CSVs stay under ignored `data/`, never Git.

Archive inventory: annual 2022/2023 files; every month 2024/2025; Jan/Feb and
Jul/Aug/Sep 2026. Actual 2022 starts May 31, not January. March–June 2026 is
missing in this source. Do not insert guessed prices across that gap. Independently
recovered March data is not included here because zone-name mapping and license
require separate handling. SkyPilot-derived April–June snapshots remain excluded.

Keep event time separate from ingestion time. Historical collector-observed latency
is unknown. Monthly opening records may be synthetic boundary carry-in records;
do not automatically count them as price shocks. Repeated equal prices are retained
as observations, not asserted changes. No uniform sampling or capacity guarantee.

`schema.sql` creates an isolated table and gap register without changing existing
tables or access permissions. Import CSV columns in their header order. Verify row
counts, earliest/latest times and per-source counts after every import. Teammate
database roles are a separate explicit access-management step.

TigerData load (2026-10-03): the isolated `public.aws_gpu_spot_prices` table in service
`db-60704` contains 1,592,024 rows after the successful archive batches. Verified bounds
are 2022-05-31 18:50:49 UTC through 2026-09-30 23:00:00 UTC, with 62 retained instance
types. The March–June 2026 interval remains intentionally absent.
