// Hidden verifier for task-002: RFC 6901 JSON Pointer on Json::Value.
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

template <typename F>
void checkLogicError(F&& fn, const std::string& what) {
  try {
    fn();
    check(false, what + " (no exception thrown)");
  } catch (const Json::LogicError&) {
    check(true, what);
  } catch (const std::exception& e) {
    check(false, what + " (wrong exception: " + e.what() + ")");
  }
}

} // namespace

int main() {
  Json::Value root;
  root["foo"] = 42;
  root["a/b"] = "slash";
  root["m~n"] = "tilde";
  root["~1"] = "tilde-one";
  root[""] = "empty-key";
  root["arr"][0] = "zero";
  root["arr"][1] = "one";
  root["arr"][2] = 3;
  root["nested"]["deep"]["x"] = true;
  root["obj"][""] = "inner-empty";
  root["unicode"]["caf\xC3\xA9"] = "accent";
  root["scalar"] = 7;

  check(root.findPointer("") == &root, "empty pointer resolves to root");
  check(root.findPointer("/foo") == &root["foo"], "/foo");
  check(root.findPointer("/a~1b") == &root["a/b"], "~1 decodes to /");
  check(root.findPointer("/m~0n") == &root["m~n"], "~0 decodes to ~");
  check(root.findPointer("/~01") == &root["~1"],
        "escapes decode left to right (~01 -> ~1)");
  check(root.findPointer("/") == &root[""], "single / addresses empty key");
  check(root.findPointer("/obj/") == &root["obj"][""],
        "trailing / addresses empty key");
  check(root.findPointer("/unicode/caf\xC3\xA9") == &root["unicode"]["caf\xC3\xA9"],
        "non-ASCII object key");
  check(root.findPointer("/nested/deep/x") == &root["nested"]["deep"]["x"],
        "deep pointer");
  check(root.findPointer("/arr/0") == &root["arr"][0], "array index 0");
  check(root.findPointer("/arr/2") == &root["arr"][2], "array index 2");
  check(root.findPointer("/arr/2")->asInt() == 3, "array element value");

  // Valid syntax, no resolution.
  check(root.findPointer("/missing") == nullptr, "missing member");
  check(root.findPointer("/arr/3") == nullptr, "array index out of range");
  check(root.findPointer("/arr/-") == nullptr, "dash is not a lookup index");
  check(root.findPointer("/arr/01") == nullptr, "leading zero index");
  check(root.findPointer("/arr/+1") == nullptr, "signed index");
  check(root.findPointer("/arr/-1") == nullptr, "negative index");
  check(root.findPointer("/arr/1e0") == nullptr, "non-decimal index");
  check(root.findPointer("/arr/999999999999999999999999999") == nullptr,
        "overflowing index");
  check(root.findPointer("/foo/bar") == nullptr, "traversal through scalar");
  check(root.findPointer("/nested/deep/x/y") == nullptr,
        "traversal through bool");
  check(root.findPointer("/nested/missing/x") == nullptr, "missing mid-path");

  // Invalid syntax.
  checkLogicError([&] { root.findPointer("foo"); }, "pointer without leading /");
  checkLogicError([&] { root.findPointer("a/b"); }, "relative pointer");
  checkLogicError([&] { root.findPointer("/a~2b"); }, "unknown escape ~2");
  checkLogicError([&] { root.findPointer("/a~"); }, "trailing ~");
  checkLogicError([&] { root.findPointer("/arr/0/x~"); }, "bad escape deep");

  // Const overload returns the same object.
  const Json::Value& constRoot = root;
  check(constRoot.findPointer("/foo") == &root["foo"], "const overload");
  check(constRoot.findPointer("/missing") == nullptr, "const missing");

  // Mutable overload mutates the document.
  *root.findPointer("/foo") = 43;
  check(root["foo"].asInt() == 43, "non-const pointer mutates document");
  *root.findPointer("/arr/1") = "ONE";
  check(root["arr"][1].asString() == "ONE", "non-const array element");

  // Root can be an array.
  Json::Value list(Json::arrayValue);
  list.append("a");
  list.append("b");
  check(list.findPointer("") == &list, "array root empty pointer");
  check(list.findPointer("/1") == &list[1], "array root index");
  check(list.findPointer("/2") == nullptr, "array root out of range");
  check(list.findPointer("/key") == nullptr, "object token on array");

  if (g_failures != 0) {
    std::cout << g_failures << " check(s) failed\n";
    return 1;
  }
  std::cout << "all json-pointer checks passed\n";
  return 0;
}
