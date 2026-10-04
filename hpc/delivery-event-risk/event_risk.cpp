// Point-in-time event response and volatility-state summary.
// C++17, standard library only. This is a diagnostic, not a trading system.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
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

namespace fs = std::filesystem;
using Row = std::vector<std::string>;
namespace {
constexpr std::array<int, 5> kHorizons{1, 2, 5, 10, 20};
constexpr std::size_t kVolWindow = 20;
constexpr std::size_t kLookback = 252;
constexpr std::size_t kMinVolHistory = 126;
constexpr std::size_t kMinTailHistory = 252;
constexpr std::size_t kMinSurpriseHistory = 5;
constexpr double kPriceScale = 100000000.0;

std::string trim_cr(std::string s) {
    if (!s.empty() && s.back() == '\r') s.pop_back();
    return s;
}

Row split(const std::string& line, char delimiter) {
    Row fields;
    std::string value;
    bool quoted = false;
    for (std::size_t i = 0; i < line.size(); ++i) {
        const char c = line[i];
        if (c == '"') {
            if (quoted && i + 1 < line.size() && line[i + 1] == '"') {
                value.push_back('"');
                ++i;
            } else {
                quoted = !quoted;
            }
        } else if (c == delimiter && !quoted) {
            fields.push_back(value);
            value.clear();
        } else {
            value.push_back(c);
        }
    }
    if (quoted) throw std::runtime_error("unterminated quoted input field");
    fields.push_back(value);
    return fields;
}

std::map<std::string, std::size_t> columns(const Row& header) {
    std::map<std::string, std::size_t> result;
    for (std::size_t i = 0; i < header.size(); ++i)
        if (!result.emplace(header[i], i).second)
            throw std::runtime_error("duplicate input column: " + header[i]);
    return result;
}

std::string get(const Row& row, const std::map<std::string, std::size_t>& col,
                const std::string& name) {
    const auto it = col.find(name);
    if (it == col.end()) throw std::runtime_error("missing input column: " + name);
    if (it->second >= row.size()) throw std::runtime_error("short input row at: " + name);
    return row[it->second];
}

double numeric(const std::string& s, const std::string& label) {
    std::size_t used = 0;
    double value = 0;
    try { value = std::stod(s, &used); }
    catch (...) { throw std::runtime_error("invalid number in " + label); }
    if (used != s.size() || !std::isfinite(value))
        throw std::runtime_error("non-finite or malformed number in " + label);
    return value;
}

bool sha256(const std::string& s) {
    if (s.size() != 64) return false;
    return std::all_of(s.begin(), s.end(), [](unsigned char c) {
        return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
    });
}

bool leap(int y) { return y % 4 == 0 && (y % 100 != 0 || y % 400 == 0); }

std::string date_string(std::string s) {
    std::replace(s.begin(), s.end(), '.', '-');
    if (s.size() != 10 || s[4] != '-' || s[7] != '-')
        throw std::runtime_error("expected YYYY-MM-DD date");
    for (std::size_t i = 0; i < s.size(); ++i)
        if (i != 4 && i != 7 && (s[i] < '0' || s[i] > '9'))
            throw std::runtime_error("malformed calendar date");
    const int y = std::stoi(s.substr(0, 4));
    const int m = std::stoi(s.substr(5, 2));
    const int d = std::stoi(s.substr(8, 2));
    const std::array<int, 12> month_days{31,28,31,30,31,30,31,31,30,31,30,31};
    if (y < 1 || m < 1 || m > 12 || d < 1 ||
        d > month_days[m - 1] + (m == 2 && leap(y) ? 1 : 0))
        throw std::runtime_error("invalid calendar date");
    return s;
}

long long days_from_civil(int y, unsigned m, unsigned d) {
    y -= m <= 2;
    const int era = (y >= 0 ? y : y - 399) / 400;
    const unsigned yoe = static_cast<unsigned>(y - era * 400);
    const unsigned mp = m > 2 ? m - 3 : m + 9;
    const unsigned doy = (153 * mp + 2) / 5 + d - 1;
    const unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    return static_cast<long long>(era) * 146097 + static_cast<long long>(doe) - 719468;
}

long long timestamp_epoch(const std::string& s, const std::string& label) {
    if (s.size() < 20 || s[10] != 'T' || s[13] != ':' || s[16] != ':')
        throw std::runtime_error(label + " must be timezone-aware ISO-8601");
    const std::string day = date_string(s.substr(0, 10));
    const int hh = std::stoi(s.substr(11, 2));
    const int mm = std::stoi(s.substr(14, 2));
    const int ss = std::stoi(s.substr(17, 2));
    if (hh > 23 || mm > 59 || ss > 60)
        throw std::runtime_error("invalid time in " + label);
    int offset = 0;
    if (s.back() == 'Z') {
        offset = 0;
    } else {
        const auto sign_pos = s.find_last_of("+-");
        if (sign_pos == std::string::npos || sign_pos < 19 || s.size() - sign_pos != 6 ||
            s[sign_pos + 3] != ':')
            throw std::runtime_error(label + " must end in Z or a ±HH:MM offset");
        const int oh = std::stoi(s.substr(sign_pos + 1, 2));
        const int om = std::stoi(s.substr(sign_pos + 4, 2));
        if (oh > 23 || om > 59) throw std::runtime_error("invalid timezone offset in " + label);
        offset = (oh * 60 + om) * 60 * (s[sign_pos] == '+' ? 1 : -1);
    }
    return days_from_civil(std::stoi(day.substr(0, 4)),
                           static_cast<unsigned>(std::stoi(day.substr(5, 2))),
                           static_cast<unsigned>(std::stoi(day.substr(8, 2)))) * 86400LL +
           hh * 3600LL + mm * 60LL + ss - offset;
}

std::string utc_day(const std::string& timestamp) {
    (void)timestamp_epoch(timestamp, "available_at_utc");
    return date_string(timestamp.substr(0, 10));
}

std::string csv(const std::string& s) {
    if (s.find_first_of(",\"\r\n") == std::string::npos) return s;
    std::string out = "\"";
    for (char c : s) { if (c == '"') out.push_back('"'); out.push_back(c); }
    return out + '"';
}

std::string fmt(const std::optional<double>& x) {
    if (!x || !std::isfinite(*x)) return "";
    std::ostringstream out;
    out << std::setprecision(12) << *x;
    return out.str();
}

double quantile(std::vector<double> values, double q) {
    if (values.empty()) throw std::runtime_error("quantile of empty sample");
    std::sort(values.begin(), values.end());
    const double pos = q * static_cast<double>(values.size() - 1);
    const auto lo = static_cast<std::size_t>(std::floor(pos));
    const auto hi = static_cast<std::size_t>(std::ceil(pos));
    const double weight = pos - static_cast<double>(lo);
    return values[lo] * (1.0 - weight) + values[hi] * weight;
}

struct Bar { std::string date; double close = 0; double volume = 0; };
using Series = std::map<std::string, std::vector<Bar>>;

Series read_bars(const fs::path& path, const std::string& sealed_start,
                 std::set<std::string>& source_batches) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("cannot open bars TSV");
    std::string line;
    if (!std::getline(in, line)) throw std::runtime_error("empty bars TSV");
    const auto col = columns(split(trim_cr(line), '\t'));
    for (const auto* key : {"date", "sym", "source_id", "batch_sha256", "close_px_e8usd", "volume", "row_sha256"})
        if (!col.count(key)) throw std::runtime_error(std::string("bars TSV missing column: ") + key);
    Series result;
    std::map<std::string, std::pair<std::string, std::string>> provenance;
    std::set<std::pair<std::string, std::string>> keys;
    while (std::getline(in, line)) {
        line = trim_cr(line);
        if (line.empty()) continue;
        const auto row = split(line, '\t');
        const std::string date = date_string(get(row, col, "date"));
        // Do not parse any price or volume at or beyond the sealed cutoff.
        if (date >= sealed_start)
            throw std::runtime_error("bars input contains a sealed-date row; stage a development-only prefix");
        const std::string sym = get(row, col, "sym");
        const std::string source = get(row, col, "source_id");
        const std::string batch = get(row, col, "batch_sha256");
        if (sym.empty() || source.empty() || !sha256(batch) || !sha256(get(row, col, "row_sha256")))
            throw std::runtime_error("invalid bar identity or provenance");
        const auto origin = std::make_pair(source, batch);
        auto [it, inserted] = provenance.emplace(sym, origin);
        if (!inserted && it->second != origin)
            throw std::runtime_error("mixed source batches for symbol " + sym);
        if (!keys.emplace(sym, date).second)
            throw std::runtime_error("duplicate symbol/date bar for " + sym + "/" + date);
        const std::string scaled_text = get(row, col, "close_px_e8usd");
        std::size_t parsed_chars = 0;
        const long long scaled = std::stoll(scaled_text, &parsed_chars);
        if (parsed_chars != scaled_text.size())
            throw std::runtime_error("bar close_px_e8usd must be an integer");
        if (scaled <= 0) throw std::runtime_error("bar close must be positive");
        const double volume = numeric(get(row, col, "volume"), "bar volume");
        if (volume < 0 || std::floor(volume) != volume)
            throw std::runtime_error("bar volume must be a nonnegative integer");
        result[sym].push_back({date, static_cast<double>(scaled) / kPriceScale, volume});
    }
    for (auto& item : result) {
        std::sort(item.second.begin(), item.second.end(), [](const Bar& a, const Bar& b) { return a.date < b.date; });
        for (std::size_t i = 1; i < item.second.size(); ++i)
            if (item.second[i - 1].date >= item.second[i].date)
                throw std::runtime_error("bar dates must increase strictly");
    }
    for (const auto& item : provenance) source_batches.insert(item.first + ":" + item.second.first + ":" + item.second.second);
    if (!result.count("SPY")) throw std::runtime_error("bars must contain SPY");
    return result;
}

