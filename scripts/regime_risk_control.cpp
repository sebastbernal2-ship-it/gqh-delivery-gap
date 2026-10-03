// Development-only volatility-regime risk overlay for the aggregate capacity strategy.
//
// Build with C++17 using the standard library only:
// c++ -std=c++17 -O2 -Wall -Wextra -Wpedantic scripts/regime_risk_control.cpp -o executable
//
// The runner consumes the existing monthly strategy artifact and a retained Massive daily-bars
// TSV produced by hpc/kdb-timeseries/scripts/export_tiger_bars.py. It uses SPY adjusted closes,
// classifies high-volatility states from past observations only, and halves pair exposure in that
// state. It has no network or provider dependency. Its date fence deliberately excludes rows whose
// return interval crosses the sealed boundary in docs/plan/sealed-test.md.

#include <algorithm>
#include <array>
#include <cctype>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <map>
#include <numeric>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

namespace {
constexpr const char* kDevelopmentStart = "2015-07";
constexpr const char* kDevelopmentLastVintage = "2022-09";
constexpr const char* kDevelopmentLastOutcome = "2022-09-30";
constexpr std::size_t kVolWindow = 20;
constexpr std::size_t kThresholdLookback = 252;
constexpr std::size_t kMinimumThresholdObservations = 126;
constexpr double kHighVolQuantile = 0.80;
constexpr double kHighVolExposure = 0.50;
constexpr double kCostPerLeg = 0.0010;  // 10 bps; doubled-cost results use 20 bps.
constexpr std::int64_t kPriceScale = 100000000;

using Row = std::vector<std::string>;

std::string trim_cr(std::string value) {
    if (!value.empty() && value.back() == '\r') value.pop_back();
    return value;
}

Row split_delimited(const std::string& line, char delimiter) {
    Row fields;
    std::string field;
    bool quoted = false;
    for (std::size_t i = 0; i < line.size(); ++i) {
        const char c = line[i];
        if (c == '"') {
            if (quoted && i + 1 < line.size() && line[i + 1] == '"') {
                field.push_back('"');
                ++i;
            } else {
                quoted = !quoted;
            }
        } else if (c == delimiter && !quoted) {
            fields.push_back(field);
            field.clear();
        } else {
            field.push_back(c);
        }
    }
    if (quoted) throw std::runtime_error("unterminated quoted field");
    fields.push_back(field);
    return fields;
}

std::map<std::string, std::size_t> header_map(const Row& header) {
    std::map<std::string, std::size_t> result;
    for (std::size_t i = 0; i < header.size(); ++i) {
        if (!result.emplace(header[i], i).second)
            throw std::runtime_error("duplicate column in input header: " + header[i]);
    }
    return result;
}

std::string field(const Row& row, const std::map<std::string, std::size_t>& columns,
                  const std::string& name) {
    const auto it = columns.find(name);
    if (it == columns.end()) throw std::runtime_error("missing input column: " + name);
    if (it->second >= row.size()) throw std::runtime_error("short input row at column: " + name);
    return row[it->second];
}

double number(const std::string& text, const std::string& label) {
    std::size_t used = 0;
    double value = 0.0;
    try {
        value = std::stod(text, &used);
    } catch (...) {
        throw std::runtime_error("invalid number in " + label + ": " + text);
    }
    if (used != text.size() || !std::isfinite(value))
        throw std::runtime_error("invalid finite number in " + label + ": " + text);
    return value;
}

std::int64_t integer(const std::string& text, const std::string& label) {
    std::size_t used = 0;
    long long value = 0;
    try {
        value = std::stoll(text, &used);
    } catch (...) {
        throw std::runtime_error("invalid integer in " + label + ": " + text);
    }
    if (used != text.size()) throw std::runtime_error("invalid integer in " + label + ": " + text);
    return static_cast<std::int64_t>(value);
}

std::string iso_date(std::string value) {
    std::replace(value.begin(), value.end(), '.', '-');
    if (value.size() != 10 || value[4] != '-' || value[7] != '-')
        throw std::runtime_error("expected YYYY-MM-DD date, got: " + value);
    return value;
}

std::string csv_escape(const std::string& value) {
    if (value.find_first_of(",\"\r\n") == std::string::npos) return value;
    std::string escaped = "\"";
    for (char c : value) {
        if (c == '"') escaped.push_back('"');
        escaped.push_back(c);
    }
    escaped.push_back('"');
    return escaped;
}

std::string format_optional(const std::optional<double>& value) {
    if (!value) return "";
    std::ostringstream out;
    out << std::setprecision(12) << *value;
    return out.str();
}

struct TradePeriod {
    std::string vintage;
    std::string signal;
    std::string entry;
    std::string exit;
    std::string position;
    double gross = 0.0;
    std::string spy_asof;
    std::optional<double> spy_vol;
    std::optional<double> threshold;
    std::string regime = "warmup";
    double multiplier = 1.0;
};

std::vector<TradePeriod> read_development_strategy(const std::string& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("cannot open strategy input: " + path);
    std::string line;
    if (!std::getline(input, line)) throw std::runtime_error("empty strategy input");
    const auto columns = header_map(split_delimited(trim_cr(line), ','));
    // Check required columns before reading outcomes.
    for (const auto* name : {"vintage", "signal", "position", "gross", "entry", "exit"})
        if (!columns.count(name)) throw std::runtime_error(std::string("missing strategy column: ") + name);

    std::vector<TradePeriod> rows;
    std::set<std::pair<std::string, std::string>> seen;
    while (std::getline(input, line)) {
        line = trim_cr(line);
        if (line.empty()) continue;
        const Row row = split_delimited(line, ',');
        const std::string vintage = field(row, columns, "vintage");
        // Fence by vintage before parsing any return or position outcome fields.
        if (vintage < kDevelopmentStart || vintage > kDevelopmentLastVintage) continue;
        const std::string exit = iso_date(field(row, columns, "exit"));
        // A development signal whose holding interval runs into October 2022 is excluded too.
        if (exit > kDevelopmentLastOutcome) continue;

        TradePeriod trade;
        trade.vintage = vintage;
        trade.signal = field(row, columns, "signal");
        trade.position = field(row, columns, "position");
        trade.entry = iso_date(field(row, columns, "entry"));
        trade.exit = exit;
        if (trade.entry > trade.exit) throw std::runtime_error("entry is after exit for " + vintage);
        if (trade.position.find("buildout") == std::string::npos &&
            trade.position.find("scarcity") == std::string::npos)
            throw std::runtime_error("unrecognized position label: " + trade.position);
        trade.gross = number(field(row, columns, "gross"), "gross");
        if (!seen.emplace(trade.vintage, trade.signal).second)
            throw std::runtime_error("duplicate vintage/signal row: " + trade.vintage + "/" + trade.signal);
        rows.push_back(std::move(trade));
    }
    if (rows.empty()) throw std::runtime_error("no complete development-period strategy rows");
    std::sort(rows.begin(), rows.end(), [](const auto& a, const auto& b) {
        return std::tie(a.signal, a.vintage) < std::tie(b.signal, b.vintage);
    });
    return rows;
}

struct SpyBar { std::string date; double close = 0.0; };

std::vector<SpyBar> read_spy_bars(const std::string& path, const std::string& last_needed_date,
                                  std::string& batch_hash) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("cannot open retained daily-bars TSV: " + path);
    std::string line;
    if (!std::getline(input, line)) throw std::runtime_error("empty daily-bars TSV");
    const auto columns = header_map(split_delimited(trim_cr(line), '\t'));
    for (const auto* name : {"date", "sym", "source_id", "batch_sha256", "close_px_e8usd"})
        if (!columns.count(name)) throw std::runtime_error(std::string("missing bars column: ") + name);

