#!/usr/bin/env python3
"""Offline tests for the COG reader and the progress indicators. No network, no imagery."""
from __future__ import annotations

import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from imagery.cog import (  # noqa: E402
    Tiff, undo_horizontal_predictor,
)
from imagery.progress import (  # noqa: E402
    as_number, bright_fraction, brightness, difference_in_differences, patch_centre, summarise, texture,
)
from imagery.stac import choose, month_window, scene_date, visual_url  # noqa: E402

failures: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        failures.append(f"{name}: got {got!r}, want {want!r}")


def close(name: str, got, want, tol=1e-6) -> None:
    if not (abs(got - want) <= tol):
        failures.append(f"{name}: got {got!r}, want about {want!r}")


# Predictor 2 stores each component as the difference from the previous pixel's component.
raw = bytes([10, 20, 30, 5, 5, 5, 1, 2, 3])
restored = undo_horizontal_predictor(raw, width=3, samples=3)
check("the first pixel of a row is absolute", tuple(restored[:3]), (10, 20, 30))
check("later pixels accumulate", tuple(restored[3:6]), (15, 25, 35))
check("the wrap is modulo 256", tuple(restored[6:9]), (16, 27, 38))
check("a second row starts absolute again",
      tuple(undo_horizontal_predictor(bytes([9, 9, 9, 1, 1, 1]), width=2, samples=3)), (9, 9, 9, 10, 10, 10))

# Indicators on synthetic patches.
patch = [bytes([10, 10, 10, 20, 20, 20, 40, 40, 40]), bytes([30, 30, 30, 40, 40, 40, 50, 50, 50])]
# Six pixels: 10, 20, 40 in one row and 30, 40, 50 in the other, so the mean is 31.67.
close("brightness is the mean across samples", brightness(patch), 31.666666, 1e-4)
# Row one steps 10 then 20, row two steps 10 then 10: the mean of those four steps is 12.5.
close("texture is the mean absolute step", texture(patch), 12.5, 1e-6)
close("texture still compares a two pixel row", texture([bytes([0, 0, 0, 30, 30, 30])]), 30.0, 1e-6)
close("bright fraction counts pixels above the threshold", bright_fraction([bytes([200] * 3 + [10] * 3)], threshold=110), 0.5)
check("brightness of nothing is not a number", brightness([]) != brightness([]), True)
close("difference in differences removes the shared move",
      difference_in_differences(100, 120, 50, 60), 10.0)

# A window is placed from the scene box, and clamped inside the raster.
item = {"bbox": [-100.0, 30.0, -99.0, 31.0]}
x, y = patch_centre(30.5, -99.5, item, size=200)
check("the centre of the box maps to the centre of the raster", (x, y), (5390, 5390))
x, y = patch_centre(31.0, -100.0, item, size=200)
check("a corner is clamped inside the raster", (x, y), (0, 0))

# Scene choice prefers the least cloud and skips items whose asset is not reachable over HTTPS.
cloudy = {"id": "cloudy", "properties": {"eo:cloud_cover": 40.0, "datetime": "2021-01-01T00:00:00Z"},
          "assets": {"visual": {"href": "https://example.invalid/a.tif"}}}
clear = {"id": "clear", "properties": {"eo:cloud_cover": 3.0, "datetime": "2021-01-02T00:00:00Z"},
         "assets": {"visual": {"href": "https://example.invalid/b.tif"}}}
s3_only = {"id": "s3", "properties": {"eo:cloud_cover": 1.0, "datetime": "2021-01-03T00:00:00Z"},
           "assets": {"visual": {"href": "s3://bucket/c.tif"}}}
check("the least cloudy reachable scene is chosen", choose([cloudy, clear, s3_only])["id"], "clear")
check("a scene with no reachable asset is refused", choose([s3_only]), None)
check("no scenes means no choice", choose([]), None)
check("the scene date is read from the item", scene_date(clear), "2021-01-02")
check("the visual url is read from the asset", visual_url(clear), "https://example.invalid/b.tif")

start, end = month_window("2021-06")
check("the month window starts before the month", start, "2021-05-01")
check("the month window ends after it", end, "2021-07-31")
check("a window can ask for just the month", month_window("2021-06", before=0, after=0),
      ("2021-06-01", "2021-06-30"))
check("a window spanning a year end is handled", month_window("2021-01", before=1, after=1),
      ("2020-12-01", "2021-02-28"))

check("a csv string becomes a number", as_number("12.5"), 12.5)
check("an unparseable value becomes not a number", as_number("n/a") != as_number("n/a"), True)
text = summarise([{"brightness_did": "5.0", "slip_months": "10"}, {"brightness_did": "-1.0", "slip_months": "-3"}])
check("the summary groups by delivery direction", "late deliveries" in text and "early deliveries" in text, True)
check("the summary refuses to call it evidence", "cannot separate a measure from noise" in text, True)
check("an empty summary is stated", summarise([]), "no sites measured")

if failures:
    print("\n".join(f"  FAIL {f}" for f in failures))
    print(f"\n{26 - len(failures)}/26 passed")
    raise SystemExit(1)
print("\n26/26 passed")
