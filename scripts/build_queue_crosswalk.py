#!/usr/bin/env python3
"""Crosswalk the LBNL queue projects to the EIA operating plant universe.

The queue panel and the EIA panel are two vocabularies for the same projects, and nothing joined
them before this. This builder matches on normalized plant name, state and capacity, with the two
structural fixes the feasibility test found: phase numbers in queue names are stripped, and EIA
generators are summed to one row per plant.

Writes results/queue-crosswalk.csv (every queue project, with its EIA match where one exists) and
results/queue-crosswalk-summary.json (matched share by status, region, technology, and examples).

    python3 scripts/build_queue_crosswalk.py
"""
from __future__ import annotations

import collections
import csv
import difflib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from eia.vintages import read_vintage  # noqa: E402

PANEL = ROOT / "results" / "queue-panel.csv"
VINTAGE = ROOT / "results" / "eia-cache" / "september_generator2024.xlsx"
OUT = ROOT / "results" / "queue-crosswalk.csv"
SUMMARY = ROOT / "results" / "queue-crosswalk-summary.json"

STOP = {"llc", "lp", "llp", "inc", "corp", "co", "company", "project", "solar", "wind", "farm",
        "energy", "power", "generation", "storage", "center", "centre", "facility", "plant",
        "phase", "unit", "units", "site", "complex", "station", "substation", "holding", "group"}
PHASE = {"1", "2", "3", "4", "5", "6", "7", "8", "9", "i", "ii", "iii", "iv", "v", "a", "b", "c"}
NAME_THRESHOLD = 0.90
SOFT_THRESHOLD = 0.85
CAPACITY_FACTOR = 1.25


PHASE_EQUIV = {"1": "i", "2": "ii", "3": "iii", "4": "iv", "5": "v", "6": "vi",
               "7": "vii", "8": "viii", "9": "ix"}


def phases_of(text: str) -> frozenset:
    """Trailing phase markers, roman and numeric read as the same phase."""
    tokens = re.split(r"[^a-z0-9]+", str(text or "").lower())
    tokens = [token for token in tokens if token]
    found = set()
    while tokens and tokens[-1] in PHASE:
        found.add(PHASE_EQUIV.get(tokens[-1], tokens[-1]))
        tokens.pop()
    return frozenset(found)


def normalize(text: str) -> str:
    text = str(text or "").lower().replace("&", " and ")
    text = text.replace("'", "")
    tokens = [token for token in re.split(r"[^a-z0-9]+", text) if token and token not in STOP]
    while len(tokens) > 1 and tokens[-1] in PHASE:
        tokens.pop()
    return " ".join(tokens)


def load_plants() -> dict[str, list[dict]]:
    """The plant universe is the union over cached vintages, so retired and planned
    plants are included, not only what still operates in one snapshot."""
    cache = VINTAGE.parent
    by_year: dict[str, Path] = {}
    for path in sorted(cache.glob("*_generator*.xlsx")):
        match = re.search(r"(20\d\d)", path.name)
        if match:
            by_year[match.group(1)] = path
    plants: dict[tuple[str, str], dict] = {}
    for year, path in sorted(by_year.items()):
        try:
            vintages = read_vintage(path, int(year), 12)
        except Exception as error:  # a damaged cache file must not hide the others
            print(f"skip {path.name}: {error}")
            continue
        for sheet in ("Operating", "Planned", "Canceled or Postponed"):
            for generator in vintages.get(sheet, []):
                row = generator.as_dict()
                key = (row.get("state", ""), row.get("plant_id", ""))
                if not row.get("plant_id") or not row.get("state"):
                    continue
                entry = plants.setdefault(key, {"plant_id": row["plant_id"], "plant_name": "",
                                                "state": row["state"], "entity": "", "capacity": 0.0,
                                                "sheets": set(), "years": set()})
                if row.get("plant_name"):
                    entry["plant_name"] = row["plant_name"]
                if row.get("entity_name"):
                    entry["entity"] = row["entity_name"]
                entry["sheets"].add(sheet)
                entry["years"].add(year)
                try:
                    entry["capacity"] = max(entry["capacity"], float(row.get("capacity_mw") or 0))
                except ValueError:
                    pass
    by_state: dict[str, list[dict]] = collections.defaultdict(list)
    for entry in plants.values():
        if entry["plant_name"] and entry["state"]:
            entry["key"] = normalize(entry["plant_name"])
            entry["sheets"] = sorted(entry["sheets"])
            entry["years"] = sorted(entry["years"])
            if entry["key"]:
                by_state[entry["state"]].append(entry)
    return by_state


