# Dedicated verifier image: all tooling and hidden tests are baked in.
# Harbor does not upload tests into a verifier image that defines its own Dockerfile.
FROM ubuntu:24.04@sha256:562111b88caa79c71391c0c4d3c2114a7d5c35915c20561fd893cb1e07929e6b

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY . /tests/
RUN chmod +x /tests/test.sh

WORKDIR /tests
