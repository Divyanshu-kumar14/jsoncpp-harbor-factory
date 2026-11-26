# RFC 8259 number validation for jsoncpp

`/app/jsoncpp` contains jsoncpp at commit `93acc7b` (declared version 1.10.0), prebuilt in `/app/build`.

jsoncpp's tokenizer accepts numbers that RFC 8259 forbids. At this baseline, `{"n":01}`, `{"n":1.}`, `{"n":+1}`, and `{"n":1.e2}` all parse successfully. For a validator, a configuration loader, or an interoperability layer, that silently rewrites malformed input.

## Required change

Add a `CharReaderBuilder` setting named `strictNumbers`.

- Default: `false`, preserving today's lenient behaviour.
- When `true`, every number token must match the RFC 8259 grammar exactly:

```text
number = [ "-" ] int [ frac ] [ exp ]
int    = "0" / ( digit1-9 *DIGIT )
frac   = "." 1*DIGIT
exp    = ("e" / "E") [ "+" / "-" ] 1*DIGIT
```

This rejects:

- leading zeros: `01`, `-01`, `00`, `00.5`;
- a leading plus: `+1`;
- a trailing decimal point: `1.`, `-1.`, `1.e2`;
- an empty exponent: `1e`, `1e+`, `1e-`;
- malformed tokens the tokenizer already rejects, such as `.5` and `1.2.3`.

It must still accept `0`, `-0`, `0.0`, `-0.5e+2`, `1E10`, `1e-7`, `10.25`, and large integers that fall back to doubles.

Rejection returns `false` and reports through the existing error mechanism. The message must contain `not a valid JSON number` and the usual `Line N, Column M` location.

Also:

- `strictMode()` must enable the setting;
- `CharReaderBuilder::validate()` must accept the key;
- trailing-comma leniency and all other settings keep working.

## Build

```bash
cmake -S /app/jsoncpp -B /app/build \
  -DJSONCPP_LIB_BUILD_SHARED=OFF -DJSONCPP_WITH_TESTS=ON -DCMAKE_BUILD_TYPE=Release
cmake --build /app/build -j"$(nproc)"
ctest --test-dir /app/build --output-on-failure
```

## Acceptance

The verifier rebuilds `/app/jsoncpp` from source and runs hidden C++ tests. They check the default-off behaviour, every invalid class above, valid boundary numbers, nested/array contexts, error text and line/column reporting, `strictMode()`, and `validate()`. `ctest` must stay green.
