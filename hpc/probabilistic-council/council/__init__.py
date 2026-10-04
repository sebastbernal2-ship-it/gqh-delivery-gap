"""Composable categorical probability council."""

from .council import CouncilModel, CouncilPrediction, LabeledCase
from .distributions import (CONTRACT_VERSION, QuantileForecast, SpecialistForecast, bin_labels,
                            from_categorical, marginalize, probabilities_to_quantiles,
                            quantiles_to_probabilities, to_categorical)
from .fusion import linear_opinion_pool, logarithmic_opinion_pool
from .jevlike_adapter import JevLikeChoiceSpecialist

__all__ = [
    "CONTRACT_VERSION",
    "CouncilModel",
    "CouncilPrediction",
    "LabeledCase",
    "JevLikeChoiceSpecialist",
    "QuantileForecast",
    "SpecialistForecast",
    "bin_labels",
    "from_categorical",
    "linear_opinion_pool",
    "logarithmic_opinion_pool",
    "marginalize",
    "probabilities_to_quantiles",
    "quantiles_to_probabilities",
    "to_categorical",
]