    std::map<std::string, SpyBar> by_date;
    std::set<std::string> batches;
    while (std::getline(input, line)) {
        line = trim_cr(line);
        if (line.empty()) continue;
        const Row row = split_delimited(line, '\t');
        if (field(row, columns, "sym") != "SPY") continue;
        const std::string date = iso_date(field(row, columns, "date"));
        // Ignore all rows after the last development entry before parsing their prices.
        if (date > last_needed_date) continue;
        if (field(row, columns, "source_id") != "massive_bars")
            throw std::runtime_error("SPY must come from the adjusted massive_bars source");
        const std::string batch = field(row, columns, "batch_sha256");
        if (batch.size() != 64 || !std::all_of(batch.begin(), batch.end(), [](unsigned char c) {
                return std::isdigit(c) || (c >= 'a' && c <= 'f');
            }))
            throw std::runtime_error("SPY batch hash is not a lowercase SHA-256 value");
        batches.insert(batch);
        const auto scaled_close = integer(field(row, columns, "close_px_e8usd"), "close_px_e8usd");
        if (scaled_close <= 0) throw std::runtime_error("SPY close must be positive");
        const double close = static_cast<double>(scaled_close) / static_cast<double>(kPriceScale);
        if (!by_date.emplace(date, SpyBar{date, close}).second)
            throw std::runtime_error("duplicate SPY session in daily-bars input: " + date);
    }
    if (batches.size() != 1) throw std::runtime_error("SPY bars must come from exactly one source batch");
    batch_hash = *batches.begin();
    std::vector<SpyBar> bars;
    for (const auto& [date, bar] : by_date) bars.push_back(bar);
    if (bars.size() <= kVolWindow + kMinimumThresholdObservations)
        throw std::runtime_error("not enough pre-boundary SPY history to classify regimes");
    return bars;
}

