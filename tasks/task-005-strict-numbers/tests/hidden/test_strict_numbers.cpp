// Hidden verifier for task-005: CharReaderBuilder["strictNumbers"].
#include <json/json.h>

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

struct Result {
  bool ok;
  std::string errors;
};

Result parse(const std::string& doc, bool strict) {
  Json::CharReaderBuilder builder;
  builder["strictNumbers"] = strict;
  Json::Value root;
  std::string errs;
  std::unique_ptr<Json::CharReader> reader(builder.newCharReader());
  Result result;
  result.ok = reader->parse(doc.data(), doc.data() + doc.size(), &root, &errs);
  result.errors = errs;
  return result;
}

void accept(const std::string& number, bool strict = true) {
  const std::string doc = "{\"n\":" + number + "}";
  Result result = parse(doc, strict);
  check(result.ok, "expected accept: " + number + " errs=" + result.errors);
}

void reject(const std::string& number, bool requireMessage) {
  const std::string doc = "{\"n\":" + number + "}";
  Result result = parse(doc, true);
  check(!result.ok, "expected reject: " + number);
  if (!result.ok && requireMessage) {
    check(result.errors.find("not a valid JSON number") != std::string::npos,
          "message names the number grammar for " + number + " got=" + result.errors);
    check(result.errors.find("Line 1") != std::string::npos,
          "line reported for " + number + " got=" + result.errors);
    check(result.errors.find("Column") != std::string::npos,
          "column reported for " + number + " got=" + result.errors);
  }
}

} // namespace

int main() {
  Json::CharReaderBuilder probe;
  check(probe.settings_.isMember("strictNumbers"),
        "CharReaderBuilder exposes a strictNumbers setting");
  check(probe.settings_["strictNumbers"].asBool() == false,
        "strictNumbers defaults to false");

  // Backward compatibility: the lenient default is unchanged.
  for (const std::string number : {"01", "1.", "+1", "-01", "1.e2"}) {
    accept(number, false);
  }

  // RFC 8259-valid numbers.
  for (const std::string number : {
           "0", "-0", "0.0", "-0.5e+2", "1E10", "123", "1e-7", "10.25",
           "-12345678901234567890", "1e+308", "0.0001", "-9.99e-10"}) {
    accept(number);
  }

  // RFC 8259-invalid numbers that jsoncpp's tokenizer accepts.
  for (const std::string number : {"01", "-01", "00", "1.", "-1.", "1.e2",
                                   "01.2", "00.5"}) {
    reject(number, true);
  }
  // Leading plus: tokenised as a number today.
  reject("+1", true);
  // Rejected by the tokenizer in both modes; still must fail.
  for (const std::string number : {".5", "1e", "1e+", "1e-", "1.2.3", "--1"}) {
    reject(number, false);
  }

  // Strict parsing also applies inside arrays and nested objects.
  check(!parse("[01]", true).ok, "reject leading zero in array");
  check(!parse("{\"a\":{\"b\":1.}}", true).ok, "reject trailing dot nested");
  check(parse("[0,1,2,3]", true).ok, "accept valid array numbers");
  check(parse("{\"a\":1,}", true).ok, "trailing comma leniency preserved");

  // strictMode() enables the setting.
  Json::CharReaderBuilder strict;
  Json::Value settings;
  strict.strictMode(&settings);
  check(settings["strictNumbers"].asBool(), "strictMode enables strictNumbers");

  // validate() accepts the new key.
  Json::CharReaderBuilder builder;
  builder["strictNumbers"] = true;
  Json::Value invalid;
  check(builder.validate(&invalid), "validate accepts strictNumbers");

  if (g_failures != 0) {
    std::cout << g_failures << " check(s) failed\n";
    return 1;
  }
  std::cout << "all strict-number checks passed\n";
  return 0;
}