std::optional<double> realized_vol(const std::vector<Bar>& bars, std::size_t end,
                                   std::size_t window = kVolWindow) {
    if (end < window || end >= bars.size()) return std::nullopt;
    std::vector<double> returns;
    returns.reserve(window);
    for (std::size_t i = end - window + 1; i <= end; ++i)
        returns.push_back(std::log(bars[i].close / bars[i - 1].close));
    const double mean = std::accumulate(returns.begin(), returns.end(), 0.0) / returns.size();
    double ss = 0;
    for (double r : returns) ss += (r - mean) * (r - mean);
    const double variance = ss / static_cast<double>(returns.size() - 1);
    return std::sqrt(variance * 252.0);
}

std::optional<double> daily_return(const std::vector<Bar>& bars, std::size_t end) {
    if (end == 0 || end >= bars.size()) return std::nullopt;
    return bars[end].close / bars[end - 1].close - 1.0;
}

std::optional<double> trailing_quantile(const std::vector<Bar>& bars, std::size_t end,
                                        std::size_t window, double q) {
    if (end < window) return std::nullopt;
    std::vector<double> values;
    for (std::size_t i = end - window + 1; i <= end; ++i) {
        auto r = daily_return(bars, i);
        if (r) values.push_back(*r);
    }
    if (values.size() != window) return std::nullopt;
    return quantile(std::move(values), q);
}