struct VolPoint { std::string date; double annualized = 0.0; };

std::vector<VolPoint> realized_volatility(const std::vector<SpyBar>& bars) {
    std::vector<double> log_returns(bars.size(), 0.0);
    for (std::size_t i = 1; i < bars.size(); ++i)
        log_returns[i] = std::log(bars[i].close / bars[i - 1].close);
    std::vector<VolPoint> result;
    for (std::size_t i = kVolWindow; i < bars.size(); ++i) {
        const auto first = log_returns.begin() + static_cast<std::ptrdiff_t>(i - kVolWindow + 1);
        const auto last = log_returns.begin() + static_cast<std::ptrdiff_t>(i + 1);
        const std::size_t n = static_cast<std::size_t>(std::distance(first, last));
        const double mean = std::accumulate(first, last, 0.0) / static_cast<double>(n);
        double squared = 0.0;
        for (auto it = first; it != last; ++it) squared += (*it - mean) * (*it - mean);
        const double sd = std::sqrt(squared / static_cast<double>(n - 1));
        result.push_back({bars[i].date, sd * std::sqrt(252.0)});
    }
    return result;
}

double quantile_nearest_rank(std::vector<double> values, double probability) {
    if (values.empty()) throw std::runtime_error("cannot compute quantile of empty values");
    std::sort(values.begin(), values.end());
    const auto rank = static_cast<std::size_t>(std::ceil(probability * values.size()));
    return values[std::max<std::size_t>(1, rank) - 1];
}

void classify_periods(std::vector<TradePeriod>& trades, const std::vector<VolPoint>& vols) {
    for (auto& trade : trades) {
        const auto bar = std::lower_bound(vols.begin(), vols.end(), trade.entry,
                                          [](const VolPoint& point, const std::string& date) {
                                              return point.date < date;
                                          });
        if (bar == vols.begin()) continue;
        const auto asof = std::prev(bar);  // State uses only a close strictly before entry.
        trade.spy_asof = asof->date;
        trade.spy_vol = asof->annualized;
        const auto index = static_cast<std::size_t>(std::distance(vols.begin(), asof));
        if (index == 0) continue;
        const std::size_t begin = index > kThresholdLookback ? index - kThresholdLookback : 0;
        const std::size_t count = index - begin;  // Excludes today's as-of volatility observation.
        if (count < kMinimumThresholdObservations) continue;
        std::vector<double> history;
        history.reserve(count);
        for (std::size_t i = begin; i < index; ++i) history.push_back(vols[i].annualized);
        trade.threshold = quantile_nearest_rank(std::move(history), kHighVolQuantile);
        if (asof->annualized > *trade.threshold) {
            trade.regime = "high_vol";
            trade.multiplier = kHighVolExposure;
        } else {
            trade.regime = "normal_vol";
            trade.multiplier = 1.0;
        }
    }
}

struct Metrics {
    std::size_t n = 0;
    std::size_t classified = 0;
    std::size_t high = 0;
    double average_exposure = 0.0;
    double mean_monthly = 0.0;
    double annualized = 0.0;
    double sharpe = 0.0;
    double max_drawdown = 0.0;
    double turnover_factor = 0.0;
    double compounded = 1.0;
};

struct OutputPeriod {
    TradePeriod trade;
    bool flip = false;
    double base_turnover = 1.0;
    double controlled_turnover = 1.0;
    std::array<double, 2> base_net{};
    std::array<double, 2> controlled_net{};
};

double max_drawdown(const std::vector<double>& returns) {
    double wealth = 1.0, peak = 1.0, worst = 0.0;
    for (double value : returns) {
        wealth *= 1.0 + value;
        peak = std::max(peak, wealth);
        if (peak > 0.0) worst = std::min(worst, wealth / peak - 1.0);
    }
    return worst;
}

