"""Download official daily archives; parse only the explicitly bounded first table."""
import argparse
import csv
import hashlib
import io
import json
import math
import re
import ssl
import certifi
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

ROOT = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/"
FILES = {"ff3": "F-F_Research_Data_Factors_daily_CSV.zip",
         "ff5": "F-F_Research_Data_5_Factors_2x3_daily_CSV.zip",
         "momentum": "F-F_Momentum_Factor_daily_CSV.zip",
         "industry12": "12_Industry_Portfolios_daily_CSV.zip"}
HEADERS = {"ff3": ["Mkt-RF", "SMB", "HML", "RF"],
           "ff5": ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"],
           "momentum": ["Mom"],
           "industry12": ["NoDur", "Durbl", "Manuf", "Enrgy", "Chems", "BusEq", "Telcm", "Utils", "Shops", "Hlth", "Money", "Other"]}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse_daily(blob, kind, start, end):
    """Percent -> decimal once; never consume equal-weight/annual tables as daily VW."""
    if start > end or kind not in HEADERS:
        raise ValueError("invalid bounds or archive kind")
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        names = [n for n in z.namelist() if n.lower().endswith('.csv')]
        if len(names) != 1 or z.getinfo(names[0]).file_size > 50_000_000:
            raise ValueError("expected one bounded CSV member")
        text = z.read(names[0]).decode('utf-8-sig')
    expected, found, begun, rows = HEADERS[kind], False, False, {}
    prefix = []
    for raw in csv.reader(io.StringIO(text)):
        fields = [x.strip() for x in raw]
        if not found:
            if fields and fields[0] == '' and fields[1:] == expected:
                if kind == 'industry12' and not any('Average Value Weighted Returns -- Daily' in x for x in prefix):
                    raise ValueError("industry value-weight daily section not identified")
                found = True
            else:
                prefix.append(','.join(fields))
            continue
        if not fields or not re.fullmatch(r'\d{8}', fields[0]):
            if begun:
                break
            continue
        begun = True
        day = datetime.strptime(fields[0], '%Y%m%d').date().isoformat()
        if not start <= day <= end:
            continue
        if day in rows or len(fields) != len(expected) + 1:
            raise ValueError("duplicate date or malformed factor row")
        values = [float(v) for v in fields[1:]]
        if any(not math.isfinite(v) or v in (-99.99, -999) for v in values):
            raise ValueError("missing/nonfinite research factor value")
        rows[day] = dict(zip(expected, (v / 100 for v in values)))
    if not found or not rows:
        raise ValueError("daily factor section/range absent")
    return rows


def fetch(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    # Confirm that these archives are linked by the official index, rather than silently switching sources.
    with urlopen(ROOT + 'data_library.html', timeout=60, context=ssl.create_default_context(cafile=certifi.where())) as response:
        index = response.read().decode('utf-8', errors='replace')
    receipt = {'retrieved_at': datetime.now(timezone.utc).isoformat(),
               'historical_availability_verified': False, 'files': {}}
    for kind, name in FILES.items():
        candidates = re.findall(r'href\s*=\s*["\']([^"\']+)["\']', index, flags=re.I)
        if not any(u.lower().endswith('/' + name.lower()) for u in candidates):
            raise ValueError(f"official index no longer links {name}")
        url = ROOT + 'ftp/' + name
        with urlopen(url, timeout=90, context=ssl.create_default_context(cafile=certifi.where())) as response:
            blob = response.read(50_000_001)
        if len(blob) > 50_000_000:
            raise ValueError("archive too large")
        path = output / name
        path.write_bytes(blob)
        receipt['files'][kind] = {'file': name, 'url': url, 'sha256': digest(path)}
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    result = fetch(args.output)
    print(json.dumps({'archives': list(result['files']), 'historical_availability_verified': False}))
