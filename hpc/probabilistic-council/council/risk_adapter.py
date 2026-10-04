"""Turn the continuous execution-risk marginals into council forecasts.

The risk track (`execution_risk_predict.py`) returns a (3, 2, 2, 3) array of marginal
quantiles: horizon 5/15/60 seconds, side buy/sell, task terminal loss and observed adverse
excursion, quantiles 0.1/0.5/0.9, in basis points. The council fits categorical forecasts,
so this adapter converts each marginal with the declared bin edges and carries the same
provenance fields as every other specialist.

`execution_dataset.py` owns `TERMINAL_EDGES` and `ADVERSE_EDGES`. The caller passes them in,
so there is one owner for the bin geometry and the two sides cannot drift apart.

Standard library only, like the rest of `council/`.
"""
from __future__ import annotations

import math
from typing import Mapping, Sequence, Tuple

from .distributions import QuantileForecast, SpecialistForecast, to_categorical

QUANTILE_LEVELS = (0.1, 0.5, 0.9)
HORIZONS = (5, 15, 60)
SIDES = ("buy", "sell")
TASKS = ("terminal_loss", "observed_adverse")


def quantile_forecasts(prediction: object, context: str, forecast_time: str, valid_until: str,
                       information_cutoff: str, model_version: str, data_version: str,
                       horizon_suffix: str = "s") -> Tuple[QuantileForecast, ...]:
    """One quantile forecast per horizon, side and task, before bin conversion."""
    shape = (len(HORIZONS), len(SIDES), len(TASKS), len(QUANTILE_LEVELS))
    cubes = _validate_prediction(prediction, shape)
    forecasts = []
    for horizon_index, horizon in enumerate(HORIZONS):
        for side_index, side in enumerate(SIDES):
            for task_index, task in enumerate(TASKS):
                forecasts.append(QuantileForecast(
                    specialist_id=f"risk:{horizon}{horizon_suffix}:{side}:{task}",
                    levels=QUANTILE_LEVELS,
                    values=cubes[horizon_index][side_index][task_index],
                    unit="bps",
                    context=context,
                    forecast_time=forecast_time,
                    valid_until=valid_until,
                    information_cutoff=information_cutoff,
                    model_version=model_version,
                    data_version=data_version,
                ))
    return tuple(forecasts)


def risk_forecasts(prediction: object, edges_by_task: Mapping[str, Sequence[float]],
                   context: str, forecast_time: str, valid_until: str, information_cutoff: str,
                   model_version: str, data_version: str) -> Tuple[SpecialistForecast, ...]:
    """The same twelve marginals as categorical forecasts, one per horizon, side and task."""
    missing = [task for task in TASKS if task not in edges_by_task]
    if missing:
        raise ValueError("missing bin edges for: " + ", ".join(missing))
    return tuple(
        to_categorical(forecast, edges_by_task[forecast.specialist_id.rsplit(":", 1)[-1]])
        for forecast in quantile_forecasts(prediction, context, forecast_time, valid_until,
                                           information_cutoff, model_version, data_version)
    )


def _validate_prediction(prediction: object, shape: Tuple[int, ...]) -> list:
    if not isinstance(prediction, (list, tuple)) or len(prediction) != shape[0]:
        raise ValueError(f"risk prediction must have {shape[0]} horizons")
    cubes = []
    for horizon in prediction:
        if not isinstance(horizon, (list, tuple)) or len(horizon) != shape[1]:
            raise ValueError(f"each horizon needs {shape[1]} sides")
        sides = []
        for side in horizon:
            if not isinstance(side, (list, tuple)) or len(side) != shape[2]:
                raise ValueError(f"each side needs {shape[2]} tasks")
            tasks = []
            for task in side:
                if not isinstance(task, (list, tuple)) or len(task) != shape[3]:
                    raise ValueError(f"each task needs {shape[3]} quantiles")
                values = tuple(float(value) for value in task)
                if any(not math.isfinite(value) for value in values):
                    raise ValueError("risk quantiles must be finite")
                tasks.append(values)
            sides.append(tasks)
        cubes.append(sides)
    return cubes
