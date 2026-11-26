// Hidden verifier for task-004: RFC 7386 JSON Merge Patch.
#include <json/json.h>

#include <iostream>
#include <string>

namespace {

int g_failures = 0;

void check(bool cond, const std::string& what) {
  if (!cond) {
    ++g_failures;
    std::cout << "FAIL: " << what << "\n";
  }
}

Json::Value parse(const std::string& text) {
  Json::CharReaderBuilder builder;
  Json::Value root;
  std::string errs;
  std::unique_ptr<Json::CharReader> reader(builder.newCharReader());
  if (!reader->parse(text.data(), text.data() + text.size(), &root, &errs)) {
    std::cout << "FAIL: cannot parse fixture: " << errs << "\n";
    ++g_failures;
  }
  return root;
}

std::string compact(const Json::Value& value) {
  Json::StreamWriterBuilder builder;
  builder["indentation"] = "";
  return Json::writeString(builder, value);
}

void expect(const std::string& target, const std::string& patch,
            const std::string& want, const std::string& label) {
  Json::Value document = parse(target);
  const Json::Value patchValue = parse(patch);
  document.mergePatch(patchValue);
  const std::string got = compact(document);
  check(got == want, label + " want=" + want + " got=" + got);
}

} // namespace

int main() {
  // RFC 7386, Section 3 example.
  expect("{\"a\":\"b\",\"c\":{\"d\":\"e\",\"f\":\"g\"}}",
         "{\"a\":\"z\",\"c\":{\"f\":null}}",
         "{\"a\":\"z\",\"c\":{\"d\":\"e\"}}", "RFC example");

  // Null deletes; absent keys are untouched; new keys are added.
  expect("{\"a\":1,\"b\":2}", "{\"b\":null,\"c\":3}", "{\"a\":1,\"c\":3}",
         "null deletes a member");
  expect("{\"a\":1}", "{\"missing\":null}", "{\"a\":1}",
         "deleting an absent key is a no-op");

  // Nested objects merge recursively.
  expect("{\"a\":{\"b\":1,\"c\":2}}", "{\"a\":{\"b\":null,\"d\":4}}",
         "{\"a\":{\"c\":2,\"d\":4}}", "nested merge");
  expect("{\"a\":{\"b\":{\"c\":1}}}", "{\"a\":{\"b\":{\"d\":2}}}",
         "{\"a\":{\"b\":{\"c\":1,\"d\":2}}}", "deep recursive merge");

  // Arrays are replaced wholesale, never merged.
  expect("{\"a\":[1,2,3]}", "{\"a\":[4]}", "{\"a\":[4]}",
         "array replaced");
  expect("{\"a\":[{\"b\":1}]}", "{\"a\":[{\"c\":2}]}", "{\"a\":[{\"c\":2}]}",
         "array of objects replaced, not merged");

  // A non-object patch replaces the target.
  expect("{\"a\":1}", "42", "42", "scalar patch replaces object");
  expect("{\"a\":1}", "\"text\"", "\"text\"", "string patch replaces object");
  expect("{\"a\":1}", "null", "null", "null patch replaces object");
  expect("{\"a\":1}", "[1,2]", "[1,2]", "array patch replaces object");

  // An object patch turns a non-object target into an object.
  expect("42", "{\"a\":1}", "{\"a\":1}", "object patch replaces scalar");
  expect("42", "{}", "{}", "empty object patch replaces scalar with object");
  expect("{\"a\":1}", "{}", "{\"a\":1}", "empty object patch is a no-op");

  // Patch value is not modified.
  Json::Value patch = parse("{\"a\":null,\"b\":{\"c\":1}}");
  const std::string before = compact(patch);
  Json::Value document = parse("{\"a\":1,\"b\":{\"c\":2}}");
  document.mergePatch(patch);
  check(compact(patch) == before, "patch is not mutated");

  // Unicode keys and self-merge safety.
  expect("{\"caf\xC3\xA9\":1}", "{\"caf\xC3\xA9\":null}", "{}",
         "unicode key deletion");
  Json::Value self = parse("{\"a\":1,\"b\":{\"c\":2}}");
  const std::string selfBefore = compact(self);
  self.mergePatch(self);
  check(compact(self) == selfBefore, "self merge is stable");

  if (g_failures != 0) {
    std::cout << g_failures << " check(s) failed\n";
    return 1;
  }
  std::cout << "all merge-patch checks passed\n";
  return 0;
}
