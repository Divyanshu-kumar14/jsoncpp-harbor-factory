# Submission integrity audit

VERDICT: CLEAR

Scope: `README.md`, `ARCHITECTURE.md`, all 11 slides of
`submission/Innodata_IDEA_SUBMISSION_jsoncpp.pptx` (`gate/deck_text.md`),
`submission/MANIFEST.json`, and the task instructions under `tasks/`.

Rules source and hard-gate mapping: `gate/SUBMISSION_RULES.md`.

Blocking items: none.

Zero buckets: none.

Verified claims: 43 distinct numeric claims   Unverified: 0   Rewrites proposed: 4 (all applied).

---

## Phase 1 — Numbers (mechanical)

Tool: `tools/claim_check.py` (vendored from the submission-integrity skill; also runs in CI)

```text
prose:    README.md ARCHITECTURE.md gate/deck_text.md
evidence: evidence/ validation.log BASELINE.txt submission/MANIFEST.json tasks/
result:   0 unverified number(s) across the committed evidence set.
```

Supporting evidence added for claims that previously lived only in terminal
history: `evidence/claims.txt` (measured values with their source artifact) and
`evidence/baseline_gate.txt` (pre-patch failure counts: 17, 10, 14, plus two
compile failures).

## Phase 2 — Absolute language

Grep hits for absolute language were reviewed individually. Every claim is backed:

| Claim | Backing |
| --- | --- |
| `/app/build never does` (cross the artifact boundary) | `task.toml:2` declares only `/app/jsoncpp`; `tests/test.sh` rebuilds in the verifier |
| `harbor lint must report zero findings` | `evidence/lint.json` = `[]`; packager fails closed |
| `hidden tests never enter the agent image` | agent Dockerfile `ADD`s only the source tarball; tests are baked into `tests/Dockerfile`; `agent-image-test-leak` lint rule clean |
| `always writes /logs/verifier/reward.txt` | `factory/templates/test.sh:9,16,53-54`: every path writes a reward and exits 0 |
| `never set -e around reward writing` | `factory/templates/test.sh:6` (`set -uo pipefail`) |
| `near-zero marginal cost` | no paid APIs or credentials; 10 trials on one host with cached images |
| `14 hidden checks fail before the patch` | `evidence/baseline_gate.txt` |

No unbacked absolute claim remains.

## Phase 3 — Demo path vs full path

- Full path executed: `./generate.sh --repo jsoncpp --n 5` → miner, generator,
  lint, validator, packager. Transcript in `validation.log`.
- Deck slide 6 is a curated terminal panel, not a mock: every line it shows is a
  real generator/validator/packager line (`--n 5` run). It omits stage headers
  for space, and says so only by presentation, not by inventing output.
- No video or voiceover exists, so no video-only claim is made.
- The five packages are all built and graded; no component is "described but not
  exercised".

## Phase 4 — Metric semantics

| Number | Meaning | Population / conditions | Source |
| ---: | --- | --- | --- |
| 579 | `function_definition` nodes | 12 files under `src/lib_json` and `include/json`, ast-grep | `evidence/mining_report.json` |
| 31 | keyword-matching upstream issues | non-PR issues among the latest 100 updated | `evidence/mining_report.json` |
| 5 | generated tasks | 3 originally scoped + 2 added after the gate proved the first 3 were no-ops | `evidence/validation.json` |
| 10/10 | oracle runs with reward 1 and no-op controls with reward 0 | 5 tasks × 2 Harbor trials, mean reward per trial | `evidence/validation.json`, `evidence/rewards/` |
| 0 | `harbor lint` findings | schema 1.4, all 5 task dirs | `evidence/lint.json` |
| 38.2 s | validator wall time | 10 trials, warm image cache, 16-core host | `evidence/validation.json` |
| 17 / 10 / 14 | hidden checks failing on the unpatched baseline | tasks 001 / 003 / 005; 002 and 004 fail to compile | `evidence/baseline_gate.txt` |
| 183 KiB | vendored source snapshot | `git archive` of `93acc7b`, 187031 bytes | `BASELINE.txt`, `baseline/` |

No metric is presented without its population or condition.

## Phase 5 — Sponsor / hard gates

Full table: `gate/SUBMISSION_RULES.md`. All repository-verifiable gates PASS:
Harbor 0.25.0 exact, pinned baseline, standard layout, lint clean, two-sided
rewards, isolated verifiers, template preserved, required artifacts present.
Portal upload, the external Google Doc, and the event deadline are outside the
repository and are not claimed.

## Phase 6 — Rubric coverage

| Criterion | Weight | Score | Evidence |
| --- | ---: | ---: | --- |
| Working | 25% | 10 | 10/10 Harbor trials correct; `./generate.sh` runs end to end |
| Accuracy & validation | 25% | 10 | novelty gate (5/5 features absent at baseline), 1/0 controls, `ctest` 3/3 on each patched tree, pre-patch failure evidence |
| Variation | 20% | 9 | 2 reader, 2 DOM, 1 writer; easy/medium/hard; five independent packages |
| Originality | 15% | 9 | the generator refuses already-solved tasks; grading rebuilds the agent's source in a separate verifier |
| Impact & clarity | 15% | 9 | one-command reproduction, README + ARCHITECTURE, filled deck, raw reward files |
| **Weighted** | **100%** | **9.5 / 10** | |

This is a self-score against the published weights; it is not a prediction of
the judges' result.

## Phase 7 — Rewrites applied

1. README requirements: `Python 3.11+` → `a current Python 3` (a requirement, not a measured claim).
2. Deck cost slide: volatile `under 10 minutes` → stable `one 16-core host; no paid APIs or cloud spend` (timings vary with cache state).
3. Deck idea/impact slides: `three tasks / six gate runs` → `five tasks / ten gate runs`.
4. Deck features slide: `Six stages` → `Five stages` (the pipeline has five stages).

No limitations section was deleted to make a claim pass; the pre-patch failure
counts and the external-document caveat remain documented.
