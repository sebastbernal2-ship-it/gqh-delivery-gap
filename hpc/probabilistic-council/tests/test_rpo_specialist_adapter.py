"""Contracts for the RPO council specialist: distribution, windows, abstention, composition."""
from __future__ import annotations

import datetime
from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from council.council import CouncilModel, LabeledCase  # noqa: E402
from council.distributions import assert_compatible  # noqa: E402
from filing_specialist.model import chronological_split  # noqa: E402
from filing_specialist.rpo_model import FEATURES, prepare_rows  # noqa: E402
from rpo_specialist import disclosure_window, fit_rpo_specialist  # noqa: E402


def vintage(ticker: str, period_end: str, relative: str, availability: str) -> dict:
    return {"ticker": ticker, "period_end": period_end, "relative_surprise_pit": relative,
            "expectation_status": "measured", "availability": availability, "change": "10",
            "previous_value": "100", "history_count": "2", "history_span_days": "365",
            "group": "datacenter", "in_sealed_window": "False"}


def rows(count: int = 30) -> list[dict]:
    out = []
    for index in range(count):
        relative = ((index % 7) - 3) / 20.0
        out.append(vintage("T", f"20{20 + index // 4}-{(index % 4) * 3 + 3:02d}-30",
                           f"{relative:.4f}",
                           f"20{21 + index // 4}-01-{index % 27 + 1:02d}T12:00:00+00:00"))
    prepared, _ = prepare_rows(out)
    return prepared


class RpoSpecialistAdapterTests(unittest.TestCase):
    def test_forecast_holds_the_distribution_and_the_clock(self):
        prepared = rows()
        fitted = fit_rpo_specialist(prepared[:20], FEATURES, "rpo-v1", "vintages-v1", steps=50)
        row = prepared[-1]
        cutoff, forecast_time, valid_until = disclosure_window(row, prepared[-2]["label_available"])
        forecast = fitted.forecast(row, "ABLZF:2024-12-31", cutoff, forecast_time, valid_until)
        self.assertEqual(len(forecast.probabilities), 5)
        self.assertAlmostEqual(sum(forecast.probabilities), 1.0, places=9)
        self.assertEqual(forecast.outcome_space, (
            "surprise-down-large", "surprise-down-small", "flat",
            "surprise-up-small", "surprise-up-large"))
        self.assertLessEqual(forecast.information_cutoff, forecast.forecast_time)
        self.assertLess(forecast.forecast_time, forecast.valid_until)
        assert_compatible((forecast,))
        self.assertFalse(forecast.abstain)

    def test_a_disclosure_without_history_abstains(self):
        prepared = rows()
        first = prepared[0]
        self.assertEqual(first["missing_prior"], 1.0)
        fitted = fit_rpo_specialist(prepared[:20], FEATURES, "rpo-v1", "vintages-v1", steps=50)
        cutoff, forecast_time, valid_until = disclosure_window(first, None)
        forecast = fitted.forecast(first, "first", cutoff, forecast_time, valid_until)
        self.assertTrue(forecast.abstain)
        self.assertAlmostEqual(sum(forecast.probabilities), 1.0, places=9)

    def test_the_council_fuses_the_specialist_with_a_second_opinion(self):
        prepared = rows(60)
        train, _ = chronological_split(prepared, 0.6)
        fitted = fit_rpo_specialist(train, FEATURES, "rpo-v1", "vintages-v1", steps=50)
        cases = {role: [] for role in ("calibration", "gate", "pool")}
        partition = {"calibration": train[:10], "gate": train[10:20], "pool": train[20:30]}
        for name, chunk in partition.items():
            for index, row in enumerate(chunk):
                cutoff, forecast_time, valid_until = disclosure_window(
                    row, chunk[index - 1]["label_available"] if index else None)
                primary = fitted.forecast(row, f"{name}-{index}", cutoff, forecast_time, valid_until)
                secondary = replace(primary, specialist_id="rpo-surprise:second-opinion")
                cases[name].append(LabeledCase(context=f"{name}-{index}", label=int(row["label_bin"]),
                                               forecasts=(primary, secondary),
                                               case_id=f"{name}-{index}"))
        model = CouncilModel.fit(cases["calibration"], cases["gate"], cases["pool"],
                                 fusion_method="linear")
        query = prepared[-1]
        cutoff, forecast_time, valid_until = disclosure_window(query, prepared[-2]["label_available"])
        forecast = fitted.forecast(query, "query", cutoff, forecast_time, valid_until)
        prediction = model.predict((forecast,
                                    replace(forecast, specialist_id="rpo-surprise:second-opinion")))
        self.assertAlmostEqual(sum(prediction.probabilities), 1.0, places=9)
        self.assertEqual(len(prediction.gate_weights), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
