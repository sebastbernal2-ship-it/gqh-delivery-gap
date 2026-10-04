"""OFF-CLUSTER: recover continuous risk labels from the pinned parent-case audit."""
import argparse
from bisect import bisect_right
import json
from pathlib import Path

import numpy as np

from execution_dataset import ADVERSE_EDGES, TERMINAL_EDGES, HORIZONS, FEATURES, load_cache
from multisession_panel import PARTITIONS
from synchronized_tape import LOWER_NS, UPPER_NS, digest

SCHEMA = "execution-risk-cache-v1"
FILES = ("features", "targets", "roles", "clocks")


def prepare(source_cache, output):
    source_cache, output = Path(source_cache), Path(output)
    spec, arrays = load_cache(source_cache)
    audit = source_cache / "label_audit.jsonl"
    if digest(audit) != spec["label_audit_sha256"]:
        raise ValueError("label audit hash mismatch")
    rows = [json.loads(line) for line in audit.read_text().splitlines()]
    if len(rows) != len(arrays["features"]):
        raise ValueError("audit parent count mismatch")
    sources = {item["sha256"] for item in spec["sources"]}
    targets = []
    for index, row in enumerate(rows):
        if (row["decision_ns"] != int(arrays["clocks"][index, 0])
                or row["label_available_ns"] != int(arrays["clocks"][index, 1])
                or row["role"] != int(arrays["roles"][index])
                or row["session"] != spec["sessions"][index]
                or not np.array_equal(np.asarray(row["sequence"], dtype=np.float32), arrays["features"][index])):
            raise ValueError("audit feature/clock/role alignment mismatch")
        refs = [row["history_ref"], row["current_ref"]] + [a["last_book_ref"] for a in row["audit"]]
        if any(ref.split(":", 1)[0] not in sources for ref in refs):
            raise ValueError("audit source not in pinned manifest")
        if [a["horizon"] for a in row["audit"]] != list(HORIZONS):
            raise ValueError("audit horizon mismatch")
        continuous, bins = [], []
        for item in row["audit"]:
            terminal = float(item["terminal_bps"])
            buy, sell = float(item["buy_adverse_bps"]), float(item["sell_adverse_bps"])
            continuous.append([[-terminal, buy], [terminal, sell]])
            bins.append([[bisect_right(TERMINAL_EDGES, terminal), bisect_right(ADVERSE_EDGES, buy)],
                         [bisect_right(TERMINAL_EDGES, -terminal), bisect_right(ADVERSE_EDGES, sell)]])
        if not np.array_equal(bins, arrays["targets"][index]) or row["targets"] != bins:
            raise ValueError("continuous audit does not reproduce categorical labels")
        targets.append(continuous)
    values = {name: np.asarray(arrays[name]) for name in FILES if name != "targets"}
    values["targets"] = np.asarray(targets, dtype=np.float32)
    manifest = {
        "schema_version": SCHEMA, "scope": "development_only",
        "target_id": "signed-terminal-and-observed-adverse-movement-bps-v1",
        "availability_basis": spec["availability_basis"],
        "horizons": list(HORIZONS), "sides": ["buy", "sell"],
        "tasks": ["terminal_loss", "observed_adverse"],
        "feature_order": spec["feature_order"], "partitions": spec["partitions"],
        "sessions": spec["sessions"], "source_manifest_sha256": digest(source_cache / "manifest.json"),
        "source_label_audit_sha256": digest(audit), "sources": spec["sources"],
        "adapter_sha256": digest(__file__),
        "eligible_for_performance_claim": False,
        "limitations": ["previously inspected development data; continuous labels add no independent observations",
                        "recorded availability proxy and trade completeness unverified",
                        "observed snapshot path only; no intervention, passive fills or realized execution cost"],
    }
    validate(manifest, values)
    output.mkdir(parents=True, exist_ok=False)
    for name, array in values.items():
        np.save(output / (name + ".npy"), array, allow_pickle=False)
    manifest["array_sha256"] = {name + ".npy": digest(output / (name + ".npy")) for name in FILES}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def validate(spec, arrays):
    if (spec.get("schema_version") != SCHEMA or spec.get("scope") != "development_only"
            or spec.get("target_id") != "signed-terminal-and-observed-adverse-movement-bps-v1"
            or spec.get("horizons") != list(HORIZONS) or spec.get("sides") != ["buy", "sell"]
            or spec.get("tasks") != ["terminal_loss", "observed_adverse"]
            or spec.get("feature_order") != list(FEATURES) or spec.get("partitions") != list(PARTITIONS)
            or spec.get("availability_basis") != "retrospective_assumption"
            or spec.get("eligible_for_performance_claim") is not False):
        raise ValueError("risk cache contract mismatch")
    x, y, roles, clocks = (arrays[name] for name in FILES)
    n = len(x)
    if (not n or x.shape != (n, 16, 24) or y.shape != (n, 3, 2, 2)
            or roles.shape != (n,) or clocks.shape != (n, 2) or len(spec["sessions"]) != n
            or clocks.dtype != np.int64 or roles.dtype.kind not in "iu"
            or not np.isfinite(x).all() or not np.isfinite(y).all()):
        raise ValueError("invalid risk cache arrays")
    if ((roles < 0) | (roles > 4)).any() or (np.diff(clocks[:, 0]) <= 0).any() or (clocks[:, 0] >= clocks[:, 1]).any():
        raise ValueError("invalid risk chronology")
    if (clocks[:, 0] < LOWER_NS).any() or (clocks[:, 1] >= UPPER_NS).any():
        raise ValueError("risk clocks outside development fence")
    if (not np.allclose(y[:, :, 0, 0], -y[:, :, 1, 0], atol=1e-6)
            or (y[:, :, :, 1] < 0).any() or (np.diff(y[:, :, :, 1], axis=1) < -1e-6).any()
            or (y[:, :, :, 1] + 1e-5 < y[:, :, :, 0]).any()):
        raise ValueError("risk label geometry mismatch")
    seen = set()
    for role in range(5):
        mask = roles == role
        if not mask.any():
            raise ValueError("empty risk role")
        sessions = {spec["sessions"][i] for i in np.flatnonzero(mask)}
        if sessions & seen:
            raise ValueError("risk session crosses roles")
        seen |= sessions
        if role < 4 and clocks[mask, 1].max() >= clocks[roles == role + 1, 0].min():
            raise ValueError("unmatured risk labels")


def load_risk_cache(root):
    root = Path(root)
    spec = json.loads((root / "manifest.json").read_text())
    arrays = {}
    for name in FILES:
        path = root / (name + ".npy")
        if digest(path) != spec["array_sha256"][path.name]:
            raise ValueError("risk array hash mismatch")
        arrays[name] = np.load(path, mmap_mode="r", allow_pickle=False)
    validate(spec, arrays)
    return spec, arrays


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.source_cache, args.output)
    print(json.dumps({"parents": len(result["sessions"]), "scope": result["scope"]}))
