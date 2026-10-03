#include "council/jevlike_tiny.hpp"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
#include <limits>
#include <set>
#include <stdexcept>

namespace probabilistic_council {
namespace {
constexpr char expected_magic[8] = {'J', 'V', 'L', 'K', 'C', 'P', 'P', '1'};
constexpr float layer_norm_epsilon = 1e-5F;
constexpr std::uint32_t maximum_width = 4096;
constexpr std::uint32_t maximum_rank = 4096;
constexpr std::uint32_t maximum_context_tokens = 65536;
constexpr std::uint32_t maximum_option_tokens = 65536;
constexpr std::size_t maximum_tensor_elements = 64U * 1024U * 1024U;

void require(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument(message);
}

std::uint32_t read_u32_le(std::ifstream& input) {
    unsigned char bytes[4]{};
    input.read(reinterpret_cast<char*>(bytes), sizeof(bytes));
    require(input.good(), "truncated JevLike C++ weights header");
    return static_cast<std::uint32_t>(bytes[0]) |
           (static_cast<std::uint32_t>(bytes[1]) << 8U) |
           (static_cast<std::uint32_t>(bytes[2]) << 16U) |
           (static_cast<std::uint32_t>(bytes[3]) << 24U);
}

std::size_t checked_product(std::size_t left, std::size_t right) {
    require(right == 0 || left <= maximum_tensor_elements / right,
            "JevLike tensor exceeds the loader size limit");
    return left * right;
}

bool is_valid_utf8(const std::string& text) {
    const auto* bytes = reinterpret_cast<const unsigned char*>(text.data());
    std::size_t index = 0;
    while (index < text.size()) {
        const unsigned char lead = bytes[index];
        if (lead <= 0x7f) {
            ++index;
            continue;
        }

        std::size_t continuation_count = 0;
        unsigned char second_min = 0x80;
        unsigned char second_max = 0xbf;
        if (lead >= 0xc2 && lead <= 0xdf) continuation_count = 1;
        else if (lead == 0xe0) { continuation_count = 2; second_min = 0xa0; }
        else if (lead >= 0xe1 && lead <= 0xec) continuation_count = 2;
        else if (lead == 0xed) { continuation_count = 2; second_max = 0x9f; }
        else if (lead >= 0xee && lead <= 0xef) continuation_count = 2;
        else if (lead == 0xf0) { continuation_count = 3; second_min = 0x90; }
        else if (lead >= 0xf1 && lead <= 0xf3) continuation_count = 3;
        else if (lead == 0xf4) { continuation_count = 3; second_max = 0x8f; }
        else return false;

        if (continuation_count > text.size() - index - 1) return false;
        const unsigned char second = bytes[index + 1];
        if (second < second_min || second > second_max) return false;
        for (std::size_t offset = 2; offset <= continuation_count; ++offset) {
            if (bytes[index + offset] < 0x80 || bytes[index + offset] > 0xbf) return false;
        }
        index += continuation_count + 1;
    }
    return true;
}

std::vector<float> read_floats(std::ifstream& input, std::size_t count) {
    require(count <= maximum_tensor_elements, "JevLike tensor exceeds the loader size limit");
    std::vector<float> values(count);
    for (float& value : values) {
        const std::uint32_t bits = read_u32_le(input);
        static_assert(sizeof(value) == sizeof(bits), "unexpected float width");
        std::memcpy(&value, &bits, sizeof(value));
        require(std::isfinite(value), "JevLike weights contain a non-finite value");
    }
    return values;
}

std::vector<std::size_t> byte_tokens(const std::string& text, std::size_t limit) {
    const std::size_t size = std::min(text.size(), limit);
    std::vector<std::size_t> result;
    result.reserve(size);
    for (std::size_t i = 0; i < size; ++i)
        result.push_back(static_cast<unsigned char>(text[i]) + 1U);
    return result;
}

std::vector<double> layer_norm(const std::vector<double>& input,
                               const std::vector<float>& weight,
                               const std::vector<float>& bias) {
    double mean = 0.0;
    for (double value : input) mean += value;
    mean /= static_cast<double>(input.size());
    double variance = 0.0;
    for (double value : input) {
        const double delta = value - mean;
        variance += delta * delta;
    }
    variance /= static_cast<double>(input.size());
    const double inverse_std = 1.0 / std::sqrt(variance + layer_norm_epsilon);
    std::vector<double> result(input.size());
    for (std::size_t i = 0; i < input.size(); ++i)
        result[i] = (input[i] - mean) * inverse_std * weight[i] + bias[i];
    return result;
}

std::vector<double> linear(const std::vector<double>& input,
                           const std::vector<float>& weights,
                           std::size_t output_width) {
    const std::size_t input_width = input.size();
    std::vector<double> output(output_width, 0.0);
    for (std::size_t row = 0; row < output_width; ++row) {
        double sum = 0.0;
        for (std::size_t col = 0; col < input_width; ++col)
            sum += static_cast<double>(weights[row * input_width + col]) * input[col];
        output[row] = sum;
    }
    return output;
}

}  // namespace

JevLikeTinyScorer JevLikeTinyScorer::load(const std::string& weights_path,
                                         std::string model_version,
                                         std::string data_version) {
    require(!model_version.empty() && !data_version.empty(),
            "JevLike model and data version metadata are required");
    std::ifstream input(weights_path, std::ios::binary);
    if (!input) throw std::runtime_error("cannot open JevLike C++ weights file: " + weights_path);
    char magic[sizeof(expected_magic)]{};
    input.read(magic, sizeof(magic));
    require(input.good() && std::memcmp(magic, expected_magic, sizeof(magic)) == 0,
            "unsupported JevLike C++ weights format");
    JevLikeTinyScorer result;
    result.width_ = read_u32_le(input);
    result.rank_ = read_u32_le(input);
    result.context_tokens_ = read_u32_le(input);
    result.option_tokens_ = read_u32_le(input);
    require(result.width_ > 0 && result.width_ <= maximum_width &&
                result.rank_ > 0 && result.rank_ <= maximum_rank &&
                result.context_tokens_ > 0 && result.context_tokens_ <= maximum_context_tokens &&
                result.option_tokens_ > 0 && result.option_tokens_ <= maximum_option_tokens,
            "JevLike C++ weights have invalid dimensions");

    result.embedding_ = read_floats(input, checked_product(257U, result.width_));
    result.position_ = read_floats(input, checked_product(result.context_tokens_, result.width_));
    result.context_norm_weight_ = read_floats(input, result.width_);
    result.context_norm_bias_ = read_floats(input, result.width_);
    result.option_norm_weight_ = read_floats(input, result.width_);
    result.option_norm_bias_ = read_floats(input, result.width_);
    const auto projection_size = checked_product(result.rank_, result.width_);
    result.query_weight_ = read_floats(input, projection_size);
    result.key_weight_ = read_floats(input, projection_size);
    result.value_weight_ = read_floats(input, projection_size);
    require(input.peek() == std::ifstream::traits_type::eof(),
            "unexpected trailing bytes in JevLike C++ weights file");
    result.model_version_ = std::move(model_version);
    result.data_version_ = std::move(data_version);
    return result;
}

ProbabilityVector JevLikeTinyScorer::score(
    const std::string& decision_text,
    const std::vector<std::string>& options) const {
    require(!decision_text.empty(), "JevLike decision text must be nonempty");
    require(is_valid_utf8(decision_text), "JevLike decision text must be valid UTF-8");
    require(options.size() >= 2 && options.size() <= 4096,
            "JevLike requires between two and 4096 options");
    require(std::all_of(options.begin(), options.end(),
                        [](const std::string& option) { return !option.empty(); }),
            "JevLike options must be nonempty");
    require(std::all_of(options.begin(), options.end(), is_valid_utf8),
            "JevLike options must be valid UTF-8");
    require(std::set<std::string>(options.begin(), options.end()).size() == options.size(),
            "JevLike options must be unique");

    const auto context_ids = byte_tokens(decision_text, context_tokens_);
    require(!context_ids.empty(), "JevLike context has no bytes after encoding");
    std::vector<std::vector<double>> context(context_ids.size(), std::vector<double>(width_));
    for (std::size_t position = 0; position < context_ids.size(); ++position) {
        for (std::size_t feature = 0; feature < width_; ++feature) {
            const double embedding = embedding_[context_ids[position] * width_ + feature];
            const double positional = position_[position * width_ + feature];
            context[position][feature] = embedding + positional;
        }
        context[position] = layer_norm(context[position], context_norm_weight_, context_norm_bias_);
    }

    std::vector<std::vector<double>> options_encoded;
    options_encoded.reserve(options.size());
    for (const auto& option : options) {
        const auto ids = byte_tokens(option, option_tokens_);
        require(!ids.empty(), "JevLike option has no bytes after encoding");
        std::vector<double> vector(width_, 0.0);
        for (std::size_t token : ids)
            for (std::size_t feature = 0; feature < width_; ++feature)
                vector[feature] += embedding_[token * width_ + feature];
        for (double& value : vector) value /= static_cast<double>(ids.size());
        options_encoded.push_back(layer_norm(vector, option_norm_weight_, option_norm_bias_));
    }

    std::vector<std::vector<double>> keys, values;
    keys.reserve(context.size());
    values.reserve(context.size());
    for (const auto& token : context) {
        keys.push_back(linear(token, key_weight_, rank_));
        values.push_back(linear(token, value_weight_, rank_));
    }

    const double scale = std::sqrt(static_cast<double>(rank_));
    ProbabilityVector logits;
    logits.reserve(options_encoded.size());
    for (const auto& option : options_encoded) {
        const auto query = linear(option, query_weight_, rank_);
        std::vector<double> attention(context.size());
        double maximum = -std::numeric_limits<double>::infinity();
        for (std::size_t token = 0; token < context.size(); ++token) {
            double dot = 0.0;
            for (std::size_t component = 0; component < rank_; ++component)
                dot += query[component] * keys[token][component];
            attention[token] = dot / scale;
            maximum = std::max(maximum, attention[token]);
        }
        double total = 0.0;
        for (double& value : attention) { value = std::exp(value - maximum); total += value; }
        for (double& value : attention) value /= total;
        double score = 0.0;
        for (std::size_t component = 0; component < rank_; ++component) {
            double attended = 0.0;
            for (std::size_t token = 0; token < context.size(); ++token)
                attended += attention[token] * values[token][component];
            score += query[component] * attended;
        }
        logits.push_back(score / scale);
    }
    const double maximum = *std::max_element(logits.begin(), logits.end());
    ProbabilityVector probabilities;
    probabilities.reserve(logits.size());
    double total = 0.0;
    for (double logit : logits) { probabilities.push_back(std::exp(logit - maximum)); total += probabilities.back(); }
    for (double& probability : probabilities) probability /= total;
    return probabilities;
}

Forecast JevLikeTinyScorer::forecast(const ChoiceRequest& request,
                                     const std::string& specialist_id) const {
    require(!specialist_id.empty() && !request.context_id.empty(),
            "JevLike forecast needs specialist and context identifiers");
    Forecast result;
    result.specialist_id = specialist_id;
    result.outcome_space = request.options;
    result.probabilities = score(request.decision_text, request.options);
    result.context = request.context_id;
    result.forecast_time = request.forecast_time;
    result.valid_until = request.valid_until;
    result.information_cutoff = request.information_cutoff;
    result.model_version = model_version_;
    result.data_version = data_version_;
    result.validate();
    return result;
}

}  // namespace probabilistic_council
