// Hidden verifier for task-003: StreamWriterBuilder["precisionMode"].
#include <json/json.h>

#include <cmath>
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

namespace {

int g_failures = 0;

void check(bool cond, const std::string& what) {
  if (!cond) {
    ++g_failures;
    std::cout << "FAIL: " << what << "\n";
  }
}

std::string write(const Json::Value& v, const char* mode, unsigned precision = 17,
                  const char* precisionType = "significant",
                  bool specialFloats = false) {
  Json::StreamWriterBuilder builder;
  builder["precisionMode"] = mode;
  builder["precision"] = precision;
  builder["precisionType"] = precisionType;
  builder["useSpecialFloats"] = specialFloats;
  builder["indentation"] = "";
  return Json::writeString(builder, v);
}

double parseDouble(const std::string& text, bool* ok) {
  Json::CharReaderBuilder builder;
  Json::Value root;
  std::string errs;
  std::unique_ptr<Json::CharReader> reader(builder.newCharReader());
  *ok = reader->parse(text.data(), text.data() + text.size(), &root, &errs);
  return *ok ? root.asDouble() : 0.0;
}

void expectText(const Json::Value& v, const char* mode, const std::string& want,
                unsigned precision = 17, const char* precisionType = "significant",
                bool specialFloats = false) {
  const std::string got =
      write(v, mode, precision, precisionType, specialFloats);
  check(got == want, std::string("mode=") + mode + " want=" + want +
                         " got=" + got);
}

} // namespace

int main() {
  Json::StreamWriterBuilder probe;
  check(probe.settings_.isMember("precisionMode"),
        "StreamWriterBuilder exposes a precisionMode setting");
  check(probe.settings_["precisionMode"].asString() == "fixed",
        "precisionMode defaults to fixed");

  // Backward compatibility: fixed mode is byte-for-byte unchanged.
  expectText(Json::Value(0.1), "fixed", "0.10000000000000001");
  expectText(Json::Value(0.1 + 0.2), "fixed", "0.30000000000000004");
  expectText(Json::Value(1.0 / 3.0), "fixed", "0.33333333333333331");
  expectText(Json::Value(1e-7), "fixed", "9.9999999999999995e-08");

  // Shortest round-trip output.
  expectText(Json::Value(0.1), "roundTrip", "0.1");
  expectText(Json::Value(0.2), "roundTrip", "0.2");
  expectText(Json::Value(0.1 + 0.2), "roundTrip", "0.30000000000000004");
  expectText(Json::Value(1.0 / 3.0), "roundTrip", "0.3333333333333333");
  expectText(Json::Value(1.0), "roundTrip", "1.0");
  expectText(Json::Value(100.0), "roundTrip", "100.0");
  expectText(Json::Value(-0.0), "roundTrip", "-0.0");
  expectText(Json::Value(1e-7), "roundTrip", "1e-07");
  expectText(Json::Value(1e20), "roundTrip", "1e+20");
  expectText(Json::Value(9007199254740992.0), "roundTrip", "9007199254740992.0");
  expectText(Json::Value(3.141592653589793), "roundTrip", "3.141592653589793");

  // precision is ignored in roundTrip mode, but still honored in fixed mode.
  expectText(Json::Value(1.0 / 3.0), "roundTrip", "0.3333333333333333", 3);
  expectText(Json::Value(1.0 / 3.0), "fixed", "0.333", 3);

  // decimalPlaces behavior must not change.
  expectText(Json::Value(1.234), "fixed", "1.23", 2, "decimal");
  expectText(Json::Value(1.005), "fixed", "1.0", 2, "decimal");
  expectText(Json::Value(1.0), "fixed", "1.0", 2, "decimal");
  expectText(Json::Value(1.234), "fixed", "1.234", 6, "decimal");

  // Non-finite values keep the useSpecialFloats contract in both modes.
  const double nan = std::nan("");
  const double inf = std::numeric_limits<double>::infinity();
  expectText(Json::Value(nan), "roundTrip", "null", 17, "significant", false);
  expectText(Json::Value(nan), "roundTrip", "NaN", 17, "significant", true);
  expectText(Json::Value(inf), "roundTrip", "Infinity", 17, "significant", true);
  expectText(Json::Value(-inf), "roundTrip", "-Infinity", 17, "significant", true);

  // Exact round-trip over a corpus, including denormals and extremes.
  const std::vector<double> corpus = {
      0.0,
      -0.0,
      0.1,
      0.2,
      0.1 + 0.2,
      1.0 / 3.0,
      -42.5,
      1e-7,
      1e-300,
      1e300,
      5e-324,
      std::numeric_limits<double>::max(),
      std::numeric_limits<double>::min(),
      std::numeric_limits<double>::epsilon(),
      2.2250738585072014e-308,
      9007199254740992.0,
      9007199254740994.0,
      123456789.123456789,
      3.141592653589793,
      2.718281828459045,
      1.7976931348623157e308,
  };
  for (double value : corpus) {
    const std::string text = write(Json::Value(value), "roundTrip");
    bool ok = false;
    const double back = parseDouble(text, &ok);
    check(ok, "roundTrip output is valid JSON: " + text);
    check(ok && back == value, "roundTrip exact value for " + text);
    check(std::signbit(back) == std::signbit(value),
          "roundTrip preserves sign of zero for " + text);
  }

  // Integer values above 2^53 are not routed through the double formatter.
  Json::Value big;
  big = Json::UInt64(9007199254740993ULL);
  expectText(big, "roundTrip", "9007199254740993");

  // validate() accepts the new setting and still rejects typos.
  Json::StreamWriterBuilder builder;
  builder["precisionMode"] = "roundTrip";
  Json::Value invalid;
  check(builder.validate(&invalid), "validate accepts precisionMode");
  builder["precisionModeo"] = "roundTrip";
  check(!builder.validate(&invalid), "validate still rejects unknown settings");

  // Bad mode is a hard error, not a silent fallback.
  bool threw = false;
  try {
    Json::StreamWriterBuilder bad;
    bad["precisionMode"] = "bogus";
    std::unique_ptr<Json::StreamWriter> writer(bad.newStreamWriter());
  } catch (const Json::RuntimeError&) {
    threw = true;
  }
  check(threw, "invalid precisionMode throws Json::RuntimeError");

  if (g_failures != 0) {
    std::cout << g_failures << " check(s) failed\n";
    return 1;
  }
  std::cout << "all precision-mode checks passed\n";
  return 0;
}
