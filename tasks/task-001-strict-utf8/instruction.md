# Strict UTF-8 validation for jsoncpp string parsing

`/app/jsoncpp` contains jsoncpp at commit `93acc7b` (declared version 1.10.0), prebuilt in `/app/build`.

RFC 8259 §8.1 requires JSON text to be UTF-8. jsoncpp currently accepts any byte `>= 0x20` inside a string, so malformed UTF-8 — overlong encodings, surrogate halves, truncated sequences — silently enters the DOM.

## Required change

Add a `CharReaderBuilder` setting named `validateUTF8`.

- Default: `false`, preserving today's behaviour for existing callers.
- When `true`, `parse()` rejects any string, whether an object key or a value, whose raw bytes are not well-formed UTF-8 as defined by RFC 3629.
- Rejection returns `false` and reports through the existing error mechanism. The message must contain `Invalid UTF-8 sequence in string` and the usual `Line N, Column M` location.
- Escaped `\uXXXX` sequences are unaffected; they keep using the existing decoding path.
- `strictMode()` must turn the setting on.
- `CharReaderBuilder::validate()` must accept the new key.

Malformed input includes stray continuation bytes, overlong encodings (`C0 AF`, `E0 80 80`, `F0 80 80 80`), UTF-16 surrogate halves (`ED A0 80`, `ED BF BF`), code points above U+10FFFF (`F4 90 80 80`, `F5 ...`), truncated sequences, and invalid lead bytes (`FE`, `FF`).

Everything else must keep working: trailing-comma leniency, comments, numeric keys, and the existing rejection of control characters `0x00`–`0x1F`.

## Build

```bash
cmake -S /app/jsoncpp -B /app/build \
  -DJSONCPP_LIB_BUILD_SHARED=OFF -DJSONCPP_WITH_TESTS=ON -DCMAKE_BUILD_TYPE=Release
cmake --build /app/build -j"$(nproc)"
ctest --test-dir /app/build --output-on-failure
```

## Acceptance

The verifier rebuilds `/app/jsoncpp` from source in a separate container and runs hidden C++ tests. It checks default-off behaviour, valid 2-, 3- and 4-byte sequences, every malformed class above, error text and line/column reporting, and preserved leniency. `ctest` must stay green.

Do not special-case the examples or weaken existing checks.
