#!/usr/bin/env python3
"""Do public satellite images separate a late delivery from an on-time one?

A feasibility probe with eight labelled sites, not a study. Each site has a promised month and a realised
month taken from the vintage panel, plus its coordinates from the same source. For each date the probe reads a
patch of the scene's visual asset and a background patch, and reports the site's change minus the background's
change, which cancels the scene-wide part of the difference.

The falsifier is declared: if the difference in differences does not separate late from early deliveries
better than noise on eight sites, then this measure at ten metre resolution is not the instrument, and the
next step would be metre-scale imagery, which is not openly reachable from here.

Usage:
    python scripts/imagery_probe.py --sites 8
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from imagery.cog import RangeReader, Tiff  # noqa: E402
from imagery.progress import (  # noqa: E402
    bright_fraction, brightness, difference_in_differences, patch_centre, summarise, texture,
)
from imagery.validation import validate_label, validate_probe_row  # noqa: E402
from imagery.stac import choose, scene_date, search, visual_url  # noqa: E402

FIELDS = ["plant_id", "plant_name", "state", "capacity_mw", "slip_months", "promised", "realized",
          "promise_scene", "promise_cloud", "realized_scene", "realized_cloud",
          "promise_brightness", "realized_brightness", "background_promise_brightness",
          "background_realized_brightness", "brightness_did", "promise_texture", "realized_texture",
          "texture_change", "promise_bright_fraction", "realized_bright_fraction"]


def measure(lat: float, lon: float, month: str, size: int = 192) -> dict | None:
    items = search(lat, lon, month)
    item = choose(items)
    if item is None:
        return None
    try:
        tiff = Tiff(RangeReader(visual_url(item)))
        tiff.check_supported()
        x, y = patch_centre(lat, lon, item, size=size)
        site = tiff.read_window(x, y, size, size)
        # The control patch must sit on valid ground, so it is taken from the same scene at a fixed offset
        # and rejected if it looks like nodata. A corner patch was black in one scene and produced a change
        # of two hundred and twenty brightness units, which is how this was found.
        background = None
        for shift in (("x", 400), ("x", -400), ("y", 400), ("y", -400)):
            direction, amount = shift
            try:
                if direction == "x":
                    patch = tiff.read_window(max(0, min(tiff.width - size, x + amount)), y, size, size)
                else:
                    patch = tiff.read_window(x, max(0, min(tiff.height - size, y + amount)), size, size)
            except Exception:
                continue
            if brightness(patch) > 5:
                background = patch
                break
        if background is None:
            print(f"    no valid control patch in this scene")
            return None
    except Exception as exc:
        print(f"    read failed for {month}: {type(exc).__name__} {str(exc)[:60]}")
        return None
    return {"scene": item["id"], "date": scene_date(item),
            "cloud": item["properties"].get("eo:cloud_cover"),
            "brightness": brightness(site), "texture": texture(site),
            "bright_fraction": bright_fraction(site),
            "background_brightness": brightness(background), "background_texture": texture(background)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", default="results/site-labels.csv")
    parser.add_argument("--sites", type=int, default=8)
    parser.add_argument("--out", default="results/imagery-probe.csv")
    args = parser.parse_args(argv)

    labels = list(csv.DictReader((ROOT / args.labels).open()))[:args.sites]
    if not labels:
        print("no labelled sites")
        return 1

    rows = []
    for site in labels:
        try:
            validate_label(site)
        except ValueError as exc:
            print(f"{site.get('plant_id', '?')}: invalid label ({exc})")
            continue
        lat, lon = float(site["latitude"]), float(site["longitude"])
        print(f"{site['plant_name'][:34]}  promised {site['promised']} realized {site['realized']} "
              f"({int(site['slip_months']):+d} months)")
        before = measure(lat, lon, site["promised"])
        after = measure(lat, lon, site["realized"])
        if before is None or after is None:
            print("    skipped: no usable scene pair")
            continue
        row = {**{k: site[k] for k in ("plant_id", "plant_name", "state", "capacity_mw", "slip_months",
                                       "promised", "realized")},
               "promise_scene": before["scene"], "promise_cloud": before["cloud"],
               "realized_scene": after["scene"], "realized_cloud": after["cloud"],
               "promise_brightness": round(before["brightness"], 1),
               "realized_brightness": round(after["brightness"], 1),
               "background_promise_brightness": round(before["background_brightness"], 1),
               "background_realized_brightness": round(after["background_brightness"], 1),
               "brightness_did": round(difference_in_differences(
                   before["brightness"], after["brightness"],
                   before["background_brightness"], after["background_brightness"]), 1),
               "promise_texture": round(before["texture"], 2),
               "realized_texture": round(after["texture"], 2),
               "texture_change": round(after["texture"] - before["texture"], 2),
               "promise_bright_fraction": round(before["bright_fraction"], 3),
               "realized_bright_fraction": round(after["bright_fraction"], 3)}
        try:
            validate_probe_row(row)
        except ValueError as exc:
            print(f"    invalid probe row: {exc}")
            continue
        rows.append(row)
        print(f"    {before['date']} -> {after['date']}  brightness "
              f"{before['brightness']:.1f} -> {after['brightness']:.1f}  "
              f"difference in differences {row['brightness_did']:+.1f}")

    if rows:
        out = ROOT / args.out
        with out.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        print(f"wrote {args.out} ({len(rows)} sites)")
    print("")
    print(summarise(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
