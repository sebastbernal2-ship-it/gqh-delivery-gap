#!/usr/bin/env bash
# Run from repository root. Downloads/generates only ignored data files.
set -euo pipefail
task_base="$(pwd)/data/aws-compute"
mkdir -p "$task_base/raw" "$task_base/csv"
clang++ -std=c++17 -O2 -Wall -Wextra -Werror src/aws_compute/normalize.cpp -o "$task_base/normalize"
"$task_base/normalize" --test
curl -L --fail --silent --show-error --retry 3 --retry-all-errors \
  https://zenodo.org/api/records/23082767 -o "$task_base/zenodo-record.json"
# Python only reads provider JSON metadata; prices are processed in C++.
while IFS=$'\t' read -r task_name task_md5 task_url; do
  task_raw="$task_base/raw/$task_name"
  task_csv="$task_base/csv/$task_name.csv"
  if [[ ! -f "$task_raw" ]] || [[ "$(md5 -q "$task_raw")" != "$task_md5" ]]; then
    # Resume interrupted inbound downloads, but trust only a matching checksum.
    curl -L --fail --silent --show-error --retry 3 --retry-all-errors \
      --continue-at - "$task_url" -o "$task_raw"
  fi
  if [[ "$(md5 -q "$task_raw")" != "$task_md5" ]]; then
    echo "Checksum mismatch: $task_name; do not import" >&2
    exit 1
  fi
  zstd -dc "$task_raw" | "$task_base/normalize" "$task_name" "$task_md5" > "$task_csv.pending"
  mv "$task_csv.pending" "$task_csv"
  echo "READY $task_name"
done < <(python3 - "$task_base/zenodo-record.json" <<'PY'
import json,re,sys
with open(sys.argv[1]) as source:
    record=json.load(source)
for item in sorted(record['files'], key=lambda item:item['key']):
    assert re.fullmatch(r'202[2-6](?:-[0-9]{2})?\.tsv\.zst',item['key'])
    checksum=item['checksum']
    assert re.fullmatch(r'md5:[0-9a-f]{32}',checksum)
    url=item['links']['self']
    assert url.startswith('https://zenodo.org/api/records/23082767/files/')
    print(item['key'],checksum[4:],url,sep='\t')
PY
)
echo "All source files validated and normalized. No database upload is implied."
