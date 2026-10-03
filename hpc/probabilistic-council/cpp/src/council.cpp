#include "council/council.hpp"

#include <algorithm>
#include <atomic>
#include <cmath>
#include <exception>
#include <limits>
#include <set>
#include <stdexcept>
#include <thread>

namespace probabilistic_council {
namespace {
constexpr double probability_floor = 1e-12;
constexpr double brier_floor = 1e-9;
const std::vector<double> temperatures{0.5, 0.65, 0.8, 0.9, 1.0,
                                        1.1, 1.25, 1.5, 2.0, 3.0};

void require(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument(message);
}

bool same_schema(const Forecast& left, const Forecast& right) {
    return left.outcome_space == right.outcome_space &&
           left.dimensions == right.dimensions &&
           left.outcome_states == right.outcome_states;
}

std::map<std::string, double> fit_weights(
    const std::vector<std::size_t>& labels,
    const std::map<std::string, std::vector<ProbabilityVector>>& forecasts,
    double minimum_weight = 0.02) {
    require(!labels.empty() && !forecasts.empty(), "gate group must be nonempty");
    require(minimum_weight >= 0.0 && minimum_weight * forecasts.size() < 1.0,
            "minimum gate weight must be nonnegative and below 1/N");
    std::map<std::string, double> inverse_errors;
    double total = 0.0;
    for (const auto& [name, rows] : forecasts) {
        require(rows.size() == labels.size(), "each specialist needs a forecast for every gate case");
        double error = 0.0;
        for (std::size_t i = 0; i < rows.size(); ++i) error += multiclass_brier(rows[i], labels[i]);
        const double inverse = 1.0 / std::max(brier_floor, error / rows.size());
        inverse_errors.emplace(name, inverse);
        total += inverse;
    }
    std::map<std::string, double> result;
    const double residual = 1.0 - forecasts.size() * minimum_weight;
    for (const auto& [name, inverse] : inverse_errors)
        result.emplace(name, minimum_weight + residual * inverse / total);
    return result;
}

std::map<std::string, ProbabilityVector> calibrated_rows(
    const LabeledCase& row,
    const std::map<std::string, TemperatureCalibrator>& calibrators,
    const std::map<std::pair<std::string, std::string>, TemperatureCalibrator>& context_calibrators) {
    std::map<std::string, ProbabilityVector> result;
    for (const auto& forecast : row.forecasts) {
        if (forecast.abstain) continue;
        const auto it = calibrators.find(forecast.specialist_id);
        require(it != calibrators.end(), "case contains an unfitted specialist: " + forecast.specialist_id);
        const auto contextual = context_calibrators.find({forecast.specialist_id, row.context});
        result.emplace(forecast.specialist_id,
                       (contextual == context_calibrators.end() ? it->second : contextual->second)
                           .apply(forecast.probabilities));
    }
    return result;
}

}  // namespace

void validate_distribution(const std::vector<std::string>& outcomes,
                           const ProbabilityVector& probabilities, double tolerance) {
    require(outcomes.size() >= 2, "outcome space needs at least two labels");
    require(std::set<std::string>(outcomes.begin(), outcomes.end()).size() == outcomes.size(),
            "outcome labels must be unique");
    require(probabilities.size() == outcomes.size(), "probability count must match outcomes");
    double sum = 0.0;
    for (double probability : probabilities) {
        require(std::isfinite(probability) && probability >= 0.0 && probability <= 1.0,
                "probabilities must be finite values in [0, 1]");
        sum += probability;
    }
    require(std::abs(sum - 1.0) <= tolerance, "probabilities must sum to one");
}

void Forecast::validate() const {
    validate_distribution(outcome_space, probabilities);
    require(!specialist_id.empty() && !context.empty() && !model_version.empty() &&
                !data_version.empty(),
            "forecast identity, context, and versions are required");
    require(information_cutoff <= forecast_time && forecast_time < valid_until,
            "information cutoff <= forecast time < valid_until is required");
    if (epistemic_uncertainty)
        require(std::isfinite(*epistemic_uncertainty) && *epistemic_uncertainty >= 0.0,
                "epistemic uncertainty must be finite and nonnegative");
    require(dimensions.empty() == outcome_states.empty(),
            "joint distributions need both dimensions and outcome states");
    if (!dimensions.empty()) {
        require(std::set<std::string>(dimensions.begin(), dimensions.end()).size() == dimensions.size(),
                "joint dimension names must be unique");
        require(outcome_states.size() == outcome_space.size(),
                "joint state count must match the probability vector");
        std::set<OutcomeState> unique_states;
        for (const auto& state : outcome_states) {
            require(state.size() == dimensions.size(), "each joint state needs one value per dimension");
            for (const auto& value : state) require(!value.empty(), "joint state values must be named");
            require(unique_states.insert(state).second, "joint outcome states must be unique");
        }
    }
}

void LabeledCase::validate() const {
    require(!case_id.empty() && !context.empty() && !forecasts.empty(),
            "labeled cases need an id, context, and specialist forecasts");
    for (const auto& forecast : forecasts) forecast.validate();
    const auto& first = forecasts.front();
    std::set<std::string> names;
    for (const auto& forecast : forecasts) {
        require(names.insert(forecast.specialist_id).second,
                "a case cannot contain duplicate specialist ids");
        require(forecast.context == context, "case and specialist contexts must match");
        require(same_schema(first, forecast), "specialists must describe identical outcome spaces");
        require(forecast.forecast_time == first.forecast_time,
                "all specialists in a case must target the same forecast time");
    }
    require(label < first.outcome_space.size(), "label is outside the outcome space");
}

ProbabilityVector temperature_scale(const ProbabilityVector& probabilities, double temperature) {
    require(std::isfinite(temperature) && temperature > 0.0,
            "temperature must be finite and positive");
    require(probabilities.size() >= 2, "temperature scaling needs at least two outcomes");
    std::vector<double> logits;
    logits.reserve(probabilities.size());
    for (double p : probabilities) {
        require(std::isfinite(p) && p >= 0.0 && p <= 1.0,
                "probabilities must be finite values in [0, 1]");
        logits.push_back(std::log(std::max(probability_floor, p)) / temperature);
    }
    const double maximum = *std::max_element(logits.begin(), logits.end());
    ProbabilityVector result;
    result.reserve(logits.size());
    double total = 0.0;
    for (double value : logits) {
        result.push_back(std::exp(value - maximum));
        total += result.back();
    }
    for (double& value : result) value /= total;
    return result;
}

ProbabilityVector TemperatureCalibrator::apply(const ProbabilityVector& probabilities) const {
    return temperature_scale(probabilities, temperature);
}

double multiclass_log_loss(const std::vector<ProbabilityVector>& rows,
                           const std::vector<std::size_t>& labels) {
    require(!rows.empty() && rows.size() == labels.size(),
            "log loss needs equally sized nonempty forecasts and labels");
    double loss = 0.0;
    for (std::size_t i = 0; i < rows.size(); ++i) {
        require(labels[i] < rows[i].size(), "label is outside the forecast outcome space");
        loss -= std::log(std::max(probability_floor, rows[i][labels[i]]));
    }
    return loss / rows.size();
}

double multiclass_brier(const ProbabilityVector& probabilities, std::size_t label) {
    require(label < probabilities.size(), "label is outside the forecast outcome space");
    double score = 0.0;
    for (std::size_t i = 0; i < probabilities.size(); ++i) {
        const double residual = probabilities[i] - (i == label ? 1.0 : 0.0);
        score += residual * residual;
    }
    return score;
}

TemperatureCalibrator fit_temperature(const std::vector<ProbabilityVector>& rows,
                                      const std::vector<std::size_t>& labels) {
    const double before = multiclass_log_loss(rows, labels);
    double best_loss = std::numeric_limits<double>::infinity();
    double best_temperature = 1.0;
    for (double temperature : temperatures) {
        std::vector<ProbabilityVector> scaled;
        scaled.reserve(rows.size());
        for (const auto& row : rows) scaled.push_back(temperature_scale(row, temperature));
        const double loss = multiclass_log_loss(scaled, labels);
        if (loss < best_loss) {
            best_loss = loss;
            best_temperature = temperature;
        }
    }
    return {best_temperature, rows.size(), before, best_loss};
}

std::map<std::string, double> ReliabilityGate::weights_for(
    const std::string& context, const std::vector<std::string>& active_specialists) const {
    require(!active_specialists.empty(), "at least one active specialist is required");
    const auto contextual = context_weights.find(context);
    const auto& source = contextual == context_weights.end() ? global_weights : contextual->second;
    std::map<std::string, double> result;
    double total = 0.0;
    for (const auto& name : active_specialists) {
        const auto it = source.find(name);
        require(it != source.end(), "gate has no fitted weight for specialist: " + name);
        result.emplace(name, it->second);
        total += it->second;
    }
    require(total > 0.0, "active specialists have no reliability weight");
    for (auto& [_, weight] : result) weight /= total;
    return result;
}

ProbabilityVector linear_opinion_pool(
    const std::map<std::string, ProbabilityVector>& distributions,
    const std::map<std::string, double>& weights) {
    require(!distributions.empty(), "at least one active specialist is required");
    const std::size_t size = distributions.begin()->second.size();
    ProbabilityVector result(size, 0.0);
    double total = 0.0;
    for (const auto& [name, row] : distributions) {
        const auto it = weights.find(name);
        require(it != weights.end(), "active specialist has no fitted weight: " + name);
        require(std::isfinite(it->second) && it->second >= 0.0,
                "fusion weights must be finite and nonnegative");
        require(row.size() == size, "all specialists need the same outcome count");
        total += it->second;
    }
    require(total > 0.0, "active fusion weights must have positive mass");
    for (const auto& [name, row] : distributions) {
        const double weight = weights.at(name) / total;
        for (std::size_t i = 0; i < size; ++i) result[i] += weight * row[i];
    }
    return result;
}

ProbabilityVector logarithmic_opinion_pool(
    const std::map<std::string, ProbabilityVector>& distributions,
    const std::map<std::string, double>& weights) {
    require(!distributions.empty(), "at least one active specialist is required");
    const std::size_t size = distributions.begin()->second.size();
    std::map<std::string, double> normalized;
    double total = 0.0;
    for (const auto& [name, row] : distributions) {
        const auto it = weights.find(name);
        require(it != weights.end(), "active specialist has no fitted weight: " + name);
        require(std::isfinite(it->second) && it->second >= 0.0,
                "fusion weights must be finite and nonnegative");
        require(row.size() == size, "all specialists need the same outcome count");
        normalized.emplace(name, it->second);
        total += it->second;
    }
    require(total > 0.0, "active fusion weights must have positive mass");
    ProbabilityVector logits(size, 0.0);
    for (const auto& [name, row] : distributions) {
        const double weight = normalized.at(name) / total;
        for (std::size_t i = 0; i < size; ++i)
            logits[i] += weight * std::log(std::max(probability_floor, row[i]));
    }
    const double maximum = *std::max_element(logits.begin(), logits.end());
    double sum = 0.0;
    for (double& value : logits) { value = std::exp(value - maximum); sum += value; }
    for (double& value : logits) value /= sum;
    return logits;
}

ProbabilityVector CouncilModel::fuse(
    const std::map<std::string, ProbabilityVector>& distributions,
    const std::map<std::string, double>& weights, FusionMethod method) {
    return method == FusionMethod::linear ? linear_opinion_pool(distributions, weights)
                                          : logarithmic_opinion_pool(distributions, weights);
}

CouncilModel CouncilModel::fit(
    const std::vector<LabeledCase>& calibration_cases,
    const std::vector<LabeledCase>& gate_cases,
    const std::vector<LabeledCase>& pool_cases,
    FusionMethod fusion_method,
    std::size_t minimum_context_rows) {
    require(!calibration_cases.empty() && !gate_cases.empty() && !pool_cases.empty(),
            "specialist calibration, gate fit, and pool calibration partitions are required");
    std::set<std::string> ids;
    std::vector<const std::vector<LabeledCase>*> partitions{&calibration_cases, &gate_cases, &pool_cases};
    std::int64_t prior_end = std::numeric_limits<std::int64_t>::min();
    Forecast schema = calibration_cases.front().forecasts.front();
    std::int64_t fit_through = prior_end;
    for (const auto* partition : partitions) {
        std::int64_t start = std::numeric_limits<std::int64_t>::max();
        std::int64_t end = std::numeric_limits<std::int64_t>::min();
        for (const auto& row : *partition) {
            row.validate();
            require(ids.insert(row.case_id).second, "case ids must be unique across fit partitions");
            require(same_schema(schema, row.forecasts.front()),
                    "all partitions must share an ordered outcome and joint-state schema");
            start = std::min(start, row.forecasts.front().forecast_time);
            end = std::max(end, row.forecasts.front().forecast_time);
        }
        require(prior_end < start, "fit partitions must be strictly chronological");
        prior_end = end;
        fit_through = end;
    }

    CouncilModel model;
    model.outcome_space_ = schema.outcome_space;
    model.dimensions_ = schema.dimensions;
    model.outcome_states_ = schema.outcome_states;
    model.fusion_method_ = fusion_method;
    model.fit_through_ = fit_through;
    model.gate_.minimum_context_rows = minimum_context_rows;

    std::map<std::string, std::vector<ProbabilityVector>> calibration_rows;
    std::map<std::string, std::vector<std::size_t>> calibration_labels;
    std::map<std::pair<std::string, std::string>, std::vector<ProbabilityVector>> context_rows;
    std::map<std::pair<std::string, std::string>, std::vector<std::size_t>> context_labels;
    for (const auto& row : calibration_cases) {
        for (const auto& forecast : row.forecasts) {
            if (forecast.abstain) continue;
            calibration_rows[forecast.specialist_id].push_back(forecast.probabilities);
            calibration_labels[forecast.specialist_id].push_back(row.label);
            const auto key = std::make_pair(forecast.specialist_id, row.context);
            context_rows[key].push_back(forecast.probabilities);
            context_labels[key].push_back(row.label);
        }
    }
    require(!calibration_rows.empty(), "calibration partition has no active forecasts");
    for (const auto& [name, rows] : calibration_rows) {
        model.specialists_.push_back(name);
        model.calibrators_.emplace(name, fit_temperature(rows, calibration_labels.at(name)));
    }
    for (const auto& [key, rows] : context_rows) {
        if (rows.size() >= minimum_context_rows)
            model.context_calibrators_.emplace(key, fit_temperature(rows, context_labels.at(key)));
    }

    std::map<std::string, std::vector<ProbabilityVector>> global_gate_rows;
    std::vector<std::size_t> gate_labels;
    std::vector<std::string> gate_contexts;
    for (const auto& name : model.specialists_) global_gate_rows.emplace(name, std::vector<ProbabilityVector>{});
    for (const auto& row : gate_cases) {
        auto distributions = calibrated_rows(row, model.calibrators_, model.context_calibrators_);
        require(distributions.size() == model.specialists_.size(),
                "each gate-fit case must cover every calibrated specialist");
        for (const auto& [name, probabilities] : distributions) global_gate_rows.at(name).push_back(probabilities);
        gate_labels.push_back(row.label);
        gate_contexts.push_back(row.context);
    }
    model.gate_.global_weights = fit_weights(gate_labels, global_gate_rows);
    for (const auto& context : gate_contexts) ++model.gate_.sample_counts[context];
    model.gate_.sample_counts["__global__"] = gate_cases.size();
    std::set<std::string> contexts(gate_contexts.begin(), gate_contexts.end());
    for (const auto& context : contexts) {
        std::vector<std::size_t> labels;
        std::map<std::string, std::vector<ProbabilityVector>> rows;
        for (const auto& name : model.specialists_) rows.emplace(name, std::vector<ProbabilityVector>{});
        for (std::size_t i = 0; i < gate_cases.size(); ++i) {
            if (gate_cases[i].context != context) continue;
            auto values = calibrated_rows(gate_cases[i], model.calibrators_, model.context_calibrators_);
            labels.push_back(gate_cases[i].label);
            for (const auto& [name, probabilities] : values) rows.at(name).push_back(probabilities);
        }
        if (labels.size() >= minimum_context_rows)
            model.gate_.context_weights.emplace(context, fit_weights(labels, rows));
    }

    std::vector<ProbabilityVector> pooled_rows;
    std::vector<std::size_t> pooled_labels;
    for (const auto& row : pool_cases) {
        auto distributions = calibrated_rows(row, model.calibrators_, model.context_calibrators_);
        require(!distributions.empty(), "pool calibration case has no active specialist");
        std::vector<std::string> active;
        for (const auto& [name, _] : distributions) active.push_back(name);
        const auto weights = model.gate_.weights_for(row.context, active);
        pooled_rows.push_back(fuse(distributions, weights, fusion_method));
        pooled_labels.push_back(row.label);
    }
    model.pool_calibrator_ = fit_temperature(pooled_rows, pooled_labels);
    return model;
}

ProbabilityVector CouncilModel::calibrate(const Forecast& forecast) const {
    const auto contextual = context_calibrators_.find({forecast.specialist_id, forecast.context});
    const auto global = calibrators_.find(forecast.specialist_id);
    require(global != calibrators_.end(), "forecast specialist was not present at fit time");
    return (contextual == context_calibrators_.end() ? global->second : contextual->second)
        .apply(forecast.probabilities);
}

CouncilPrediction CouncilModel::predict(const std::vector<Forecast>& forecasts) const {
    require(!forecasts.empty(), "prediction needs at least one specialist forecast");
    for (const auto& forecast : forecasts) forecast.validate();
    const auto& first = forecasts.front();
    require(first.forecast_time > fit_through_, "prediction must be later than every fit partition");
    std::set<std::string> ids;
    std::map<std::string, ProbabilityVector> distributions;
    std::vector<std::string> active;
    std::vector<std::string> abstained;
    for (const auto& forecast : forecasts) {
        require(same_schema(first, forecast), "specialists must share one outcome and joint-state schema");
        require(forecast.context == first.context && forecast.forecast_time == first.forecast_time,
                "specialist forecasts must share context and forecast time");
        require(ids.insert(forecast.specialist_id).second, "duplicate specialist forecast");
        require(calibrators_.count(forecast.specialist_id) != 0,
                "forecast specialist was not present at fit time");
        if (forecast.abstain) abstained.push_back(forecast.specialist_id);
        else {
            active.push_back(forecast.specialist_id);
            distributions.emplace(forecast.specialist_id, calibrate(forecast));
        }
    }
    require(!distributions.empty(), "all specialists abstained");
    const auto weights = gate_.weights_for(first.context, active);
    const auto raw_pool = fuse(distributions, weights, fusion_method_);
    const auto final_probabilities = pool_calibrator_.apply(raw_pool);
    double entropy = 0.0;
    for (double p : final_probabilities) entropy -= p * std::log(std::max(probability_floor, p));
    double disagreement = 0.0;
    for (const auto& [name, probabilities] : distributions) {
        const double weight = weights.at(name);
        for (std::size_t i = 0; i < probabilities.size(); ++i) {
            const double delta = probabilities[i] - raw_pool[i];
            disagreement += weight * delta * delta;
        }
    }
    double uncertainty_sum = 0.0;
    double uncertainty_weight = 0.0;
    for (const auto& forecast : forecasts) {
        if (forecast.abstain || !forecast.epistemic_uncertainty) continue;
        const double weight = weights.at(forecast.specialist_id);
        uncertainty_sum += weight * *forecast.epistemic_uncertainty;
        uncertainty_weight += weight;
    }
    std::optional<double> uncertainty;
    if (uncertainty_weight > 0.0) uncertainty = uncertainty_sum / uncertainty_weight;
    return {outcome_space_, final_probabilities, first.forecast_time, active, abstained,
            weights, entropy, disagreement, uncertainty, fusion_method_, dimensions_, outcome_states_};
}

CouncilPrediction CouncilModel::predict_parallel(const std::vector<SpecialistTask>& tasks,
                                                  std::size_t max_workers) const {
    require(!tasks.empty(), "parallel prediction needs at least one specialist task");
    std::set<std::string> names;
    for (const auto& task : tasks) {
        require(!task.specialist_id.empty() && static_cast<bool>(task.infer),
                "parallel tasks need an id and inference callable");
        require(names.insert(task.specialist_id).second, "duplicate parallel specialist task");
        require(std::find(specialists_.begin(), specialists_.end(), task.specialist_id) != specialists_.end(),
                "parallel task is not a fitted specialist: " + task.specialist_id);
    }
    const std::size_t worker_count = max_workers == 0 ? std::min<std::size_t>(8, tasks.size())
                                                       : max_workers;
    require(worker_count > 0, "max_workers must be positive");
    const std::size_t actual_workers = std::min(worker_count, tasks.size());
    std::vector<Forecast> outputs(tasks.size());
    std::vector<std::exception_ptr> failures(tasks.size());
    std::atomic<std::size_t> next{0};
    std::vector<std::thread> workers;
    workers.reserve(actual_workers);
    for (std::size_t worker = 0; worker < actual_workers; ++worker) {
        workers.emplace_back([&]() {
            while (true) {
                const std::size_t index = next.fetch_add(1);
                if (index >= tasks.size()) return;
                try {
                    outputs[index] = tasks[index].infer();
                    require(outputs[index].specialist_id == tasks[index].specialist_id,
                            "parallel task key does not match returned forecast specialist id");
                } catch (...) { failures[index] = std::current_exception(); }
            }
        });
    }
    for (auto& worker : workers) worker.join();
    for (std::size_t i = 0; i < failures.size(); ++i) {
        if (!failures[i]) continue;
        try { std::rethrow_exception(failures[i]); }
        catch (const std::exception& error) {
            throw std::runtime_error("specialist inference failed: " + tasks[i].specialist_id +
                                     ": " + error.what());
        }
        catch (...) { throw std::runtime_error("specialist inference failed: " + tasks[i].specialist_id); }
    }
    return predict(outputs);
}

std::map<std::string, double> CouncilPrediction::marginal(const std::string& dimension) const {
    const auto it = std::find(dimensions.begin(), dimensions.end(), dimension);
    require(it != dimensions.end(), "requested dimension is not declared in this joint forecast");
    require(outcome_states.size() == probabilities.size(), "joint output state metadata is incomplete");
    const auto index = static_cast<std::size_t>(it - dimensions.begin());
    std::map<std::string, double> result;
    for (std::size_t i = 0; i < probabilities.size(); ++i) result[outcome_states[i][index]] += probabilities[i];
    return result;
}

}  // namespace probabilistic_council
