# Submission rules and evidence

Rules source: the Hack2Skill × Innodata brief supplied for this build (§3 hard
constraints, §7 validation gates, §8 deliverables) plus the supplied
`Innodata _ IDEA SUBMISSION.pptx` template. The external Google Doc and the
portal form were not accessible; no claim in this repository depends on them.

| # | Requirement | Evidence (file:line) | Verdict |
| --- | --- | --- | --- |
| 1 | `harbor==0.25.0` exactly | `generate.sh:55-58` (version check + forced install), `evidence/validation.json` → `harbor_version: 0.25.0` | PASS |
| 2 | jsoncpp only, pinned commit, no floating master | `BASELINE.txt:2` (`93acc7b…`), `BASELINE.txt:8` (archive SHA-256), vendored tarball in every `environment/` | PASS |
| 3 | Standard Harbor task layout | each of the 5 `tasks/task-00X-*/` has `instruction.md`, `task.toml`, `environment/Dockerfile`, `solution/{solve.sh,patch.diff}`, `tests/{Dockerfile,test.sh,hidden/}` | PASS |
| 4 | `harbor lint` passes | `evidence/lint.json` = `[]`; `packager` exits 0 on all 5 tasks | PASS |
| 5 | Reward 1 with solution, 0 without | `evidence/validation.json` (10/10), `evidence/rewards/*.txt` (raw 1/0) | PASS |
| 6 | Independent, isolated trials | `tasks/task-001-strict-utf8/task.toml:23` (`environment_mode = "separate"`), `task.toml:2` (`artifacts = ["/app/jsoncpp"]`), no shared state between task directories | PASS |
| 7 | Keep the supplied template's filenames | deck built from the supplied PPTX, 11 slides preserved in place: `submission/Innodata_IDEA_SUBMISSION_jsoncpp.pptx` | PASS |
| 8 | Source + setup + sample outputs + validation evidence + technical explanation | `README.md`, `ARCHITECTURE.md`, `validation.log`, `evidence/`, `gate/`, deck | PASS |
| 9 | N ≥ 3 tasks | 5 tasks, `evidence/validation.json` → `tasks: 5` | PASS |
| 10 | Deadline / portal upload | external; not verifiable from this repository | OUT OF SCOPE |

## Notes

- The template turned out to be an 11-slide PPTX deck, not a zip. The deck is
  filled from `factory/deck.py`; task packages keep the canonical Harbor layout.
- The baseline was confirmed interactively as `93acc7b`. If the Google Doc names
  a different commit, `BASELINE.txt` is the single place to change, followed by
  `./generate.sh --refresh-baseline --n 5`.
