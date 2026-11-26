# RFC 7386 JSON Merge Patch for `Json::Value`

`/app/jsoncpp` contains jsoncpp at commit `93acc7b` (declared version 1.10.0), prebuilt in `/app/build`.

Applications commonly layer configuration files: a base document, then one or more overlays where `null` removes a key. jsoncpp has no merge-patch primitive, so every caller reimplements the recursion and gets the edge cases wrong.

## Required change

Add one method to `Json::Value`:

```cpp
void mergePatch(const Value& patch);
```

It mutates `*this` according to RFC 7386:

- If `patch` is **not an object**, replace `*this` with a copy of `patch`. This includes `null`, scalars, and arrays.
- If `patch` is an object:
  - If `*this` is not an object, convert it to an empty object first.
  - For each member of `patch`:
    - a `null` value deletes that key from the target; deleting a missing key is a no-op;
    - any other value **replaces** the member, except that nested objects merge recursively.
  - Arrays are replaced wholesale and never merged element-wise.
- The `patch` argument must not be modified.
- Merging a value with itself must be safe.

Example:

```json
target: {"a":"b","c":{"d":"e","f":"g"}}
patch:  {"a":"z","c":{"f":null}}
result: {"a":"z","c":{"d":"e"}}
```

## Build

```bash
cmake -S /app/jsoncpp -B /app/build \
  -DJSONCPP_LIB_BUILD_SHARED=OFF -DJSONCPP_WITH_TESTS=ON -DCMAKE_BUILD_TYPE=Release
cmake --build /app/build -j"$(nproc)"
ctest --test-dir /app/build --output-on-failure
```

## Acceptance

The verifier rebuilds `/app/jsoncpp` from source and links hidden C++ tests against it. They cover the RFC example, deletion, missing-key deletion, recursive merge, array replacement, scalar/array/null replacement of the whole document, object-over-scalar conversion, empty patches, patch immutability, Unicode keys, and self-merge. `ctest` must stay green.

Use exactly this method name and signature; the tests call `Value::mergePatch`.