Metrics metrics(const std::vector<double>& returns, const std::vector<OutputPeriod>& periods,
                bool controlled) {
    Metrics result;
    result.n = returns.size();
    if (returns.empty()) return result;
    result.mean_monthly = std::accumulate(returns.begin(), returns.end(), 0.0) /
                          static_cast<double>(returns.size());
    double variance = 0.0;
    if (returns.size() > 1) {
        for (double value : returns) variance += (value - result.mean_monthly) * (value - result.mean_monthly);
        variance /= static_cast<double>(returns.size() - 1);
    }
    const double sd = std::sqrt(variance);
    result.sharpe = sd > 0.0 ? result.mean_monthly / sd * std::sqrt(12.0) : 0.0;
    result.compounded = std::accumulate(returns.begin(), returns.end(), 1.0,
        [](double wealth, double value) { return wealth * (1.0 + value); });
    if (result.compounded > 0.0)
        result.annualized = std::pow(result.compounded, 12.0 / static_cast<double>(returns.size())) - 1.0;
    result.max_drawdown = max_drawdown(returns);
    for (const auto& period : periods) {
        if (period.trade.regime != "warmup") ++result.classified;
        if (period.trade.regime == "high_vol") ++result.high;
        result.average_exposure += controlled ? period.trade.multiplier : 1.0;
        result.turnover_factor += controlled ? period.controlled_turnover : period.base_turnover;
    }
    result.average_exposure /= static_cast<double>(periods.size());
    result.turnover_factor /= static_cast<double>(periods.size());
    return result;
}

std::vector<OutputPeriod> calculate(std::vector<TradePeriod> trades) {
    std::vector<OutputPeriod> out;
    std::string previous_signal;
    std::string previous_position;
    double previous_multiplier = 1.0;
    for (const auto& trade : trades) {
        OutputPeriod row;
        row.trade = trade;
        const bool same_series = trade.signal == previous_signal;
        row.flip = same_series && trade.position != previous_position;
        row.base_turnover = 1.0 + (row.flip ? 1.0 : 0.0);
        const double prior_multiplier = same_series ? previous_multiplier : 1.0;
        // The base strategy charges one rebalance per leg and an extra unit on a direction flip.
        // Scale the regular rebalance by current exposure. Charge the overlay's size change, or
        // the average prior/current exposure for a direction flip, as additional per-leg turnover.
        double transition_extra = 0.0;
        if (same_series) {
            transition_extra = row.flip ? (prior_multiplier + trade.multiplier) / 2.0
                                        : std::abs(trade.multiplier - prior_multiplier);
        }
        row.controlled_turnover = trade.multiplier + transition_extra;
        for (std::size_t cost_case = 0; cost_case < 2; ++cost_case) {
            const double cost = kCostPerLeg * (cost_case == 0 ? 1.0 : 2.0);
            const double base_cost = 2.0 * cost * row.base_turnover;
            const double controlled_cost = 2.0 * cost * row.controlled_turnover;
            row.base_net[cost_case] = trade.gross - base_cost;
            row.controlled_net[cost_case] = trade.gross * trade.multiplier - controlled_cost;
        }
        out.push_back(row);
        previous_signal = trade.signal;
        previous_position = trade.position;
        previous_multiplier = trade.multiplier;
    }
    return out;
}

