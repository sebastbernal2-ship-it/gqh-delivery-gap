"""Bounded source retrieval with immutable bytes and resumable, explicit request receipts."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, build_opener, HTTPRedirectHandler, HTTPSHandler


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def strict_json(data):
    def invalid(value):
        raise ValueError("nonfinite JSON value")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    result = json.loads(data, parse_constant=invalid, object_pairs_hook=unique)
    canonical(result)  # Also rejects overflow such as 1e999 parsed as float infinity.
    return result


def public_url(url):
    p = urlparse(url)
    if p.scheme != "https" or p.username or p.password or p.fragment:
        raise ValueError("invalid source URL")
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
             if k.lower() not in {"apikey", "api_key", "token", "access_token"}]
    return urlunparse(p._replace(query=urlencode(sorted(query))))


def atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w") as f:
        f.write(canonical(value) + "\n")
    tmp.replace(path)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Retrieval:
    """One writer per run directory. Resume reads validated retained bytes, never refetches silently."""
    def __init__(self, root: Path, api_key: str = "", delay: float = 0.35):
        import certifi
        self.root, self.key, self.delay = root, api_key, delay
        self.last_request = 0.0
        (root / "objects").mkdir(parents=True, exist_ok=True)
        (root / "requests").mkdir(exist_ok=True)
        self.opener = build_opener(NoRedirect(), HTTPSHandler(
            context=ssl.create_default_context(cafile=certifi.where())))

    def fetch(self, url, *, massive=False, max_bytes=10_000_000):
        url = public_url(url)
        if massive and urlparse(url).netloc != "api.massive.com":
            raise ValueError("refusing credential outside Massive origin")
        if massive and (not self.key or os.environ.get("GQH_MASSIVE_TEAM_STRATEGY_LICENSE") != "confirmed"):
            raise ValueError("Massive configuration or license assertion missing")
        identity = sha(url.encode())
        dest = self.root / "requests" / (identity + ".json")
        if dest.exists():
            receipt = strict_json(dest.read_bytes())
            data = (self.root / "objects" / receipt["sha256"]).read_bytes()
            if receipt["url"] != url or sha(data) != receipt["sha256"]:
                raise ValueError("cached source receipt mismatch")
            return data, receipt
        headers = {"User-Agent": "GQH-Delivery-Gap/0.2 research retrieval"}
        if massive:
            headers["Authorization"] = "Bearer " + self.key
        for attempt in range(5):
            time.sleep(max(0, self.last_request + self.delay - time.monotonic()))
            self.last_request = time.monotonic()
            try:
                with self.opener.open(Request(url, headers=headers), timeout=45) as response:
                    data = response.read(max_bytes + 1)
                    if len(data) > max_bytes:
                        raise ValueError("source size bound exceeded")
                    if self.key and self.key.encode() in data:
                        raise ValueError("source echoes credential; refusing retention")
                    receipt = {"url": url, "sha256": sha(data), "size_bytes": len(data),
                        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                        "http_status": response.status, "content_type": response.headers.get("Content-Type"),
                        "last_modified": response.headers.get("Last-Modified")}
                object_path = self.root / "objects" / receipt["sha256"]
                if not object_path.exists():
                    with object_path.open("xb") as f:
                        f.write(data)
                elif sha(object_path.read_bytes()) != receipt["sha256"]:
                    raise ValueError("existing object corrupted")
                atomic_json(dest, receipt)
                return data, receipt
            except HTTPError as exc:
                if exc.code not in (429, 500, 502, 503, 504) or attempt == 4:
                    raise RuntimeError(f"HTTP {exc.code}; response details suppressed") from None
            except (URLError, TimeoutError):
                if attempt == 4:
                    raise RuntimeError("network request exhausted; details suppressed") from None
            time.sleep(min(2 ** (attempt + 1), 20))
        raise RuntimeError("retrieval attempts exhausted")

    def pages(self, url, max_pages=1000):
        seen = set()
        while url:
            url = public_url(url)
            if url in seen or len(seen) >= max_pages:
                raise ValueError("pagination cycle or page bound exceeded")
            seen.add(url)
            data, receipt = self.fetch(url, massive=True)
            page = strict_json(data)
            if page.get("status") not in ("OK", "DELAYED", "DELISTED"):
                raise ValueError("provider returned unsuccessful status")
            rows = page.get("results", [])
            if not isinstance(rows, list):
                raise ValueError("expected list result")
            yield rows, receipt, page
            url = page.get("next_url")


def validate_bar(row, start_ms, end_ms):
    for name in ("o", "h", "l", "c", "v"):
        v = row.get(name)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError("invalid numeric bar field")
        if v < 0:
            raise ValueError("negative bar field")
    t = row.get("t")
    if isinstance(t, bool) or not isinstance(t, int) or not start_ms <= t < end_ms:
        raise ValueError("bar outside requested window")
    if row["h"] < max(row["o"], row["c"], row["l"]) or row["l"] > min(row["o"], row["c"], row["h"]):
        raise ValueError("inconsistent OHLC")
    if row.get("n") is not None and (isinstance(row["n"], bool) or not isinstance(row["n"], int) or row["n"] < 0):
        raise ValueError("invalid trade count")


def records_file(path: Path, records):
    """Deterministic local build; caller must keep one writer per path."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    count = 0
    with tmp.open("w") as f:
        for record in records:
            f.write(canonical(record) + "\n")
            count += 1
    tmp.replace(path)
    return {"rows": count, "sha256": sha(path.read_bytes()), "file": path.name}