std::optional<std::size_t> asof_index(const std::vector<Bar>& bars, const std::string& event_day) {
    auto it = std::lower_bound(bars.begin(), bars.end(), event_day,
                               [](const Bar& bar, const std::string& day) { return bar.date < day; });
    if (it == bars.begin()) return std::nullopt;
    return static_cast<std::size_t>(std::distance(bars.begin(), it) - 1);
}

std::optional<std::size_t> entry_index(const std::vector<Bar>& bars, const std::string& event_day) {
    auto it = std::upper_bound(bars.begin(), bars.end(), event_day,
                               [](const std::string& day, const Bar& bar) { return day < bar.date; });
    if (it == bars.end()) return std::nullopt;
    return static_cast<std::size_t>(std::distance(bars.begin(), it));
}

std::optional<double> window_return(const std::vector<Bar>& bars, const std::string& event_day,
                                    int horizon, std::string& entry, std::string& exit,
                                    const std::string& sealed_start) {
    auto start = entry_index(bars, event_day);
    if (!start || *start + static_cast<std::size_t>(horizon) >= bars.size()) return std::nullopt;
    const std::size_t end = *start + static_cast<std::size_t>(horizon);
    entry = bars[*start].date;
    exit = bars[end].date;
    if (exit >= sealed_start) return std::nullopt;
    return bars[end].close / bars[*start].close - 1.0;
}