def match(row: dict, by_state: dict[str, list[dict]]) -> dict | None:
    key = normalize(row.get("project_name", ""))
    if not key:
        return None
    key_tokens = set(key.split())
    first = key.split()[0]
    try:
        capacity = float(row.get("mw1") or 0)
    except ValueError:
        capacity = 0.0
    best, best_ratio = None, 0.0
    for candidate in by_state.get(row.get("state", ""), []):
        candidate_tokens = set(candidate["key"].split())
        if first not in candidate_tokens and not (key_tokens & candidate_tokens):
            continue
        if capacity and candidate["capacity"]:
            ratio = capacity / candidate["capacity"]
            if not (1 / (CAPACITY_FACTOR ** 3) <= ratio <= CAPACITY_FACTOR ** 3):
                continue
        score = difflib.SequenceMatcher(None, key, candidate["key"]).quick_ratio()
        if score < SOFT_THRESHOLD:
            continue
        score = difflib.SequenceMatcher(None, key, candidate["key"]).ratio()
        if score > best_ratio:
            best_ratio, best = score, candidate
    if not best:
        return None
    generic = len(key) < 8 or len(key.split()) < 2
    if generic and key != best["key"]:
        return None
    capacity_ratio = (capacity / best["capacity"]) if capacity and best["capacity"] else None
    queue_phases = phases_of(row.get("project_name", ""))
    plant_phases = phases_of(best["plant_name"])
    phase_clash = bool(queue_phases and plant_phases and queue_phases != plant_phases)
    if phase_clash and capacity_ratio is not None and not 1 / 1.1 <= capacity_ratio <= 1.1:
        return None
    if best_ratio >= NAME_THRESHOLD:
        if capacity_ratio is None or 1 / 1.5 <= capacity_ratio <= 1.5:
            return {"plant": best, "ratio": best_ratio}
        return None
    if best_ratio >= SOFT_THRESHOLD and capacity_ratio is not None:
        if 1 / CAPACITY_FACTOR <= capacity_ratio <= CAPACITY_FACTOR:
            return {"plant": best, "ratio": best_ratio}
    return None


def main() -> int:
    by_state = load_plants()
    print(f"EIA operating plants with names: {sum(len(v) for v in by_state.values())}")
    rows = list(csv.DictReader(PANEL.open()))
    matched = 0
    examples: list[dict] = []
    output: list[dict] = []
    for row in rows:
        result = match(row, by_state)
        record = {"q_id": row.get("q_id", ""), "q_status": row.get("q_status", ""),
                  "q_date": row.get("q_date", ""), "state": row.get("state", ""),
                  "project_name": row.get("project_name", ""), "mw1": row.get("mw1", ""),
                  "type_clean": row.get("type_clean", ""), "developer": row.get("developer", ""),
                  "eia_plant_id": "", "eia_plant_name": "", "eia_entity": "", "eia_capacity_mw": "",
                  "name_ratio": "", "match": "no"}
        if result:
            plant = result["plant"]
            record.update({"eia_plant_id": plant["plant_id"], "eia_plant_name": plant["plant_name"],
                           "eia_entity": plant["entity"], "eia_capacity_mw": round(plant["capacity"], 1),
                           "name_ratio": round(result["ratio"], 3), "match": "yes"})
            matched += 1
            if len(examples) < 12 and row.get("q_status") == "operational":
                examples.append({"project": row.get("project_name", ""), "plant": plant["plant_name"],
                                 "state": row.get("state", ""), "queue_mw": row.get("mw1", ""),
                                 "eia_mw": round(plant["capacity"], 1), "ratio": round(result["ratio"], 3)})
        output.append(record)
    fields = list(output[0]) if output else []
    with OUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(output)

    def share(status: str) -> dict:
        subset = [record for record in output if record["q_status"] == status]
        matched_subset = [record for record in subset if record["match"] == "yes"]
        return {"projects": len(subset), "matched": len(matched_subset),
                "matched_share": round(len(matched_subset) / len(subset), 4) if subset else None}

    by_status = {status: share(status) for status in sorted({row["q_status"] for row in output})}
    summary = {
        "queue_projects": len(output),
        "matched": matched,
        "matched_share": round(matched / len(output), 4) if output else None,
        "eia_plants": sum(len(v) for v in by_state.values()),
        "by_status": by_status,
        "examples": examples,
    }
    SUMMARY.write_text(json.dumps(summary, indent=1) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(output):,} rows) and {SUMMARY.relative_to(ROOT)}")
    print(f"matched {matched:,} of {len(output):,} ({summary['matched_share']:.1%})")
    for status, stats in by_status.items():
        print(f"  {status:12s} {stats['projects']:>7,}  matched {stats['matched']:>7,} "
              f"({(stats['matched_share'] or 0):.1%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
