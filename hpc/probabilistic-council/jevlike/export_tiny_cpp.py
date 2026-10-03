"""Export a JevLike tiny checkpoint to the versioned C++ inference format."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

import torch


UPSTREAM_COMMIT = "94f5fd1b0b11d52bbdfdf4e0ee6aa96b568f8452"
TENSOR_ORDER = (
    "embedding.weight",
    "position.weight",
    "head.context_norm.weight",
    "head.context_norm.bias",
    "head.option_norm.weight",
    "head.option_norm.bias",
    "head.query.weight",
    "head.key.weight",
    "head.value.weight",
)
MAGIC = b"JVLKCPP1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--data-version", required=True)
    args = parser.parse_args()

    payload = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    config = payload.get("config", {})
    if config.get("encoder") != "tiny":
        raise SystemExit("C++ binary export currently supports only JevLike's tiny byte encoder")
    state = payload.get("state_dict", {})
    missing = [name for name in TENSOR_ORDER if name not in state]
    if missing:
        raise SystemExit("checkpoint is missing tensors: " + ", ".join(missing))

    width = int(config["width"])
    rank = int(config["rank"])
    context_tokens = int(config["context_tokens"])
    option_tokens = int(config["option_tokens"])
    expected_shapes = {
        "embedding.weight": (257, width),
        "position.weight": (context_tokens, width),
        "head.context_norm.weight": (width,),
        "head.context_norm.bias": (width,),
        "head.option_norm.weight": (width,),
        "head.option_norm.bias": (width,),
        "head.query.weight": (rank, width),
        "head.key.weight": (rank, width),
        "head.value.weight": (rank, width),
    }
    for name, shape in expected_shapes.items():
        if tuple(state[name].shape) != shape:
            raise SystemExit(f"unexpected tensor shape for {name}: {tuple(state[name].shape)}")
        if not torch.isfinite(state[name]).all():
            raise SystemExit(f"non-finite values in tensor {name}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("wb") as handle:
        handle.write(MAGIC)
        handle.write(struct.pack("<4I", width, rank, context_tokens, option_tokens))
        for name in TENSOR_ORDER:
            values = state[name].detach().cpu().to(torch.float32).contiguous().numpy().astype("<f4", copy=False)
            handle.write(values.tobytes(order="C"))

    manifest = {
        "format": "jevlike-tiny-cpp-v1",
        "upstream_repository": "https://github.com/vinnylarouge/jevlike",
        "upstream_commit": UPSTREAM_COMMIT,
        "encoder": "tiny-byte-encoder",
        "checkpoint_sha256": sha256(args.checkpoint),
        "weights_sha256": sha256(args.output),
        "data_version": args.data_version,
        "config": {name: config[name] for name in (
            "encoder", "width", "rank", "context_tokens", "option_tokens"
        )},
        "tensor_order": list(TENSOR_ORDER),
        "byte_tokenization": "utf8 bytes + 1; 0 is padding; truncate to configured byte count",
        "source_probability": "softmax of JevLike option logits",
        "calibration": "none; fit separately before council use",
    }
    manifest_path = args.output.with_suffix(args.output.suffix + ".json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"weights": str(args.output), "manifest": str(manifest_path),
                      "weights_sha256": manifest["weights_sha256"]}))


if __name__ == "__main__":
    main()