struct Event {
    std::string id, cluster, ticker, metric, unit, available, event_day, sector, expectation_type;
    std::string eligibility = "eligible", asof = "", vol_regime = "warmup", tail_state = "unknown";
    double surprise = 0;
    std::optional<double> surprise_z, issuer_vol, market_vol, vol_threshold;
    std::optional<double> long_cost10, short_cost10, long_cost20, short_cost20;
    std::map<int, std::optional<double>> stock, market, market_abnormal, sector_return;
    std::map<int, std::string> entry, exit;
};

std::vector<Event> read_events(const fs::path& path, const std::string& development_start,
                               const std::string& sealed_start, std::size_t& skipped_outside) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("cannot open events CSV");
    std::string line;
    if (!std::getline(in, line)) throw std::runtime_error("empty events CSV");
    const auto col = columns(split(trim_cr(line), ','));
    for (const auto* key : {"event_id", "event_cluster_id", "ticker", "metric_key", "unit", "available_at_utc",
        "expectation_available_at_utc", "expectation_type", "prior_expectation", "current_value", "review_status",
        "exposure_status", "sector_symbol", "document_sha256", "in_sealed_window"})
        if (!col.count(key)) throw std::runtime_error(std::string("events CSV missing column: ") + key);
    std::vector<Event> result;
    std::set<std::string> ids;
    while (std::getline(in, line)) {
        line = trim_cr(line);
        if (line.empty()) continue;
        const auto row = split(line, ',');
        const std::string sealed = get(row, col, "in_sealed_window");
        if (sealed == "true" || sealed == "1" || sealed == "TRUE")
            throw std::runtime_error("events input contains a sealed row; stage development events only");
        const std::string available = get(row, col, "available_at_utc");
        const std::string day = utc_day(available);
        if (day >= sealed_start)
            throw std::runtime_error("events input contains a sealed-date row; stage development events only");
        if (day < development_start) { ++skipped_outside; continue; }
        Event event;
        for (int horizon : kHorizons) {
            event.entry[horizon] = "";
            event.exit[horizon] = "";
            event.stock[horizon] = std::nullopt;
            event.market[horizon] = std::nullopt;
            event.market_abnormal[horizon] = std::nullopt;
            event.sector_return[horizon] = std::nullopt;
        }
        event.id = get(row, col, "event_id");
        if (event.id.empty() || !ids.insert(event.id).second)
            throw std::runtime_error("event IDs must be nonempty and unique");
        event.cluster = get(row, col, "event_cluster_id");
        event.ticker = get(row, col, "ticker");
        event.metric = get(row, col, "metric_key");
        event.unit = get(row, col, "unit");
        event.available = available;
        event.event_day = day;
        event.sector = get(row, col, "sector_symbol");
        event.expectation_type = get(row, col, "expectation_type");
        const std::string expectation_at = get(row, col, "expectation_available_at_utc");
        if (event.cluster.empty()) event.eligibility = "missing_event_cluster";
        else if (event.ticker.empty() || event.metric.empty() || event.unit.empty()) event.eligibility = "missing_identity_or_unit";
        else if (get(row, col, "review_status") != "reviewed") event.eligibility = "not_reviewed";
        else if (get(row, col, "exposure_status") != "verified") event.eligibility = "exposure_not_verified";
        else if (event.expectation_type != "management_guidance") event.eligibility = "unsupported_expectation_type";
        else if (!sha256(get(row, col, "document_sha256"))) event.eligibility = "invalid_document_sha256";
        else if (timestamp_epoch(expectation_at, "expectation_available_at_utc") >
                 timestamp_epoch(available, "available_at_utc")) event.eligibility = "expectation_not_yet_public";
        if (event.eligibility == "eligible" &&
            (get(row, col, "prior_expectation").empty() || get(row, col, "current_value").empty()))
            event.eligibility = "missing_comparable_expectation_value";
        if (event.eligibility == "eligible" && expectation_at.empty())
            event.eligibility = "missing_expectation_availability";
        if (event.eligibility == "eligible") {
            event.surprise = numeric(get(row, col, "current_value"), "current_value") -
                             numeric(get(row, col, "prior_expectation"), "prior_expectation");
        }
        result.push_back(std::move(event));
    }
    std::stable_sort(result.begin(), result.end(), [](const Event& a, const Event& b) {
        return std::make_pair(timestamp_epoch(a.available, "available_at_utc"), a.id) <
               std::make_pair(timestamp_epoch(b.available, "available_at_utc"), b.id);
    });
    return result;
}

