# jsoncpp → Harbor v0.25.x task factory

An automated pipeline that mines [open-source-parsers/jsoncpp](https://github.com/open-source-parsers/jsoncpp) at a pinned baseline and emits independent, containerized [Harbor](https://docs.harborframework.com/) task packages, each validated with a two-sided gate: **reward 1 with the reference solution, reward 0 without it**.

Built for the Hack2Skill × Innodata AI Hackathon, Prototype Submissions module.

---

## Result at a glance

| Task | Difficulty | Feature | Oracle | No-op control | `harbor lint` |
| --- | --- | --- | ---: | ---: | --- |
| `task-001-strict-utf8` | easy | `CharReaderBuilder["validateUTF8"]` | **1** | **0** | clean |
| `task-002-json-pointer` | medium | `Value::findPointer` (RFC 6901) | **1** | **0** | clean |
| `task-003-roundtrip-precision` | hard | `StreamWriterBuilder["precisionMode"]` | **1** | **0** | clean |

Raw evidence, not just summaries:

- `evidence/rewards/task-00X-positive.reward.txt` → `1`
- `evidence/rewards/task-00X-negative.reward.txt` → `0`
- `evidence/lint.json` → `[]`
- `evidence/validation.json` → `"passed": true`
- `validation.log` → every command, exit code, and Harbor summary

(`evidence/jobs/` holds the full local trial payloads and is gitignored; the reward files above are copied from it verbatim.)

---

## Why these three tasks (important)

The original brief specified control-character rejection, duplicate-key rejection, and 17-digit precision. **All three are already implemented at the pinned baseline**, so a patch would be a no-op and the no-solution gate would return 1. Verified at runtime:

| Proposed task | Observed baseline behaviour |
| --- | --- |
| Reject `0x00`–`0x1F` | Already rejected: `Control character in string`, `Line 1, Column 6` |
| `rejectDupKeys` | Setting already exists: `Duplicate key: 'a'` |
| 17-digit round-trip | Default is 17 significant digits: `0.1+0.2` → `0.30000000000000004` |

With the baseline fixed, the factory instead implements capabilities that are genuinely absent:

| Task | Absent at baseline | Evidence |
| --- | --- | --- |
| 001 | No UTF-8 validation; `C3 28` is accepted | 17 hidden checks fail before the patch |
| 002 | No JSON Pointer API | hidden test does not compile before the patch |
| 003 | No shortest round-trip mode; `0.1` → `0.10000000000000001` | 10 hidden checks fail before the patch |

The generator enforces this permanently with a **novelty gate**: every task declares markers that must be absent from the baseline. A task whose feature already exists is refused, not packaged.

---

## Baseline

```text
repo    https://github.com/open-source-parsers/jsoncpp
commit  93acc7b155048f1a66c43235cc205519f1e7a6ea   (2026-10-26)
describe 1.9.8-18-g93acc7b
version.h declares 1.10.0, but upstream publishes no v1.10.0 tag (newest is 1.9.8)
archive baseline/jsoncpp-93acc7b.tar.gz
sha256  1e29b66c58b56ca8d936fba105e0e44d1224db6d2e898a86b51fde5d0243b698
```

The archive is vendored so task images build offline and deterministically. `BASELINE.txt` is the source of truth and is checked by every stage.

---

## Quick start

Requirements: Docker, `uv`, Python 3.11+, `git`, `gh` (optional, for issue mining).

```bash
git clone https://github.com/Divyanshu-kumar14/jsoncpp-harbor-factory
cd jsoncpp-harbor-factory

# Installs harbor==0.25.0 if needed, then mines, generates, lints,
# validates (1/0) and packages.
./generate.sh --repo jsoncpp --n 3
```

Useful variants:

```bash
./generate.sh --n 3 --skip-validate          # fast authoring loop
./generate.sh --n 3 --skip-preflight         # skip local build/test preflight
./generate.sh --refresh-baseline             # re-clone upstream at the pinned commit
./generate.sh --n 3 --template /path/template.zip   # compare against the dashboard template
```

`--n` is capped by the verified catalogue (currently 3). Requesting 5 prints a notice and generates the 3 verified tasks rather than padding with unverified ones.

---

## Repository layout

```text
.
├── generate.sh                  # one-command pipeline
├── BASELINE.txt                 # pinned commit + archive checksum
├── baseline/
│   └── jsoncpp-93acc7b.tar.gz   # offline, deterministic source snapshot
├── factory/
│   ├── miner.py                 # ast-grep function map + gh issue scrape
│   ├── generator.py             # novelty gate, preflight, task rendering
│   ├── validator.py             # docker build + Harbor 1/0 gate
│   ├── packager.py              # harbor lint + submission zip
│   ├── catalog.py               # declarative task specs
│   ├── baseline.py              # archive verification, patch preflight
│   ├── config.py                # paths and constants
│   ├── assets/task-00X/         # instruction, patch, hidden test
│   └── templates/               # Dockerfiles, test.sh, solve.sh, task.toml
├── tasks/
│   ├── task-001-strict-utf8/
│   ├── task-002-json-pointer/
│   └── task-003-roundtrip-precision/
├── evidence/                    # mining, lint, validation, raw rewards
└── validation.log
```

Each task follows Harbor's standardized layout:

```text
task-00X/
├── instruction.md
├── task.toml
├── environment/
│   ├── Dockerfile
│   └── jsoncpp-93acc7b.tar.gz
├── solution/
│   ├── solve.sh
│   └── patch.diff
└── tests/
    ├── Dockerfile
    ├── test.sh
    └── hidden/test_*.cpp
```

---

## How grading works

Harbor 0.25 defaults to a **separate verifier**. The agent container holds `/app/jsoncpp` and `/app/build`; its filesystem changes are *not* inherited by the verifier. `task.toml` therefore declares:

```toml
artifacts = ["/app/jsoncpp"]

[verifier]
environment_mode = "separate"
```

The verifier image (`tests/Dockerfile`) bakes in the hidden tests and all tooling. At grade time `tests/test.sh`:

1. rebuilds jsoncpp from the agent's source with CMake,
2. compiles each hidden C++ test against that library,
3. runs it,
4. writes `1` to `/logs/verifier/reward.txt` only if every test passed, otherwise `0`.

The script always exits 0 after writing the reward, so a compile failure is a clean `0`, never a harness error. Hidden tests never enter the agent image (`agent-image-test-leak` stays clean).

More detail: [`ARCHITECTURE.md`](ARCHITECTURE.md).

---

## Manual verification of one task

```bash
cd tasks/task-001-strict-utf8

harbor lint . --json
harbor run -p . -a oracle -e docker -y
cat ../../evidence/jobs/validate-task-001-positive/*/verifier/reward.txt   # 1

# Negative control: replace solve.sh with a no-op and rerun
cp -r . /tmp/noop-task
printf '#!/bin/bash\nexit 0\n' > /tmp/noop-task/solution/solve.sh
harbor run -p /tmp/noop-task -a oracle -e docker -y
cat jobs/*/task-001*/verifier/reward.txt                                    # 0
```

The validator automates exactly this and records both rewards.

---

## Notes and open items

- **Dashboard template zip** was not available in this environment. `packager.py --template <zip>` compares the template's entries against generated tasks by basename and writes `evidence/template_check.json`. The submission zip currently uses the canonical Harbor layout.
- **Google Doc URL / exact doc baseline hash** were not available; the baseline was confirmed interactively as `93acc7b`. If the document specifies a different hash, update `BASELINE.txt` and run `./generate.sh --refresh-baseline`.
- `harbor==0.25.0` is enforced by `generate.sh`; newer/older versions abort the run.
- No API keys, credentials, or network access are needed at task runtime (`network_mode = "no-network"`).
