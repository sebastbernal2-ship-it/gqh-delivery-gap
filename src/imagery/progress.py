"""A crude physical progress indicator, and the control that keeps it honest.

A site is judged by two numbers: how bright and how textured a patch of ground looks, and how much those
changed between two dates. Brightness alone is confounded by season, sun angle and haze, so every site is
measured against a **background patch** in the same scene, far from the site. The reported quantity is the
site's change minus the background's change, which cancels the scene-wide part.

This is deliberately simple. It is a feasibility measure for whether imagery separates construction states at
all, not a construction detector.
"""
from __future__ import annotations

import statistics


def brightness(rows: list[bytes], samples: int = 3) -> float:
    """Mean value across the channels of a patch, 0 to 255."""
    total, count = 0, 0
    for row in rows:
        for index in range(0, len(row) - samples + 1, samples):
            total += sum(row[index:index + samples]) / samples
            count += 1
    return total / count if count else float("nan")


def texture(rows: list[bytes], samples: int = 3) -> float:
    """Mean absolute horizontal difference: a stand-in for how much structure a patch carries.

    Every adjacent pair is compared, including the last one. An earlier version stopped one pair early,
    which a test caught by returning nothing for a two pixel row.
    """
    total, count = 0, 0
    for row in rows:
        pixels = len(row) // samples
        for index in range(0, max(0, (pixels - 1)) * samples, samples):
            total += abs(row[index] - row[index + samples])
            count += 1
    return total / count if count else float("nan")


def bright_fraction(rows: list[bytes], threshold: int = 110, samples: int = 3) -> float:
    """Share of pixels brighter than a threshold, which bare graded ground tends to be."""
    bright, count = 0, 0
    for row in rows:
        for index in range(0, len(row) - samples + 1, samples):
            if sum(row[index:index + samples]) / samples > threshold:
                bright += 1
            count += 1
    return bright / count if count else float("nan")


def patch_centre(centre_lat: float, centre_lon: float, item: dict, size: int = 256) -> tuple[int, int]:
    """Pixel window around a coordinate, from the scene footprint and the item's own geometry box."""
    bbox = item["bbox"]
    width = 10980
    height = 10980
    west, south, east, north = bbox[0], bbox[1], bbox[2], bbox[3]
    if not (west <= centre_lon <= east and south <= centre_lat <= north):
        raise ValueError("the scene does not cover the site")
    x = int((centre_lon - west) / (east - west) * width) - size // 2
    y = int((north - centre_lat) / (north - south) * height) - size // 2
    return max(0, min(width - size, x)), max(0, min(height - size, y))


def difference_in_differences(site_before: float, site_after: float,
                              background_before: float, background_after: float) -> float:
    """The site's change minus the background's change, which is the number to report."""
    return (site_after - site_before) - (background_after - background_before)


def as_number(value) -> float:
    """A CSV round trip turns numbers into strings, which once compared a string to an int."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def summarise(rows: list[dict]) -> str:
    if not rows:
        return "no sites measured"
    dids = [as_number(row.get("brightness_did")) for row in rows]
    dids = [value for value in dids if value == value]
    lines = [f"sites measured: {len(rows)}",
             f"brightness change, site minus background: median {statistics.median(dids):+.1f}"
             if dids else "no usable measurements"]
    late = [row for row in rows if as_number(row.get("slip_months")) > 0]
    early = [row for row in rows if as_number(row.get("slip_months")) < 0]
    for label, group in (("late", late), ("early", early)):
        values = [as_number(row.get("brightness_did")) for row in group]
        values = [value for value in values if value == value]
        if values:
            lines.append(f"  {label} deliveries (n={len(values)}): median {statistics.median(values):+.1f}")
    lines.append("Descriptive only: a handful of sites cannot separate a measure from noise, and this is a")
    lines.append("feasibility check on whether imagery separates construction states at all.")
    return "\n".join(lines)