std::optional<double> robust_z(double x, const std::vector<double>& history) {
    if (history.size() < kMinSurpriseHistory) return std::nullopt;
    const double med = quantile(history, 0.5);
    std::vector<double> deviations;
    for (double h : history) deviations.push_back(std::abs(h - med));
    const double mad = quantile(std::move(deviations), 0.5);
    if (mad <= std::numeric_limits<double>::epsilon()) return std::nullopt;
    return (x - med) / (1.4826 * mad);
}

void attach_states(std::vector<Event>& events, const Series& bars) {
    const auto& market = bars.at("SPY");
    std::map<std::tuple<std::string, std::string, std::string>, std::vector<double>> history;
    std::map<std::tuple<std::string, std::string, std::string>, std::set<std::string>> clusters;
    for (auto& event : events) {
        if (event.eligibility != "eligible") continue;
        const auto key = std::make_tuple(event.ticker, event.metric, event.unit);
        const bool new_cluster = clusters[key].insert(event.cluster).second;
        if (new_cluster) event.surprise_z = robust_z(event.surprise, history[key]);
        auto mkt_idx = asof_index(market, event.event_day);
        if (mkt_idx) {
            event.asof = market[*mkt_idx].date;
            event.market_vol = realized_vol(market, *mkt_idx);
            std::vector<double> prior_vol;
            const std::size_t begin = *mkt_idx > kLookback ? *mkt_idx - kLookback : 0;
            for (std::size_t i = begin; i < *mkt_idx; ++i) {
                auto v = realized_vol(market, i);
                if (v) prior_vol.push_back(*v);
            }
            if (event.market_vol && prior_vol.size() >= kMinVolHistory) {
                event.vol_threshold = quantile(std::move(prior_vol), 0.80);
                event.vol_regime = *event.market_vol > *event.vol_threshold ? "high_vol" : "normal_vol";
            }
            auto shock_cut = *mkt_idx > 0 ? trailing_quantile(market, *mkt_idx - 1, kMinTailHistory, 0.01)
                                           : std::nullopt;
            auto prior_day_return = daily_return(market, *mkt_idx);
            if (shock_cut && prior_day_return)
                event.tail_state = *prior_day_return <= *shock_cut ? "tail_shock" : "no_tail_shock";
        }
        const auto issuer = bars.find(event.ticker);
        if (issuer != bars.end()) {
            auto idx = asof_index(issuer->second, event.event_day);
            if (idx) event.issuer_vol = realized_vol(issuer->second, *idx);
        }
        if (new_cluster) history[key].push_back(event.surprise);
    }
}

void attach_outcomes(std::vector<Event>& events, const Series& bars, double cost_bps,
                     const std::string& sealed_start) {
    const double one_round_trip = 2.0 * cost_bps / 10000.0;
    for (auto& event : events) {
        if (event.eligibility != "eligible") continue;
        auto stock = bars.find(event.ticker);
        auto market = bars.find("SPY");
        if (stock == bars.end()) { event.eligibility = "missing_ticker_bars"; continue; }
        for (int horizon : kHorizons) {
            std::string stock_entry, stock_exit, market_entry, market_exit;
            auto sr = window_return(stock->second, event.event_day, horizon, stock_entry, stock_exit, sealed_start);
            auto mr = window_return(market->second, event.event_day, horizon, market_entry, market_exit, sealed_start);
            event.entry[horizon] = stock_entry;
            event.exit[horizon] = stock_exit;
            event.stock[horizon] = sr;
            event.market[horizon] = mr;
            if (sr && mr) event.market_abnormal[horizon] = *sr - *mr;
            auto sector = event.sector.empty() ? bars.end() : bars.find(event.sector);
            if (sector != bars.end()) {
                std::string sector_entry, sector_exit;
                auto rr = window_return(sector->second, event.event_day, horizon, sector_entry, sector_exit, sealed_start);
                if (sr && rr) event.sector_return[horizon] = *sr - *rr;
            }
        }
        // Both long and short stock sensitivities are displayed; neither is selected as a strategy.
        const int h = 5;
        if (event.stock[h]) {
            event.long_cost10 = *event.stock[h] - one_round_trip;
            event.short_cost10 = -*event.stock[h] - one_round_trip;
            event.long_cost20 = *event.stock[h] - 2.0 * one_round_trip;
            event.short_cost20 = -*event.stock[h] - 2.0 * one_round_trip;
        }
    }
}

