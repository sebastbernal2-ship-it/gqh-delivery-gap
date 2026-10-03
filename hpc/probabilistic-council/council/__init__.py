"""Composable categorical probability council."""

from .council import CouncilModel, CouncilPrediction, LabeledCase
from .distributions import CONTRACT_VERSION, SpecialistForecast, marginalize
from .fusion import linear_opinion_pool, logarithmic_opinion_pool
from .laya_adapter import LayaChoiceSpecialist

__all__ = [
    "CONTRACT_VERSION",
    "CouncilModel",
    "CouncilPrediction",
    "LabeledCase",
    "LayaChoiceSpecialist",
    "SpecialistForecast",
    "linear_opinion_pool",
    "logarithmic_opinion_pool",
    "marginalize",
]
