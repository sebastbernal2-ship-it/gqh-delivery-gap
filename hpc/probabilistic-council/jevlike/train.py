"""Train a scorer from JSONL examples."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from torch.nn import functional as F
from torch.utils.data import DataLoader

from .data import JsonlDataset
from .model import make_system, select_device, trainable_state


def move(batch, device):
    return {name: tensor.to(device) for name, tensor in batch.items()}


@torch.no_grad()
def mean_loss(model, loader, device):
    model.eval()
    total, count = 0.0, 0
    for batch in loader:
        batch = move(batch, device)
        loss = F.cross_entropy(model(batch), batch["labels"], reduction="sum")
        total += float(loss)
        count += batch["labels"].numel()
    return total / count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("train")
    parser.add_argument("--validation", required=True)
    parser.add_argument("--output", default="runs/model.pt")
    parser.add_argument("--encoder", choices=("tiny", "hf"), default="tiny")
    parser.add_argument("--hf-model", default="Qwen/Qwen2.5-0.5B")
    parser.add_argument("--width", type=int, default=64)
    parser.add_argument("--rank", type=int, default=64)
    parser.add_argument("--context-tokens", type=int, default=192)
    parser.add_argument("--option-tokens", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=2e-3)
    parser.add_argument("--device", choices=("auto", "cpu", "mps", "cuda"), default="auto")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    torch.manual_seed(args.seed)
    device = select_device(args.device)
    config = {
        "encoder": args.encoder, "hf_model": args.hf_model,
        "width": args.width, "rank": args.rank,
        "context_tokens": args.context_tokens, "option_tokens": args.option_tokens,
    }
    model, collator = make_system(config, device)
    train_loader = DataLoader(
        JsonlDataset(args.train), batch_size=args.batch_size, shuffle=True,
        collate_fn=collator,
    )
    validation_loader = DataLoader(
        JsonlDataset(args.validation), batch_size=args.batch_size,
        collate_fn=collator,
    )
    parameters = [parameter for parameter in model.parameters() if parameter.requires_grad]
    optimiser = torch.optim.AdamW(parameters, lr=args.learning_rate, weight_decay=1e-4)
    best_loss, best_state = float("inf"), None
    for epoch in range(args.epochs):
        model.train()
        total, count = 0.0, 0
        for host_batch in train_loader:
            batch = move(host_batch, device)
            loss = F.cross_entropy(model(batch), batch["labels"])
            optimiser.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(parameters, 1.0)
            optimiser.step()
            total += float(loss.detach()) * batch["labels"].numel()
            count += batch["labels"].numel()
        validation_loss = mean_loss(model, validation_loader, device)
        if validation_loss < best_loss:
            best_loss, best_state = validation_loss, trainable_state(model)
        print(json.dumps({
            "epoch": epoch + 1, "train_nll": total / count,
            "validation_nll": validation_loss, "device": str(device),
        }))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"config": config, "state_dict": best_state}, output)
    print(json.dumps({"checkpoint": str(output), "best_validation_nll": best_loss}))


if __name__ == "__main__":
    main()
