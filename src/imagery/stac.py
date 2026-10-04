"""Find imagery for a site, and choose the scene a person would choose.

Selection rules, declared here so they cannot drift: prefer the scene with the least cloud, within a date
window, from the Sentinel-2 L2A collection whose assets are reachable over HTTPS. The visual asset is what is
read, because it is the RGB rendering a human would look at.
"""
from __future__ import annotations

import calendar
import datetime as dt

import requests

from imagery.validation import validate_scene

UA = {"User-Agent": "gqh-delivery-gap research research@example.com"}
SEARCH = "https://earth-search.aws.element84.com/v1/search"
COLLECTIONS = ("sentinel-2-c1-l2a", "sentinel-2-l2a", "sentinel-2-pre-c1-l2a")


def month_window(month: str, before: int = 1, after: int = 1) -> tuple[str, str]:
    """A date interval of whole calendar months around a year-month, as the API wants it.

    Calendar arithmetic rather than day counts, because thirty day steps drift and the first version of this
    returned an end date that a test disagreed with by a day.
    """
    year, number = (int(part) for part in month.split("-"))

    def shift(year: int, month: int, months: int) -> tuple[int, int]:
        total = year * 12 + (month - 1) + months
        return total // 12, total % 12 + 1

    start_year, start_month = shift(year, number, -before)
    end_year, end_month = shift(year, number, after)
    end_day = calendar.monthrange(end_year, end_month)[1]
    return dt.date(start_year, start_month, 1).isoformat(), dt.date(end_year, end_month, end_day).isoformat()


def search(lat: float, lon: float, month: str, span: float = 0.05, max_cloud: float = 20.0,
           limit: int = 6) -> list[dict]:
    """Scenes covering a small box around a site, cloudiest filtered out at the API."""
    start, end = month_window(month)
    bbox = [lon - span, lat - span, lon + span, lat + span]
    for collection in COLLECTIONS:
        payload = {"collections": [collection], "bbox": bbox,
                   "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z",
                   "query": {"eo:cloud_cover": {"lt": max_cloud}}, "limit": limit}
        try:
            response = requests.post(SEARCH, json=payload, headers=UA, timeout=90)
        except requests.RequestException:
            continue
        if response.status_code != 200:
            continue
        items = response.json().get("features", [])
        if items:
            return items
    return []


def choose(items: list[dict]) -> dict | None:
    """Least cloud, then closest to the middle of the month asked for."""
    usable = []
    for item in items:
        try:
            validate_scene(item)
        except (TypeError, ValueError):
            continue
        usable.append(item)
    if not usable:
        return None
    return min(usable, key=lambda item: (item["properties"].get("eo:cloud_cover", 100.0),
                                         item["properties"].get("datetime", "")))


def visual_url(item: dict) -> str:
    return item["assets"]["visual"]["href"]


def scene_date(item: dict) -> str:
    return str(item["properties"].get("datetime", ""))[:10]