void write_events(const fs::path& path, const std::vector<Event>& events) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("cannot write event outcomes");
    out << "event_id,event_cluster_id,ticker,metric_key,unit,available_at_utc,eligibility,expectation_type,surprise,surprise_z,asof_session,issuer_vol20_ann,spy_vol20_ann,high_vol_threshold_ann,vol_regime,tail_state,sector_symbol";
    for (int h : kHorizons) out << ",entry_" << h << ",exit_" << h << ",stock_return_" << h << ",market_return_" << h << ",market_abnormal_" << h << ",sector_abnormal_" << h;
    out << ",long_stock_net_5s_configured_cost,short_stock_net_5s_configured_cost,long_stock_net_5s_double_cost,short_stock_net_5s_double_cost\n";
    for (const auto& e : events) {
        out << csv(e.id) << ',' << csv(e.cluster) << ',' << csv(e.ticker) << ',' << csv(e.metric) << ',' << csv(e.unit) << ','
            << csv(e.available) << ',' << e.eligibility << ',' << csv(e.expectation_type) << ',' << fmt(e.eligibility == "eligible" ? std::optional<double>(e.surprise) : std::nullopt) << ','
            << fmt(e.surprise_z) << ',' << e.asof << ',' << fmt(e.issuer_vol) << ',' << fmt(e.market_vol) << ',' << fmt(e.vol_threshold) << ','
            << e.vol_regime << ',' << e.tail_state << ',' << csv(e.sector);
        for (int h : kHorizons) out << ',' << e.entry.at(h) << ',' << e.exit.at(h) << ',' << fmt(e.stock.at(h)) << ','
                                   << fmt(e.market.at(h)) << ',' << fmt(e.market_abnormal.at(h)) << ',' << fmt(e.sector_return.at(h));
        out << ',' << fmt(e.long_cost10) << ',' << fmt(e.short_cost10) << ',' << fmt(e.long_cost20) << ',' << fmt(e.short_cost20) << '\n';
    }
}

struct Obs { double value; std::string cluster; };
std::pair<double, double> center_tail(const std::vector<double>& x) {
    const double p = quantile(x, 0.05);
    std::vector<double> tail;
    for (double v : x) if (v <= p) tail.push_back(v);
    const double es = std::accumulate(tail.begin(), tail.end(), 0.0) / tail.size();
    return {p, es};
}

void write_summary(const fs::path& path, const std::vector<Event>& events) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("cannot write regime summary");
    out << "state,horizon,measure,event_count,independent_clusters,mean,median,p05,es05\n";
    const std::array<std::string, 7> states{"all", "high_vol", "normal_vol", "warmup", "tail_shock", "no_tail_shock", "unknown"};
    for (const auto& state : states) for (int h : kHorizons) {
        for (const auto& measure : {std::string("stock_return"), std::string("market_abnormal"),
                                    std::string("sector_abnormal")}) {
            std::vector<double> cluster_means;
            std::map<std::string, std::vector<double>> by_cluster;
            std::size_t event_count = 0;
            for (const auto& e : events) {
                if (e.eligibility != "eligible") continue;
                if (state != "all" && state != e.vol_regime && state != e.tail_state) continue;
                std::optional<double> v;
                if (measure == "stock_return") v = e.stock.at(h);
                else if (measure == "market_abnormal") v = e.market_abnormal.at(h);
                else v = e.sector_return.at(h);
                if (v) { by_cluster[e.cluster].push_back(*v); ++event_count; }
            }
            for (const auto& [cluster, cluster_values] : by_cluster) {
                (void)cluster;
                cluster_means.push_back(std::accumulate(cluster_values.begin(), cluster_values.end(), 0.0) /
                                        cluster_values.size());
            }
            out << state << ',' << h << ',' << measure << ',' << event_count << ',' << by_cluster.size();
            if (cluster_means.empty()) { out << ",,,,\n"; continue; }
            const double mean = std::accumulate(cluster_means.begin(), cluster_means.end(), 0.0) / cluster_means.size();
            const double med = quantile(cluster_means, 0.5);
            const auto [p05, es05] = center_tail(cluster_means);
            out << ',' << fmt(mean) << ',' << fmt(med) << ',' << fmt(p05) << ',' << fmt(es05) << '\n';
        }
    }
}

