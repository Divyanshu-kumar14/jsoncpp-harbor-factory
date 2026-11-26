// Hidden verifier for task-001: CharReaderBuilder["validateUTF8"].
// Compiles against both the baseline (setting ignored) and a correct solution.
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

Result parse(const std::string& doc, bool validateUTF8, bool* settingExists) {
  Json::CharReaderBuilder builder;
  Json::Value settings = builder.settings_;
  if (settingExists)
    *settingExists = settings.isMember("validateUTF8");
  builder["validateUTF8"] = validateUTF8;
  Json::Value root;
  std::string errs;
  std::unique_ptr<Json::CharReader> reader(builder.newCharReader());
  Result r;
  r.ok = reader->parse(doc.data(), doc.data() + doc.size(), &root, &errs);
  r.errors = errs;
  return r;
}

void expectAccept(const std::string& doc, const char* label, bool validate) {
  Result r = parse(doc, validate, nullptr);
  check(r.ok, std::string("expected accept: ") + label + (r.ok ? "" : " errs=" + r.errors));
}

void expectReject(const std::string& doc, const char* label) {
  Result r = parse(doc, true, nullptr);
  check(!r.ok, std::string("expected reject: ") + label);
  if (!r.ok) {
    check(r.errors.find("Invalid UTF-8 sequence in string") != std::string::npos,
          std::string("error message mentions UTF-8: ") + label + " got=" + r.errors);
    check(r.errors.find("Line 1") != std::string::npos,
          std::string("error reports line: ") + label + " got=" + r.errors);
    check(r.errors.find("Column") != std::string::npos,
          std::string("error reports column: ") + label + " got=" + r.errors);
  }
}

std::string docWith(const std::string& raw) { return "{\"a\":\"" + raw + "\"}"; }

} // namespace

int main() {
  bool settingExists = false;
  parse("{}", true, &settingExists);
  check(settingExists, "CharReaderBuilder exposes a validateUTF8 setting");

  // Valid UTF-8 must keep parsing with validation enabled.
  expectAccept("{\"a\":\"ascii\"}", "ascii", true);
  expectAccept("{\"a\":\"caf\xC3\xA9\"}", "2-byte U+00E9", true);
  expectAccept("{\"a\":\"\xE2\x82\xAC\"}", "3-byte U+20AC", true);
  expectAccept("{\"a\":\"\xF0\x9F\x98\x80\"}", "4-byte U+1F600", true);
  expectAccept("{\"a\":\"\xE0\xA0\x80\"}", "3-byte boundary U+0800", true);
  expectAccept("{\"a\":\"\xED\x9F\xBF\"}", "last before surrogates U+D7FF", true);
  expectAccept("{\"a\":\"\xEE\x80\x80\"}", "first after surrogates U+E000", true);
  expectAccept("{\"a\":\"\xF4\x8F\xBF\xBF\"}", "max scalar U+10FFFF", true);
  expectAccept("{\"a\":\"\\u00e9\"}", "escaped unicode stays valid", true);
  expectAccept("{\"a\":[1,2,{\"b\":\"\xC3\xA9\"}]}", "nested valid UTF-8", true);
  expectAccept("{\"a\":\"ok\",}", "trailing comma leniency preserved", true);

  // Malformed sequences are rejected only when validation is requested.
  const std::vector<std::pair<std::string, const char*>> bad = {
      {"\xC3\x28", "unexpected continuation (C3 28)"},
      {"\x80", "lone continuation byte"},
      {"\xC0\xAF", "overlong 2-byte slash"},
      {"\xC1\xBF", "overlong 2-byte"},
      {"\xE0\x80\x80", "overlong 3-byte"},
      {"\xED\xA0\x80", "UTF-16 surrogate U+D800"},
      {"\xED\xBF\xBF", "UTF-16 surrogate U+DFFF"},
      {"\xF0\x80\x80\x80", "overlong 4-byte"},
      {"\xF4\x90\x80\x80", "above U+10FFFF"},
      {"\xF5\x80\x80\x80", "invalid lead F5"},
      {"\xFE", "invalid lead FE"},
      {"\xFF", "invalid lead FF"},
      {"\xC3", "truncated 2-byte"},
      {"\xE2\x82", "truncated 3-byte"},
      {"\xF0\x9F\x98", "truncated 4-byte"},
  };
  for (const auto& b : bad)
    expectReject(docWith(b.first), b.second);

  // Invalid bytes in an object key are also strings.
  expectReject("{\"\xC3\x28\":1}", "invalid UTF-8 in key");

  // Default is off: existing non-UTF-8 payloads keep working.
  expectAccept(docWith("\xC3\x28"), "default allows invalid UTF-8", false);

  if (g_failures != 0) {
    std::cout << g_failures << " check(s) failed\n";
    return 1;
  }
  std::cout << "all utf8-validation checks passed\n";
  return 0;
}
