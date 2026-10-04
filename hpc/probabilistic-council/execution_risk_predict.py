"""Hash-pinned risk inference once per state, then analytical order-cost overlays."""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

from execution_action_model import QUANTILES
from execution_dataset import FEATURES
from execution_risk_cost import MarketableOrder, compose_order, validate_sequence_book
from execution_risk_model import ExecutionRiskJev
from execution_risk_train import VIEWS, view_tensor
from synchronized_tape import Book, digest


class ExecutionRiskPredictor:
    def __init__(self, checkpoint, sha256, device="cpu"):
        if digest(checkpoint) != sha256:
            raise ValueError("risk checkpoint hash mismatch")
        self.device = torch.device(device)
        payload = torch.load(checkpoint, map_location="cpu", weights_only=True)
        if (payload["schema_version"] != "execution-risk-jev-v1"
                or payload["scope"] != "development_only" or payload["calibrated"] is not False
                or payload["quantiles"] != list(QUANTILES) or payload["feature_order"] != list(FEATURES)):
            raise ValueError("risk checkpoint contract mismatch")
        self.variant = payload["variant"]
        self.mean, self.scale = np.asarray(payload["mean"]), np.asarray(payload["scale"])
        self.target_scale = float(payload["target_scale"])
        if (self.mean.shape != (24,) or self.scale.shape != (24,)
                or not np.isfinite(self.mean).all() or not np.isfinite(self.scale).all()
                or (self.scale <= 0).any() or not np.isfinite(self.target_scale) or self.target_scale <= 0):
            raise ValueError("invalid saved risk normalizer")
        if self.variant == "empirical_quantiles":
            self.model = None
            self.prior = np.asarray(payload["prior_quantiles"])
            if self.prior.shape != (3, 2, 2, 3) or not np.isfinite(self.prior).all():
                raise ValueError("invalid empirical risk quantiles")
        elif self.variant in VIEWS:
            self.model = ExecutionRiskJev(**payload["config"]).to(self.device).eval()
            self.model.load_state_dict(payload["state"], strict=True)
        else:
            raise ValueError("unknown risk variant")

    def risk(self, sequence):
        raw = np.asarray(sequence, dtype=float)
        if raw.shape != (16, 24) or not np.isfinite(raw).all():
            raise ValueError("finite raw 16x24 risk sequence required")
        if self.model is None:
            return self.prior.copy()
        x = torch.tensor(((raw - self.mean) / self.scale)[None], dtype=torch.float32, device=self.device)
        if not torch.isfinite(x).all():
            raise ValueError("nonfinite standardized risk input")
        with torch.no_grad():
            result = self.model(view_tensor(x, self.variant))[0].double().cpu().numpy() * self.target_scale
        if not np.isfinite(result).all():
            raise ValueError("nonfinite risk output")
        return result

    def predict(self, sequence, book, decision_ns, orders):
        validate_sequence_book(sequence, book, decision_ns)
        if not orders:
            raise ValueError("at least one proposed marketable order required")
        risk = self.risk(sequence)
        candidates = []
        for proposed in orders:
            if proposed.get("order_type", "marketable") != "marketable":
                raise ValueError("passive order risk needs a validated fill/queue model")
            order = MarketableOrder(proposed["side"], proposed["size"], proposed["horizon_seconds"], proposed["taker_fee_bps"])
            candidates.append(compose_order(risk, book, order, decision_ns))
        return {"scope": "development_only", "variant": self.variant, "calibrated": False,
                "forecast_state_count": 1, "risk_quantiles_bps": risk.tolist(), "orders": candidates,
                "limitations": ["hypothetical price-taking orders; snapshot cost is not a verified fill",
                                "no completed-order implementation shortfall, round-trip P&L or HFT latency claim",
                                "three marginal quantiles, no identified full or joint distribution"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--request", type=Path, required=True)
    args = parser.parse_args()
    request = json.loads(args.request.read_text())
    b = request["book"]
    book = Book(b["event_ns"], b["recorded_ns"], tuple(map(tuple, b["bids"])), tuple(map(tuple, b["asks"])), b["source_ref"])
    predictor = ExecutionRiskPredictor(args.checkpoint, args.sha256)
    print(json.dumps(predictor.predict(request["sequence"], book, request["decision_ns"], request["orders"]), indent=2))
