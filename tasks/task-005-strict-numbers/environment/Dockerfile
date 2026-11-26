# Agent environment for every jsoncpp task in this factory.
# The baseline tree is baked in so the image builds offline and deterministically.
FROM ubuntu:24.04@sha256:562111b88caa79c71391c0c4d3c2114a7d5c35915c20561fd893cb1e07929e6b

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        patch \
        python3 \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ADD jsoncpp-93acc7b.tar.gz /app/

WORKDIR /app
RUN cmake -S /app/jsoncpp -B /app/build \
        -DJSONCPP_LIB_BUILD_SHARED=OFF \
        -DJSONCPP_WITH_TESTS=ON \
        -DCMAKE_BUILD_TYPE=Release \
    && cmake --build /app/build -j"$(nproc)"

ENV JSONCPP_SRC=/app/jsoncpp \
    JSONCPP_BUILD=/app/build

WORKDIR /app
