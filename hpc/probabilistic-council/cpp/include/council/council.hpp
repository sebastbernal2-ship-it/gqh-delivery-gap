#pragma once

#include <cstdint>
#include <functional>
#include <map>
#include <optional>
#include <string>
#include <utility>
#include <vector>

namespace probabilistic_council {

inline constexpr const char* contract_version = "council-distribution-0.2.0";
using ProbabilityVector = std::vector<double>;
using OutcomeState = std::vector<std::string>;

enum class FusionMethod { linear, logarithmic };

struct Forecast {
    std::string specialist_id;
    std::vector<std::string> outcome_space;
    ProbabilityVector probabilities;
    std::string context;
    // UTC Unix seconds. The caller owns ISO-8601 parsing and source-clock provenance.
    std::int64_t forecast_time{};
    std::int64_t valid_until{};
    std::int64_t information_cutoff{};
    std::string model_version;
    std::string data_version;
    std::optional<double> epistemic_uncertainty;
    bool abstain{false};
    std::vector<std::string> dimensions;
    std::vector<OutcomeState> outcome_states;

    void validate() const;
};

struct LabeledCase {
    std::string case_id;
    std::string context;
    std::size_t label{};
    std::vector<Forecast> forecasts;

    void validate() const;
};

struct TemperatureCalibrator {
    double temperature{1.0};
    std::size_t sample_count{};
    double log_loss_before{};
    double log_loss_after{};
    ProbabilityVector apply(const ProbabilityVector& probabilities) const;
};

struct ReliabilityGate {
    std::map<std::string, double> global_weights;
    std::map<std::string, std::map<std::string, double>> context_weights;
    std::map<std::string, std::size_t> sample_counts;
    std::size_t minimum_context_rows{40};

    std::map<std::string, double> weights_for(
        const std::string& context,
        const std::vector<std::string>& active_specialists) const;
};

struct CouncilPrediction {
    std::vector<std::string> outcome_space;
    ProbabilityVector probabilities;
    std::int64_t forecast_time{};
    std::vector<std::string> active_specialists;
    std::vector<std::string> abstained_specialists;
    std::map<std::string, double> gate_weights;
    double predictive_entropy{};
    double between_model_disagreement{};
    std::optional<double> weighted_input_epistemic_uncertainty;
    FusionMethod fusion_method{FusionMethod::linear};
    std::vector<std::string> dimensions;
    std::vector<OutcomeState> outcome_states;

    std::map<std::string, double> marginal(const std::string& dimension) const;
};

struct SpecialistTask {
    std::string specialist_id;
    std::function<Forecast()> infer;
};

class CouncilModel {
public:
    static CouncilModel fit(
        const std::vector<LabeledCase>& specialist_calibration_cases,
        const std::vector<LabeledCase>& gate_fit_cases,
        const std::vector<LabeledCase>& pool_calibration_cases,
        FusionMethod fusion_method = FusionMethod::linear,
        std::size_t minimum_context_rows = 40);

    CouncilPrediction predict(const std::vector<Forecast>& forecasts) const;
    CouncilPrediction predict_parallel(
        const std::vector<SpecialistTask>& tasks,
        std::size_t max_workers = 0) const;

    const std::vector<std::string>& outcome_space() const noexcept { return outcome_space_; }
    const std::vector<std::string>& specialists() const noexcept { return specialists_; }
    std::int64_t fit_through() const noexcept { return fit_through_; }
    FusionMethod fusion_method() const noexcept { return fusion_method_; }

private:
    std::vector<std::string> outcome_space_;
    std::vector<std::string> dimensions_;
    std::vector<OutcomeState> outcome_states_;
    std::vector<std::string> specialists_;
    std::map<std::string, TemperatureCalibrator> calibrators_;
    std::map<std::pair<std::string, std::string>, TemperatureCalibrator> context_calibrators_;
    ReliabilityGate gate_;
    TemperatureCalibrator pool_calibrator_;
    FusionMethod fusion_method_{FusionMethod::linear};
    std::int64_t fit_through_{};

    ProbabilityVector calibrate(const Forecast& forecast) const;
    static ProbabilityVector fuse(
        const std::map<std::string, ProbabilityVector>& distributions,
        const std::map<std::string, double>& weights,
        FusionMethod method);
};

void validate_distribution(const std::vector<std::string>& outcomes,
                           const ProbabilityVector& probabilities,
                           double tolerance = 1e-9);
ProbabilityVector temperature_scale(const ProbabilityVector& probabilities, double temperature);
double multiclass_log_loss(const std::vector<ProbabilityVector>& rows,
                           const std::vector<std::size_t>& labels);
double multiclass_brier(const ProbabilityVector& probabilities, std::size_t label);
TemperatureCalibrator fit_temperature(const std::vector<ProbabilityVector>& rows,
                                      const std::vector<std::size_t>& labels);
ProbabilityVector linear_opinion_pool(
    const std::map<std::string, ProbabilityVector>& distributions,
    const std::map<std::string, double>& weights);
ProbabilityVector logarithmic_opinion_pool(
    const std::map<std::string, ProbabilityVector>& distributions,
    const std::map<std::string, double>& weights);

}  // namespace probabilistic_council
