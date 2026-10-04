"""Jev-like shared state model for uncertain movement; known costs stay analytic."""
import torch
from torch import nn
from torch.nn import functional as F

from execution_model import ExecutionJev


class ExecutionRiskJev(ExecutionJev):
    """12 marginal risk queries, each with ordered q10/q50/q90 estimates in bps.

    Terminal buy/sell losses are derived from one midpoint-return forecast.
    Observed adverse excursions are nonnegative and monotone with horizon.
    Neither these constraints nor three quantiles identify a joint distribution.
    """

    def __init__(self, features=24, steps=16, width=32):
        super().__init__(features, steps, width)
        # Three horizons x (midpoint return, buy excursion, sell excursion) x 3.
        self.options = nn.Parameter(torch.randn(27, width) * 0.02)

    def forward(self, x):
        encoded = self.encode(x)
        scores = self.head(
            encoded,
            torch.ones(x.shape[:2], dtype=torch.bool, device=x.device),
            self.options.unsqueeze(0).expand(len(x), -1, -1),
            torch.ones((len(x), 27), dtype=torch.bool, device=x.device),
        ).reshape(len(x), 3, 3, 3)
        first = scores[..., :1]
        ordered = torch.cat((first, first + torch.cumsum(F.softplus(scores[..., 1:]), -1)), -1)
        returns = ordered[:, :, 0]
        # Q_tau(-R) = -Q_(1-tau)(R); quantile levels are reflection-symmetric.
        terminal = torch.stack((-returns.flip(-1), returns), dim=2)
        adverse = torch.cat(
            (F.softplus(first[:, :, 1:]),
             F.softplus(first[:, :, 1:]) + torch.cumsum(F.softplus(scores[:, :, 1:, 1:]), -1)),
            dim=-1,
        )
        # Pathwise worst loss includes the terminal observation. Its marginal
        # quantiles therefore dominate terminal loss at the same quantile level.
        adverse = torch.cummax(torch.maximum(adverse, terminal), dim=1).values
        return torch.stack((terminal, adverse), dim=3)
