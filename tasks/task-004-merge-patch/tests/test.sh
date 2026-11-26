#!/bin/bash
# Harbor verifier: rebuild the agent's jsoncpp tree from source, then run the
# hidden acceptance tests that were baked into this image.
#
# Always exits 0 after writing a reward; a non-zero exit must never be confused
# with "reward 1".
set -uo pipefail

REWARD_FILE=/logs/verifier/reward.txt
SRC=/app/jsoncpp
BUILD=/tmp/verify-build

mkdir -p /logs/verifier

fail() {
    echo "REWARD=0 reason=$1"
    echo 0 > "$REWARD_FILE"
    exit 0
}

[ -d "$SRC" ] || fail "artifact /app/jsoncpp is missing"
[ -f "$SRC/CMakeLists.txt" ] || fail "/app/jsoncpp is not a jsoncpp source tree"

rm -rf "$BUILD"
if ! cmake -S "$SRC" -B "$BUILD" \
        -DJSONCPP_LIB_BUILD_SHARED=OFF \
        -DJSONCPP_WITH_TESTS=OFF \
        -DCMAKE_BUILD_TYPE=Release; then
    fail "cmake configure failed"
fi
if ! cmake --build "$BUILD" -j"$(nproc)"; then
    fail "jsoncpp build failed"
fi

LIB="$BUILD/lib/libjsoncpp.a"
[ -f "$LIB" ] || fail "static library was not produced"

shopt -s nullglob
tests=(/tests/hidden/*.cpp)
[ "${#tests[@]}" -gt 0 ] || fail "no hidden tests found in verifier image"

for test_src in "${tests[@]}"; do
    name="$(basename "$test_src" .cpp)"
    bin="/tmp/$name"
    if ! g++ -std=c++17 -O2 -I"$SRC/include" "$test_src" "$LIB" -pthread -o "$bin"; then
        fail "hidden test failed to compile: $name"
    fi
    if ! "$bin"; then
        fail "hidden test failed: $name"
    fi
done

echo "REWARD=1 all hidden tests passed"
echo 1 > "$REWARD_FILE"
exit 0
