# Shortest round-trip double formatting for jsoncpp

`/app/jsoncpp` contains jsoncpp at commit `93acc7b` (declared version 1.10.0), prebuilt in `/app/build`.

The writer's default is 17 significant digits, so a double that has a short exact representation is serialized with noise: `0.1` becomes `0.10000000000000001`, `1e-7` becomes `9.9999999999999995e-08`, and `1/3` becomes `0.33333333333333331`. The values round-trip, but logs, config files and wire payloads become unreadable, and diffs churn.

## Required change

Add a `StreamWriterBuilder` setting named `precisionMode`:

- `"fixed"` (default): today's behaviour, byte for byte. `precision` and `precisionType` keep working exactly as before.
- `"roundTrip"`: emit the shortest decimal string that parses back to exactly the same IEEE-754 binary64 value. Ignore `precision` and `precisionType` in this mode.
- Any other value throws `Json::RuntimeError` from `newStreamWriter()`.
- `StreamWriterBuilder::validate()` must accept the new key.
- `setDefaults()` must include `"precisionMode": "fixed"`.

Required examples in `roundTrip` mode:

| Value | Output |
| --- | --- |
| `0.1` | `0.1` |
| `0.2` | `0.2` |
| `0.1 + 0.2` | `0.30000000000000004` |
| `1.0 / 3.0` | `0.3333333333333333` |
| `1.0` | `1.0` |
| `1e-7` | `1e-07` |
| `1e20` | `1e+20` |

Preserve the surrounding contracts:

- Non-finite values still follow `useSpecialFloats` (`null`/`NaN`/`Infinity`/`-Infinity`).
- `precisionType: "decimal"` is unchanged in `fixed` mode.
- Integers, including `UInt64` values above 2^53, still take the integer path and are never routed through the double formatter.
- The output is valid JSON and must parse back to the identical double for the whole corpus, including denormals (`5e-324`), `DBL_MIN`, `DBL_MAX`, and `DBL_EPSILON`.
- `-0.0` serializes with its sign preserved.

Ubuntu 24.04 ships GCC 13, so `std::to_chars` for floating point is available. A fallback to 17 significant digits on toolchains without it is acceptable.

## Build

```bash
cmake -S /app/jsoncpp -B /app/build \
  -DJSONCPP_LIB_BUILD_SHARED=OFF -DJSONCPP_WITH_TESTS=ON -DCMAKE_BUILD_TYPE=Release
cmake --build /app/build -j"$(nproc)"
ctest --test-dir /app/build --output-on-failure
```

## Acceptance

The verifier rebuilds `/app/jsoncpp` from source and runs hidden C++ tests. They assert byte-for-byte `fixed` compatibility, the exact `roundTrip` outputs above, ignore-`precision` behaviour, decimal-mode compatibility, special-float handling, the untouched `UInt64` path, `validate()`, and an exact parse-back corpus. `ctest` must stay green.
