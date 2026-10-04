"""Experimental Jev-like scorer for market state conditioned on a proposed order.

This module defines the model contract only. The current execution cache has no
action-conditioned executable-cost labels and must not be used to train it.
"""

import torch
from torch import nn
import torch.nn.functional as F


ACTION_FEATURES = (
    "side_buy",
    "side_sell",
    "order_marketable",
    "order_passive",
    "log_size_over_top5_depth",
    "aggressiveness_bps_scaled",
    "urgency_0_to_1",
    "log_horizon_seconds_scaled",
)
QUANTILES = (0.1, 0.5, 0.9)


class ActionConditionedExecutionJev(nn.Module):
    """Estimate cost quantiles for each proposed order against one market state.

    ``state`` is the existing 16-step by 24-feature numeric sequence. ``action``
    is either ``[batch, action_features]`` or a candidate set shaped
    ``[batch, candidates, action_features]`` and ordered as ``ACTION_FEATURES``.
    Candidate actions share one state encoding. The scalar target contract is
    chosen by the training dataset; this model does not create execution labels.
    """

    def __init__(self, features=24, steps=16, action_features=len(ACTION_FEATURES), width=32):
        super().__init__()
        if features < 1 or steps < 1 or action_features != len(ACTION_FEATURES) or width < 4 or width % 4:
            raise ValueError("invalid action-conditioned model dimensions")
        self.config = dict(
            features=features,
            steps=steps,
            action_features=action_features,
            width=width,
            quantiles=list(QUANTILES),
        )
        self.project = nn.Linear(features, width)
        self.position = nn.Parameter(torch.zeros(steps, width))
        layer = nn.TransformerEncoderLayer(
            width, 4, 2 * width, dropout=0.0, batch_first=True
        )
        self.encoder = nn.TransformerEncoder(layer, 1, enable_nested_tensor=False)
        self.action = nn.Sequential(
            nn.Linear(action_features, width),
            nn.GELU(),
            nn.Linear(width, width),
        )
        self.fusion = nn.Sequential(
            nn.LayerNorm(2 * width),
            nn.Linear(2 * width, width),
            nn.GELU(),
            nn.Linear(width, 3),
        )

    def forward(self, state, action):
        if state.ndim != 3 or tuple(state.shape[1:]) != (self.config["steps"], self.config["features"]):
            raise ValueError("state must have shape [batch, steps, features]")
        single_action = action.ndim == 2
        if single_action:
            valid_action_shape = tuple(action.shape) == (state.shape[0], self.config["action_features"])
        else:
            valid_action_shape = (
                action.ndim == 3
                and action.shape[0] == state.shape[0]
                and action.shape[2] == self.config["action_features"]
                and action.shape[1] > 0
            )
        if not valid_action_shape:
            raise ValueError("action must have shape [batch, action_features] or [batch, candidates, action_features]")
        if not torch.isfinite(state).all() or not torch.isfinite(action).all():
            raise ValueError("state and action must be finite")

        market = self.encoder(self.project(state) + self.position).select(1, -1)
        proposed_order = self.action(action)
        if single_action:
            fused = torch.cat((market, proposed_order), dim=-1)
        else:
            market = market.unsqueeze(1).expand(-1, action.shape[1], -1)
            fused = torch.cat((market, proposed_order), dim=-1)
        raw = self.fusion(fused)
        # Parameterize quantiles in increasing order, avoiding crossing by design.
        lower = raw[..., 0]
        median = lower + F.softplus(raw[..., 1])
        upper = median + F.softplus(raw[..., 2])
        return torch.stack((lower, median, upper), dim=-1)


def pinball_loss(prediction, target, quantiles=QUANTILES):
    """Mean quantile-regression loss for one scalar outcome per example."""
    if prediction.ndim < 2 or prediction.shape[-1] != len(quantiles):
        raise ValueError("prediction must end in number_of_quantiles")
    if tuple(target.shape) != tuple(prediction.shape[:-1]) or not target.numel():
        raise ValueError("target must match prediction without its quantile axis")
    if not torch.isfinite(prediction).all() or not torch.isfinite(target).all():
        raise ValueError("prediction and target must be finite")
    q = torch.as_tensor(quantiles, dtype=prediction.dtype, device=prediction.device)
    if q.ndim != 1 or len(q) != prediction.shape[-1] or not ((q > 0) & (q < 1)).all() or not (q[1:] > q[:-1]).all():
        raise ValueError("quantiles must be a vector in (0, 1) matching prediction width")
    error = target.unsqueeze(-1) - prediction
    return torch.maximum(q * error, (q - 1) * error).mean()
