# Raw reward evidence

Copied verbatim from each trial's `/logs/verifier/reward.txt`.

| File | Gate | Reward |
| --- | --- | ---: |
| `task-001-positive.reward.txt` | reference solution applied | 1 |
| `task-001-negative.reward.txt` | `solve.sh` replaced with a no-op | 0 |
| `task-002-positive.reward.txt` | reference solution applied | 1 |
| `task-002-negative.reward.txt` | `solve.sh` replaced with a no-op | 0 |
| `task-003-positive.reward.txt` | reference solution applied | 1 |
| `task-003-negative.reward.txt` | `solve.sh` replaced with a no-op | 0 |

Source directories (local run, not committed): `evidence/jobs/validate-<task>-<gate>/`.
Machine-readable aggregation: `evidence/validation.json`.
Command transcript: `validation.log` at the repository root.
