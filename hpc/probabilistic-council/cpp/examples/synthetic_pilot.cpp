#include "council/council.hpp"

#include <cmath>
#include <iomanip>
#include <iostream>
#include <random>
#include <sstream>

using namespace probabilistic_council;

namespace {
Forecast make_forecast(const std::string& specialist, const std::string& context,
                       std::int64_t time, double probability_yes) {
    Forecast forecast;
    forecast.specialist_id = specialist;
    forecast.outcome_space = {"no", "yes"};
    forecast.probabilities = {1.0 - probability_yes, probability_yes};
    forecast.context = context;
    forecast.forecast_time = time;
    forecast.valid_until = time + 10;
    forecast.information_cutoff = time - 1;
    forecast.model_version = "synthetic-v1";
    forecast.data_version = "synthetic-seed-20261003";
    forecast.epistemic_uncertainty = 0.1;
    return forecast;
}

LabeledCase make_case(std::size_t index, std::mt19937_64& rng) {
    const std::string context = index % 2 == 0 ? "trend" : "reversal";
    const double truth = context == "trend" ? 0.72 : 0.28;
    std::bernoulli_distribution sample(truth);
    const auto time = static_cast<std::int64_t>(index + 1);
    const double trend = context == "trend" ? 0.78 : 0.35;
    const double reversal = context == "trend" ? 0.35 : 0.78;
    return {"case-" + std::to_string(index), context, sample(rng) ? 1U : 0U,
            {make_forecast("trend", context, time, trend),
             make_forecast("reversal", context, time, reversal)}};
}
}  // namespace

int main() {
    std::mt19937_64 rng(20261003);
    std::vector<LabeledCase> calibration, gate, pool;
    for (std::size_t i = 0; i < 360; ++i) {
        auto row = make_case(i, rng);
        if (i < 120) calibration.push_back(std::move(row));
        else if (i < 240) gate.push_back(std::move(row));
        else pool.push_back(std::move(row));
    }

    const auto council = CouncilModel::fit(calibration, gate, pool,
                                           FusionMethod::logarithmic, 20);
    std::vector<ProbabilityVector> predictions;
    std::vector<std::size_t> labels;
    for (std::size_t i = 360; i < 480; ++i) {
        const auto row = make_case(i, rng);
        const auto prediction = council.predict(row.forecasts);
        predictions.push_back(prediction.probabilities);
        labels.push_back(row.label);
    }
    const auto first_time = static_cast<std::int64_t>(481);
    const auto trend_task = SpecialistTask{
        "trend", [=] { return make_forecast("trend", "trend", first_time, 0.78); }};
    const auto reversal_task = SpecialistTask{
        "reversal", [=] { return make_forecast("reversal", "trend", first_time, 0.35); }};
    const auto parallel = council.predict_parallel({trend_task, reversal_task}, 2);

    std::cout << std::fixed << std::setprecision(6)
              << "{\"contract\":\"" << contract_version << "\","
              << "\"data\":\"synthetic_fixture_only\","
              << "\"evaluation_rows\":" << predictions.size() << ","
              << "\"log_loss\":" << multiclass_log_loss(predictions, labels) << ","
              << "\"multiclass_brier\":";
    double brier = 0.0;
    for (std::size_t i = 0; i < predictions.size(); ++i)
        brier += multiclass_brier(predictions[i], labels[i]);
    brier /= predictions.size();
    std::cout << brier << ",\"parallel_first_distribution\":["
              << parallel.probabilities[0] << "," << parallel.probabilities[1] << "],"
              << "\"parallel_entropy_nats\":" << parallel.predictive_entropy << ","
              << "\"fit_through\":" << council.fit_through() << "}\n";
}