void write_outputs(const std::string& periods_path, const std::string& summary_path,
                   const std::vector<OutputPeriod>& all, bool force, const std::string& batch_hash) {
    auto safe_output = [&](const std::string& path) {
        if (path.empty()) throw std::runtime_error("output path must not be empty");
        std::ifstream probe(path);
        if (probe.good() && !force)
            throw std::runtime_error("refusing to overwrite " + path + "; pass --force deliberately");
    };
    safe_output(periods_path);
    safe_output(summary_path);
    if (periods_path == summary_path)
        throw std::runtime_error("period and summary outputs must be different files");

    std::ofstream periods(periods_path);
    if (!periods) throw std::runtime_error("cannot create period output: " + periods_path);
    periods << "vintage,signal,entry,exit,position,spy_asof,spy_vol_annualized,threshold_annualized,"
               "regime,exposure_multiplier,gross,base_net_10bps,base_net_20bps,"
               "controlled_net_10bps,controlled_net_20bps,spy_batch_sha256\n";
    periods << std::setprecision(12);
    for (const auto& row : all) {
        const auto& t = row.trade;
        periods << t.vintage << ',' << csv_escape(t.signal) << ',' << t.entry << ',' << t.exit << ','
                << csv_escape(t.position) << ',' << t.spy_asof << ','
                << format_optional(t.spy_vol) << ',' << format_optional(t.threshold) << ',' << t.regime << ','
                << t.multiplier << ',' << t.gross << ',' << row.base_net[0] << ',' << row.base_net[1]
                << ',' << row.controlled_net[0] << ',' << row.controlled_net[1] << ',' << batch_hash << '\n';
    }
    periods.close();
    if (!periods) throw std::runtime_error("failed while writing period output");

    std::ofstream summary(summary_path);
    if (!summary) throw std::runtime_error("cannot create summary output: " + summary_path);
    summary << "signal,policy,condition,cost_bps_per_leg,periods,classified_periods,high_vol_periods,"
               "average_exposure,mean_monthly_net,annualized_net,sharpe_monthly,max_drawdown,"
               "average_turnover_factor,compounded_net,spy_batch_sha256\n";
    summary << std::setprecision(12);
    std::map<std::string, std::vector<OutputPeriod>> by_signal;
    for (const auto& row : all) by_signal[row.trade.signal].push_back(row);
    for (const auto& [signal, rows] : by_signal) {
        for (bool controlled : {false, true}) {
            for (std::size_t cost_case = 0; cost_case < 2; ++cost_case) {
                for (const std::string condition : {"all", "normal_vol", "high_vol", "warmup"}) {
                    std::vector<OutputPeriod> subset;
                    std::vector<double> returns;
                    for (const auto& row : rows) {
                        if (condition != "all" && row.trade.regime != condition) continue;
                        subset.push_back(row);
                        returns.push_back(controlled ? row.controlled_net[cost_case] : row.base_net[cost_case]);
                    }
                    const Metrics m = metrics(returns, subset, controlled);
                    summary << csv_escape(signal) << ',' << (controlled ? "high_vol_half_exposure" : "unfiltered")
                            << ',' << condition << ',' << (cost_case == 0 ? 10 : 20) << ',' << m.n << ','
                            << m.classified << ',' << m.high << ',' << m.average_exposure << ',' << m.mean_monthly
                            << ',' << m.annualized << ',' << m.sharpe << ',' << m.max_drawdown << ','
                            << m.turnover_factor << ',' << m.compounded << ',' << batch_hash << '\n';
                }
            }
        }
    }
    summary.close();
    if (!summary) throw std::runtime_error("failed while writing summary output");
}

struct Args {
    std::string strategy;
    std::string bars;
    std::string periods;
    std::string summary;
    bool force = false;
};

Args parse_args(int argc, char** argv) {
    Args args;
    for (int i = 1; i < argc; ++i) {
        const std::string key = argv[i];
        if (key == "--force") { args.force = true; continue; }
        if (key == "--help" || key == "-h") {
            std::cout << "Usage: regime_risk_control --strategy capacity-strategy.csv --bars massive-bars.tsv "
                         "--out-periods periods.csv --out-summary summary.csv [--force]\n"
                         "Development only: vintage 2015-07 through 2022-09, with outcomes ending by "
                         "2022-09-30. Uses SPY 20-session realized volatility and its past-only "
                         "80th-percentile threshold over up to 252 prior observations; halves exposure "
                         "in high-volatility states.\n";
            std::exit(0);
        }
        if (i + 1 >= argc) throw std::runtime_error("missing value after " + key);
        const std::string value = argv[++i];
        if (key == "--strategy") args.strategy = value;
        else if (key == "--bars") args.bars = value;
        else if (key == "--out-periods") args.periods = value;
        else if (key == "--out-summary") args.summary = value;
        else throw std::runtime_error("unknown argument: " + key);
    }
    if (args.strategy.empty() || args.bars.empty() || args.periods.empty() || args.summary.empty())
        throw std::runtime_error("--strategy, --bars, --out-periods and --out-summary are required");
    if (args.periods == args.strategy || args.periods == args.bars ||
        args.summary == args.strategy || args.summary == args.bars)
        throw std::runtime_error("output files must not overwrite either input");
    return args;
}
}  // namespace

int main(int argc, char** argv) {
    try {
        const Args args = parse_args(argc, argv);
        auto trades = read_development_strategy(args.strategy);
        const auto latest_entry = std::max_element(trades.begin(), trades.end(),
            [](const auto& a, const auto& b) { return a.entry < b.entry; })->entry;
        std::string batch_hash;
        const auto bars = read_spy_bars(args.bars, latest_entry, batch_hash);
        const auto vols = realized_volatility(bars);
        classify_periods(trades, vols);
        const auto periods = calculate(std::move(trades));
        write_outputs(args.periods, args.summary, periods, args.force, batch_hash);
        std::cout << "wrote " << args.periods << " and " << args.summary << " from " << periods.size()
                  << " development rows; sealed outcomes were excluded by date fence\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "regime_risk_control: " << error.what() << '\n';
        return 2;
    }
}
