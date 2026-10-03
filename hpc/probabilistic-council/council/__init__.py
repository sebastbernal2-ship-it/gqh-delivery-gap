"""Composable categorical probability council."""

from .council import CouncilModel, CouncilPrediction, LabeledCase
from .distributions import CONTRACT_VERSION, SpecialistForecast, marginalize
from .fusion import linear_opinion_pool, logarithmic_opinion_pool
from .jevlike_adapter import JevLikeChoiceSpecialist

__all__ = [
    "CONTRACT_VERSION",
    "CouncilModel",
    "CouncilPrediction",
    "LabeledCase",
    "JevLikeChoiceSpecialist",
    "SpecialistForecast",
    "linear_opinion_pool",
    "logarithmic_opinion_pool",
    "marginalize",
]
