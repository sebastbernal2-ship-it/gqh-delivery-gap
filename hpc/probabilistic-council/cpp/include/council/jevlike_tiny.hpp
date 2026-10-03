#pragma once

#include "council/council.hpp"

#include <string>
#include <vector>

namespace probabilistic_council {

struct ChoiceRequest {
    std::string decision_text;
    std::vector<std::string> options;
    std::string context_id;
    std::int64_t forecast_time{};
    std::int64_t valid_until{};
    std::int64_t information_cutoff{};
};

// Native C++ inference for checkpoints exported from JevLike's tiny byte encoder.
// Frozen Hugging Face encoders are intentionally not accepted by this loader.
class JevLikeTinyScorer {
public:
    static JevLikeTinyScorer load(const std::string& weights_path,
                                  std::string model_version,
                                  std::string data_version);

    ProbabilityVector score(const std::string& decision_text,
                            const std::vector<std::string>& options) const;
    Forecast forecast(const ChoiceRequest& request,
                      const std::string& specialist_id = "jevlike_tiny") const;

private:
    std::size_t width_{};
    std::size_t rank_{};
    std::size_t context_tokens_{};
    std::size_t option_tokens_{};
    std::vector<float> embedding_;
    std::vector<float> position_;
    std::vector<float> context_norm_weight_;
    std::vector<float> context_norm_bias_;
    std::vector<float> option_norm_weight_;
    std::vector<float> option_norm_bias_;
    std::vector<float> query_weight_;
    std::vector<float> key_weight_;
    std::vector<float> value_weight_;
    std::string model_version_;
    std::string data_version_;
};

}  // namespace probabilistic_council
