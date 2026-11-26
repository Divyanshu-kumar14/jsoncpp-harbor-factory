#!/bin/bash
# Reference solution: apply the task patch to the baseline tree and rebuild.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="${JSONCPP_SRC:-/app/jsoncpp}"

cd "$SRC"
patch -p1 --forward --batch < "$DIR/patch.diff"

cmake -S "$SRC" -B /app/build \
    -DJSONCPP_LIB_BUILD_SHARED=OFF \
    -DJSONCPP_WITH_TESTS=ON \
    -DCMAKE_BUILD_TYPE=Release
cmake --build /app/build -j"$(nproc)"
