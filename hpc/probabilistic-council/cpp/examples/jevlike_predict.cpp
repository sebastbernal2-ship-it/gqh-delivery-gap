#include "council/jevlike_tiny.hpp"

#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

using namespace probabilistic_council;

namespace {
std::string json_escape(const std::string& value) {
    std::string escaped;
    escaped.reserve(value.size());
    for (unsigned char ch : value) {
        switch (ch) {
            case '"': escaped += "\\\""; break;
            case '\\': escaped += "\\\\"; break;
            case '\b': escaped += "\\b"; break;
            case '\f': escaped += "\\f"; break;
            case '\n': escaped += "\\n"; break;
            case '\r': escaped += "\\r"; break;
            case '\t': escaped += "\\t"; break;
            default:
                if (ch < 0x20) {
                    constexpr char hex[] = "0123456789abcdef";
                    escaped += "\\u00";
                    escaped += hex[ch >> 4];
                    escaped += hex[ch & 0x0f];
                } else {
                    escaped += static_cast<char>(ch);
                }
        }
    }
    return escaped;
}
}  // namespace

int main(int argc, char** argv) {
    if (argc < 10) {
        std::cerr << "usage: jevlike-predict-cpp WEIGHTS MODEL_VERSION DATA_VERSION "
                     "TEXT CONTEXT_ID FORECAST_TIME VALID_UNTIL CUTOFF OPTION OPTION...\n";
        return 2;
    }
    const auto scorer = JevLikeTinyScorer::load(argv[1], argv[2], argv[3]);
    ChoiceRequest request;
    request.decision_text = argv[4];
    request.context_id = argv[5];
    request.forecast_time = std::stoll(argv[6]);
    request.valid_until = std::stoll(argv[7]);
    request.information_cutoff = std::stoll(argv[8]);
    for (int i = 9; i < argc; ++i) request.options.emplace_back(argv[i]);
    const Forecast result = scorer.forecast(request);
    std::cout << std::fixed << std::setprecision(9)
              << "{\"contract\":\"" << contract_version << "\","
              << "\"specialist_id\":\"" << json_escape(result.specialist_id) << "\","
              << "\"context\":\"" << json_escape(result.context) << "\","
              << "\"forecast_time\":" << result.forecast_time << ','
              << "\"valid_until\":" << result.valid_until << ','
              << "\"information_cutoff\":" << result.information_cutoff << ','
              << "\"model_version\":\"" << json_escape(result.model_version) << "\","
              << "\"data_version\":\"" << json_escape(result.data_version) << "\","
              << "\"abstain\":" << (result.abstain ? "true" : "false") << ','
              << "\"outcome_space\":[";
    for (std::size_t i = 0; i < result.outcome_space.size(); ++i) {
        if (i) std::cout << ',';
        std::cout << '"' << json_escape(result.outcome_space[i]) << '"';
    }
    std::cout << "],\"probabilities\":[";
    for (std::size_t i = 0; i < result.probabilities.size(); ++i) {
        if (i) std::cout << ',';
        std::cout << result.probabilities[i];
    }
    std::cout << "]}\n";
    return 0;
}
