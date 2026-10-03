"""Adapt the vendored JevLike one-pass scorer to the categorical council contract."""

from __future__ import annotations

from typing import Sequence

from .distributions import SpecialistForecast


class JevLikeChoiceSpecialist:
    """Run an initialized JevLike scorer and return its option probabilities.

    `model` and `collator` come from `jevlike.model.load_checkpoint`. PyTorch and the JevLike
    package are imported only when `forecast()` is called, so the classical council remains usable
    without the neural-model dependencies installed.
    """

    def __init__(self, model, collator, specialist_id: str,
                 model_version: str, data_version: str) -> None:
        required = (specialist_id, model_version, data_version)
        if any(not value for value in required):
            raise ValueError("JevLike identity and version metadata are required")
        self.model = model
        self.collator = collator
        self.specialist_id = specialist_id
        self.model_version = model_version
        self.data_version = data_version

    def forecast(self, decision_text: str, options: Sequence[str], context_id: str,
                 forecast_time: str, valid_until: str,
                 information_cutoff: str) -> SpecialistForecast:
        from jevlike.data import ChoiceExample
        import torch

        ordered_options = tuple(options)
        if not decision_text or not context_id:
            raise ValueError("decision text and council context are required")
        if len(ordered_options) < 2 or any(not option for option in ordered_options):
            raise ValueError("JevLike needs at least two non-empty options")
        if len(set(ordered_options)) != len(ordered_options):
            raise ValueError("JevLike options must be unique within a decision")

        batch = self.collator([ChoiceExample(decision_text, ordered_options, 0)])
        try:
            device = next(self.model.parameters()).device
        except StopIteration:
            device = torch.device("cpu")
        batch = {name: tensor.to(device) for name, tensor in batch.items()}
        was_training = self.model.training
        self.model.eval()
        try:
            with torch.no_grad():
                logits = self.model(batch)
                probabilities = logits.softmax(-1)[0, :len(ordered_options)].cpu().tolist()
        finally:
            if was_training:
                self.model.train()

        return SpecialistForecast(
            specialist_id=self.specialist_id,
            outcome_space=ordered_options,
            probabilities=tuple(float(value) for value in probabilities),
            context=context_id,
            forecast_time=forecast_time,
            valid_until=valid_until,
            information_cutoff=information_cutoff,
            model_version=self.model_version,
            data_version=self.data_version,
        )
