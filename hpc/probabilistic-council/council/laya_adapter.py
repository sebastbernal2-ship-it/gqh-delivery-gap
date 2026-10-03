"""Optional adapter from Laya's typed choice head into the council contract."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from .distributions import SpecialistForecast, validate_distribution


class LayaChoiceSpecialist:
    """Turn one Laya ``choice`` question into an ordered council distribution.

    Pass an initialized ``laya.Router``. Laya remains an optional runtime dependency;
    importing this adapter does not import or download model weights.
    """

    def __init__(self, router: Any, specialist_id: str, question_id: str,
                 instructions: str, criteria: Mapping[str, str],
                 model_version: str, data_version: str,
                 model: Optional[str] = None):
        if not criteria or any(not label or not meaning for label, meaning in criteria.items()):
            raise ValueError("criteria must map each nonempty outcome label to its meaning")
        self.router = router
        self.specialist_id = specialist_id
        self.question_id = question_id
        self.instructions = instructions
        self.criteria = dict(criteria)
        self.outcome_space = tuple(criteria.keys())
        self.model_version = model_version
        self.data_version = data_version
        self.model = model

    def forecast(self, state: Any, context: str, forecast_time: str,
                 valid_until: str, information_cutoff: str,
                 epistemic_uncertainty: Optional[float] = None) -> SpecialistForecast:
        question = {
            self.question_id: {
                "type": "choice",
                "instructions": self.instructions,
                "criteria": self.criteria,
            }
        }
        kwargs = {"model": self.model} if self.model is not None else {}
        result = self.router.predict(state, question, **kwargs)
        try:
            answer = result["answers"][self.question_id]
            raw = answer["probabilities"]
        except (KeyError, TypeError) as error:
            raise ValueError("Laya response is missing choice probabilities") from error
        if not isinstance(raw, Mapping) or set(raw) != set(self.outcome_space):
            raise ValueError("Laya probability labels differ from the declared outcome space")
        probabilities = tuple(float(raw[label]) for label in self.outcome_space)
        # Upstream examples serialize rounded decimals; only repair small rounding drift.
        validate_distribution(self.outcome_space, probabilities, tolerance=1e-3)
        total = sum(probabilities)
        if total <= 0.0:
            raise ValueError("Laya returned zero probability mass")
        probabilities = tuple(value / total for value in probabilities)
        return SpecialistForecast(
            specialist_id=self.specialist_id,
            outcome_space=self.outcome_space,
            probabilities=probabilities,
            context=context,
            forecast_time=forecast_time,
            valid_until=valid_until,
            information_cutoff=information_cutoff,
            model_version=self.model_version,
            data_version=self.data_version,
            epistemic_uncertainty=epistemic_uncertainty,
        )
