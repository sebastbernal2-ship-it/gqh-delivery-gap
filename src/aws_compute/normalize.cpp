#include <array>
#include <cassert>
#include <ctime>
#include <iomanip>
#include <iostream>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

static bool starts(const std::string& s, const std::string& p) {
  return s.compare(0, p.size(), p) == 0;
}
static bool selected(const std::string& zone, const std::string& sku,
                     const std::string& os) {
  if (os != "Linux/UNIX" || !(starts(zone, "use1-") || starts(zone, "usw2-"))) return false;
  for (const auto& prefix : {"p3.","p3dn.","p4d.","p4de.","p5.","p5e.","p5en.",
                             "p6.","p6e.","p6-b200.","p6-b300.",
                             "g3.","g3s.","g4dn.","g4ad.","g5.","g5g.","g6.","g6e.","g6f."})
    if (starts(sku, prefix)) return true;
  return false;
}
static bool price_valid(const std::string& s) {
  static const std::regex r("[0-9]{1,15}(\\.[0-9]{1,9})?");
  return std::regex_match(s, r);
}
static std::string quoted(const std::string& s) {
  std::string out = "\"";
  for (char c : s) { if (c == '"') out += '"'; out += c; }
  return out + '"';
}
static std::array<std::string,5> split(const std::string& line) {
  std::array<std::string,5> f;
  size_t a = 0;
  for (size_t i=0;i<4;++i) {
    size_t b=line.find('\t',a);
    if (b==std::string::npos) throw std::runtime_error("expected five TSV fields");
    f[i]=line.substr(a,b-a);a=b+1;
  }
  if (line.find('\t',a)!=std::string::npos) throw std::runtime_error("extra TSV field");
  f[4]=line.substr(a);return f;
}
int main(int argc,char** argv) {
  if (argc==2 && std::string(argv[1])=="--test") {
    assert(price_valid("0.000001"));assert(price_valid("71.113800"));
    assert(!price_valid("nan"));assert(!price_valid("1e-6"));assert(!price_valid("-1"));
    assert(!price_valid("1.0000000001"));assert(!price_valid("1."));
    assert(quoted("a\"b")=="\"a\"\"b\"");
    assert(selected("use1-az1","p4d.24xlarge","Linux/UNIX"));
    assert(!selected("euw1-az1","p4d.24xlarge","Linux/UNIX"));
    assert(!selected("use1-az1","m5.large","Linux/UNIX"));
    assert(!selected("use1-az1","p4d.24xlarge","Windows"));
    assert(split("z\ts\to\tp\tt")[4]=="t");
    bool caught=false;try { split("a\tb"); } catch (...) {caught=true;}assert(caught);
    std::cerr << "normalizer tests passed\n";return 0;
  }
  if (argc!=3) {std::cerr<<"usage: normalize source_file source_md5\n";return 2;}
  const std::regex timestamp("[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})");
  unsigned long long total=0,kept=0;
  const auto now = std::time(nullptr);
  std::tm utc = *std::gmtime(&now);
  std::ostringstream timestamp_out;
  timestamp_out << std::put_time(&utc, "%Y-%m-%dT%H:%M:%SZ");
  const std::string ingested_at = timestamp_out.str();
  std::cout<<"price_time,zone_id,instance_type,operating_system,usd_per_instance_hour,source_file,source_doi,source_md5,license,ingested_at\n";
  try {
    std::string line;
    while (std::getline(std::cin,line)) {
      ++total;if (!line.empty() && line.back()=='\r') line.pop_back();
      auto f=split(line);if (!selected(f[0],f[1],f[2])) continue;
      if (!price_valid(f[3]) || !std::regex_match(f[4],timestamp))
        throw std::runtime_error("invalid retained price or timestamp");
      std::cout<<quoted(f[4])<<','<<quoted(f[0])<<','<<quoted(f[1])<<','<<quoted(f[2])<<','
        <<quoted(f[3])<<','<<quoted(argv[1])<<",10.5281/zenodo.23082767,"<<quoted(argv[2])<<",CC-BY-4.0,"<<quoted(ingested_at)<<'\n';
      ++kept;
    }
    if (std::cin.bad() || !std::cout.good()) throw std::runtime_error("stream I/O failure");
    std::cerr<<argv[1]<<": scanned="<<total<<" retained="<<kept<<'\n';
  } catch (const std::exception& e) {
    std::cerr<<"FAIL at input line "<<total<<": "<<e.what()<<'\n';return 1;
  }
}
