# RFC 6901 JSON Pointer lookup for `Json::Value`

`/app/jsoncpp` contains jsoncpp at commit `93acc7b` (declared version 1.10.0), prebuilt in `/app/build`.

The DOM can address members one level at a time (`find`, `operator[]`), but there is no way to resolve a standard JSON Pointer path. Applications that implement JSON Patch, configuration overlays, or URL-addressed documents have to reimplement RFC 6901 themselves.

## Required change

Add two methods to `Json::Value`:

```cpp
Value* findPointer(const String& pointer);
const Value* findPointer(const String& pointer) const;
```

Resolution rules:

- The empty pointer `""` resolves to `this`.
- A non-empty pointer must begin with `/`, otherwise throw `Json::LogicError`.
- Tokens are separated by `/`. Inside a token, `~1` decodes to `/` and `~0` decodes to `~`, applied left to right. Any other `~` escape (including a trailing `~`) throws `Json::LogicError`.
- Object tokens match member names byte for byte after decoding. A missing member returns `nullptr`.
- Array tokens must be `0` or a decimal integer with no leading zero and no sign. Out-of-range indices, `-`, `+1`, `01`, and non-numeric tokens return `nullptr`.
- Traversing through a scalar returns `nullptr`.
- The const overload returns a const pointer; the non-const overload allows mutating the resolved element.

Examples, for `{"a":{"b":[10,20]}}`:

| Pointer | Result |
| --- | --- |
| `""` | the root value |
| `/a/b/1` | `20` |
| `/a/b/2` | `nullptr` |
| `/a/b/01` | `nullptr` |
| `/a/missing` | `nullptr` |
| `"a/b"` | throws `Json::LogicError` |

## Build

```bash
cmake -S /app/jsoncpp -B /app/build \
  -DJSONCPP_LIB_BUILD_SHARED=OFF -DJSONCPP_WITH_TESTS=ON -DCMAKE_BUILD_TYPE=Release
cmake --build /app/build -j"$(nproc)"
ctest --test-dir /app/build --output-on-failure
```

## Acceptance

The verifier rebuilds `/app/jsoncpp` from source and links hidden C++ tests against it. Those tests cover root resolution, nesting, both escape sequences, empty keys, non-ASCII keys, array index grammar, out-of-range and overflow indices, scalar traversal, const and mutable overloads, and syntax-error exceptions. `ctest` must stay green.

Do not add a different public API name; the tests call `findPointer`.