void write_associations(const fs::path& path, const std::vector<Event>& events) {
    std::ofstream out(path);
    if (!out) throw std::runtime_error("cannot write surprise association summary");
    out << "state,horizon,outcome,event_count,independent_clusters,pearson_r\n";
    const std::array<std::string, 6> states{"all", "high_vol", "normal_vol", "tail_shock", "no_tail_shock", "unknown"};
    for (const auto& state : states) for (int h : kHorizons) {
        for (const auto& name : {std::string("market_abnormal"), std::string("sector_abnormal")}) {
            std::map<std::string, std::pair<std::vector<double>, std::vector<double>>> by_cluster;
            for (const auto& e : events) {
                if (e.eligibility != "eligible" || !e.surprise_z) continue;
                if (state != "all" && state != e.vol_regime && state != e.tail_state) continue;
                const auto outcome = name == "market_abnormal" ? e.market_abnormal.at(h) : e.sector_return.at(h);
                if (!outcome) continue;
                by_cluster[e.cluster].first.push_back(*e.surprise_z);
                by_cluster[e.cluster].second.push_back(*outcome);
            }
            std::vector<double> x, y;
            for (const auto& [cluster, values] : by_cluster) {
                (void)cluster;
                x.push_back(std::accumulate(values.first.begin(), values.first.end(), 0.0) / values.first.size());
                y.push_back(std::accumulate(values.second.begin(), values.second.end(), 0.0) / values.second.size());
            }
            out << state << ',' << h << ',' << name << ',' << x.size() << ',' << by_cluster.size() << ',';
            if (x.size() < 3) { out << '\n'; continue; }
            const double mx = std::accumulate(x.begin(), x.end(), 0.0) / x.size();
            const double my = std::accumulate(y.begin(), y.end(), 0.0) / y.size();
            double covariance = 0.0, vx = 0.0, vy = 0.0;
            for (std::size_t i = 0; i < x.size(); ++i) {
                covariance += (x[i] - mx) * (y[i] - my);
                vx += (x[i] - mx) * (x[i] - mx);
                vy += (y[i] - my) * (y[i] - my);
            }
            if (vx <= 0 || vy <= 0) out << '\n';
            else out << fmt(covariance / std::sqrt(vx * vy)) << '\n';
        }
    }
}

void write_report(const fs::path& path, const std::vector<Event>& events,
                  std::size_t skipped_outside, const std::string& development_start,
                  const std::string& sealed_start, double cost_bps,
                  const std::set<std::string>& sources) {
    std::size_t eligible = 0, excluded = 0, high = 0, tail = 0;
    std::set<std::string> clusters;
    for (const auto& e : events) {
        if (e.eligibility == "eligible") { ++eligible; clusters.insert(e.cluster); if (e.vol_regime == "high_vol") ++high; if (e.tail_state == "tail_shock") ++tail; }
        else ++excluded;
    }
    std::ofstream out(path);
    if (!out) throw std::runtime_error("cannot write report");
    out << "# Delivery revision event risk\n\n"
        << "Generated by the C++17 HiPerGator runner. This is a development diagnostic, not a trading result.\n\n"
        << "## Coverage\n\n"
        << "- Development availability-date window: " << development_start << " through the day before " << sealed_start << ".\n"
        << "- Sealed rows admitted to the run: 0; inputs containing sealed rows are rejected before outcomes are calculated.\n"
        << "- Rows outside the development date window: " << skipped_outside << ".\n"
        << "- Rows retained: " << events.size() << "; eligible: " << eligible << "; excluded by review, exposure, or expectation gate: " << excluded << ".\n"
        << "- Eligible independent event clusters: " << clusters.size() << "; high-vol events: " << high << "; prior-session tail-shock events: " << tail << ".\n\n"
        << "## Interpretation limits\n\n"
        << "- High volatility is a past-only SPY 20-session realized-volatility state, above the prior 80th percentile when 126 prior estimates exist.\n"
        << "- Tail shock means the prior completed SPY session return was at or below its past 252-session 1st percentile. It does not forecast rare events.\n"
        << "- The report includes every predeclared horizon (1, 2, 5, 10, and 20 sessions). It does not select a best horizon.\n"
        << "- Five-session long/short stock-return costs are shown at " << cost_bps << " bps per execution side and doubled. These are sensitivity assumptions, not measured spreads; short borrow is excluded.\n"
        << "- `regime-summary.csv` reports mean, median, 5th percentile, and lower-tail mean. Small cluster counts make tail summaries descriptive only.\n"
        << "- `surprise-association.csv` reports unadjusted Pearson associations between past-only robust surprise scores and subsequent benchmark-adjusted returns; it is descriptive, not causal evidence.\n"
        << "- Market and sector adjusted returns are diagnostics, not executable hedge P&L. Missing sector inputs remain missing.\n"
        << "- Input bar batches used:\n";
    for (const auto& s : sources) out << "  - " << s << "\n";
    if (eligible < 20 || clusters.size() < 20)
        out << "\n**Sample warning:** fewer than 20 eligible events or independent clusters; do not infer reliable regime-specific tail probabilities.\n";
}

