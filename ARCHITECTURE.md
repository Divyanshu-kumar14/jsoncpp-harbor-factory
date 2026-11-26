# Architecture

## Goal

Turn a pinned C++ repository into independent, reproducible Harbor tasks without hand-authoring each package and without shipping tasks that are already solved upstream.

## Pipeline

```text
            ┌──────────────┐
 baseline → │   miner.py   │  ast-grep function map + gh issue scrape
            └──────┬───────┘
                   ▼
            ┌──────────────┐
            │ generator.py │  novelty gate → patch → presence → build → test
            └──────┬───────┘
                   ▼
            ┌──────────────┐
            │  packager.py │  harbor lint (fail closed)
            └──────┬───────┘
                   ▼
            ┌──────────────┐
            │ validator.py │  docker build → oracle 1 → no-op 0
            └──────┬───────┘
                   ▼
            submission zip + evidence
```

`generate.sh` orchestrates the stages and pins `harbor==0.25.0`.

## Novelty gate

Every catalogue entry declares `absent_markers`: `(relative_path, needle)` pairs that must **not** exist in the baseline. The generator refuses to emit a task if any marker is found.

This is the factory's most important correctness property. Without it, a plausible-sounding task can be a no-op because the feature already landed upstream — exactly what happened with the brief's original control-character, duplicate-key, and 17-digit-precision tasks.

After applying the patch, the generator checks `present_markers`, configures CMake, builds `libjsoncpp.a`, compiles the hidden test, and runs it. Only then is the Harbor package rendered.

## Task package

Harbor schema `1.4`. One task = one directory = one independent unit.

| Component | Choice | Reason |
| --- | --- | --- |
| Agent image | `ubuntu:24.04@sha256:562111b8…` + gcc/cmake/patch + prebuilt jsoncpp | digest-pinned, offline, fast |
| Verifier mode | `separate` (Harbor 0.25 default) | hidden tests never reach the agent |
| Verifier image | `tests/Dockerfile`, tests baked in | no runtime installs or downloads (`verifier-runtime-install`, `verifier-network-download` clean) |
| Cross-container data | `artifacts = ["/app/jsoncpp"]` | Harbor copies agent outputs into the fresh verifier at the original path |
| Reward | `/logs/verifier/reward.txt` | required by Harbor |
| Network | `no-network` at runtime | reproducibility and safety |

### Why the artifact is the whole source tree

The verifier must observe the agent's edits, not its build outputs. Harbor deliberately does not inherit the agent filesystem into a separate verifier, and it sanitizes artifacts (setuid bits, escaping symlinks). Shipping `/app/jsoncpp` and rebuilding inside the verifier means:

- a stale or tampered `/app/build` cannot affect grading;
- the grade reflects the actual source the agent left behind;
- artifact transfer stays small (~2 MB).

`/app/build` is intentionally excluded from the artifact.

## Grading contract

`tests/test.sh` is defensive:

- `set -uo pipefail`, but never `set -e` around reward writing.
- Missing artifact, CMake failure, compile failure, or test failure all funnel through `fail()`, which writes `0` and exits `0`.
- Success writes `1` only after every hidden test exits 0.

Hidden tests use only the public jsoncpp API (`CharReaderBuilder`, `Json::Value`, `StreamWriterBuilder`). They assert behaviour, not implementation text, so any correct implementation passes.

### Two-sided validation

`validator.py` runs Harbor twice per task:

1. **Oracle**: the reference `solution/solve.sh` applies `patch.diff` and rebuilds → must be `1.0`.
2. **Negative control**: a copy of the task whose `solve.sh` does nothing → must be `0.0`.

The negative control is what makes the reward meaningful. It is also the check that catches a task whose feature already exists.

## Reproducibility

- Source pinned by commit and vendored as a tarball with a recorded SHA-256.
- Base image pinned by digest.
- All build dependencies installed at image-build time; task runtime has no network.
- Hidden tests and verifier toolchain baked into the verifier image.
- Job results, raw `reward.txt`, lint JSON, and validator output are written under `evidence/`.

## Extending the factory

1. Add a `TaskSpec` to `factory/catalog.py`, including `absent_markers` and `present_markers`.
2. Add `factory/assets/<task-id>/instruction.md`, `patch.diff`, and the hidden test.
3. Run `./generate.sh --n <count>`.

The novelty and build gates run before any Docker work, so a bad idea fails in seconds rather than after a full Harbor cycle.
