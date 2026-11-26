# Deck text (extracted for the claim audit)

## Slide 1
Team Name :  jsoncpp Task Factory
Problem Statement :
AI coding benchmarks are expensive to author and easy to leak. This factory turns a pinned C++ repository into non-trivial, containerized Harbor tasks — and proves every one with a 0/1 gate.
Team Leader Name :  Divyanshu

## Slide 2
01 · THE IDEA
A factory that proves its own tasks are non-trivial
Jsoncpp Harbor Task Factory converts open-source-parsers/jsoncpp at commit 93acc7b into independent Harbor v0.25.0 task packages. One command runs mining, generation, lint, validation and packaging.
The generator refuses any capability already present at the baseline, then applies the reference patch, builds jsoncpp and runs the hidden test before a package is allowed to exist.
Five tasks cover the reader, DOM and writer. All ten gate runs returned 1 with the reference solution and 0 with a no-op solution.

## Slide 3
02 · OPPORTUNITY
Benchmarks should be generated, not hand-written
How is it different?
A novelty gate blocks tasks that upstream already solved. Every package is compiled and tested before it ships, so “already implemented” and “does not build” cannot masquerade as benchmark tasks.
How does it solve the problem?
Pinned baseline → mined gap → reference patch → isolated verifier → two-sided reward. Hidden tests live only in the verifier image and grade a rebuild of the agent's source.
USP
Non-triviality is enforced mechanically, and every reward is backed by a raw 1/0 file. The same pipeline reproduces all five tasks from one command.

## Slide 4
03 · FEATURES
Five stages, each fail-closed
•  ast-grep map: 579 function definitions across 12 files, plus 31 matching issues from the latest gh sample.
•  Novelty gate: absent-marker checks reject features that already exist at 93acc7b.
•  Preflight: patch, symbol check, CMake build and hidden test before packaging.
•  Harbor 0.25 packaging: schema 1.4, separate verifier, digest-pinned Ubuntu 24.04.
•  Artifact transfer: /app/jsoncpp crosses the boundary; /app/build never does.
•  Two-sided validation: oracle must score 1, a no-op solve.sh must score 0.
•  Packager: harbor lint must report zero findings, then emits the submission zip.

## Slide 5
04 · PROCESS
Mine → generate → lint → validate → package
A failure at any stage stops the run; no package is produced.
•  Novelty gate: the capability must be absent at 93acc7b, or the task is refused.
•  Preflight: the reference patch must compile and pass the hidden test before packaging.
•  Validator: each task runs twice — with the reference solution (1) and a no-op (0).

## Slide 6
05 · INTERFACE
One command, every stage
./generate.sh --repo jsoncpp --n 5 — the full reproduction path.

## Slide 7
06 · ARCHITECTURE
Isolated grading by construction
Harbor starts a separate verifier that rebuilds the agent's source.
•  Only /app/jsoncpp crosses the boundary; /app/build is deliberately excluded.
•  Hidden tests are baked into tests/Dockerfile and never enter the agent image.
•  A tampered build directory cannot influence the reward — the verifier rebuilds.
Every reward is a raw 1 or 0 in /logs/verifier/reward.txt.

## Slide 8
07 · STACK
Small, open, reproducible
•  Harbor 0.25.0 is the execution engine: task images, separate verifier, artifacts, rewards.
•  Task schema 1.4; hidden tests live only in the verifier image.
•  Docker 29 · Ubuntu 24.04 pinned by SHA-256 digest.
•  GCC 13 · CMake · static libjsoncpp.a built in-image.
•  ast-grep for typed function mining; gh CLI for issue context.
•  Bash verifier that always writes /logs/verifier/reward.txt.
•  No paid APIs, no runtime network, no credentials.

## Slide 9
08 · COST
Near-zero marginal cost
•  All components are open source: jsoncpp (MIT), Harbor, ast-grep, Docker.
•  Ten Harbor trials over five tasks on one 16-core host; no paid APIs or cloud spend.
•  Five 183 KB source snapshots keep every task self-contained and offline.
•  Adding a task costs one catalogue entry, one patch and one hidden test — not a new harness.

## Slide 10
09 · DELIVERABLES
What the judges can run
•  github.com/Divyanshu-kumar14/jsoncpp-harbor-factory — public and reproducible.
•  5 tasks: strict UTF-8 · JSON Pointer · round-trip precision · merge patch · strict numbers.
•  submission/jsoncpp-harbor-tasks.zip — tasks, raw rewards, docs and this deck.
•  evidence/rewards/*.txt — raw 1/0 files from all ten trials.
•  validation.log · evidence/lint.json · README.md · ARCHITECTURE.md.
•  Verified: harbor lint 0 findings; 10/10 gate trials correct.

## Slide 11