int main_impl(int argc, char** argv) {
    std::map<std::string, std::string> args;
    for (int i = 1; i < argc; ++i) {
        std::string key = argv[i];
        if (key == "--help" || key == "-h") {
            std::cout << "Usage: event_risk --events CSV --bars TSV --development-start YYYY-MM-DD --sealed-start YYYY-MM-DD --output NEW_DIR [--cost-bps-per-side 10]\n";
            return 0;
        }
        if (key.rfind("--", 0) != 0 || i + 1 >= argc) throw std::runtime_error("expected --name value arguments; use --help");
        args[key] = argv[++i];
    }
    for (const auto* key : {"--events", "--bars", "--development-start", "--sealed-start", "--output"})
        if (!args.count(key)) throw std::runtime_error(std::string("required argument missing: ") + key);
    const std::string dev_start = date_string(args.at("--development-start"));
    const std::string sealed_start = date_string(args.at("--sealed-start"));
    if (dev_start >= sealed_start) throw std::runtime_error("development start must precede sealed start");
    double cost_bps = args.count("--cost-bps-per-side") ? numeric(args.at("--cost-bps-per-side"), "cost bps") : 10.0;
    if (cost_bps < 0 || cost_bps > 1000) throw std::runtime_error("cost bps per side must be between 0 and 1000");
    std::size_t skipped_outside = 0;
    auto events = read_events(args.at("--events"), dev_start, sealed_start, skipped_outside);
    std::set<std::string> sources;
    auto bars = read_bars(args.at("--bars"), sealed_start, sources);
    attach_states(events, bars);
    attach_outcomes(events, bars, cost_bps, sealed_start);
    const fs::path output(args.at("--output"));
    if (fs::exists(output)) throw std::runtime_error("refusing to overwrite existing output directory");
    if (!fs::create_directories(output)) throw std::runtime_error("cannot create output directory");
    write_events(output / "event-outcomes.csv", events);
    write_summary(output / "regime-summary.csv", events);
    write_associations(output / "surprise-association.csv", events);
    write_report(output / "report.md", events, skipped_outside, dev_start, sealed_start, cost_bps, sources);
    std::ofstream meta(output / "run-metadata.json");
    if (!meta) throw std::runtime_error("cannot write metadata");
    meta << "{\n  \"software\": \"delivery-event-risk-cxx17\",\n  \"study_role\": \"development\",\n"
         << "  \"development_start\": \"" << dev_start << "\",\n  \"sealed_start\": \"" << sealed_start << "\",\n"
         << "  \"cost_bps_per_execution_side\": " << cost_bps
         << ",\n  \"sealed_rows_admitted\": 0,\n  \"skipped_outside_events\": " << skipped_outside << ",\n  \"event_rows_written\": " << events.size()
         << ",\n  \"bar_batches\": [";
    bool first = true;
    for (const auto& s : sources) { if (!first) meta << ','; first = false; meta << "\n    \"" << s << "\""; }
    if (!sources.empty()) meta << '\n';
    meta << "  ]\n}\n";
    std::cout << "wrote " << (output / "report.md") << " with " << events.size() << " in-window event rows\n";
    return 0;
}
} // namespace

int main(int argc, char** argv) {
    try { return main_impl(argc, argv); }
    catch (const std::exception& e) { std::cerr << "event_risk: " << e.what() << '\n'; return 2; }
}
