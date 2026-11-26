"""Validate every generated task with the two-sided Harbor gate.

For each task:
  * docker build the agent image and the separate verifier image,
  * `harbor run -a oracle`  -> reward must be 1,
  * copy the task, replace solve.sh with a no-op,
    `harbor run -a oracle` -> reward must be 0.

The negative control is the important half: it proves the hidden tests fail on
the untouched baseline instead of rewarding a no-op patch.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import catalog, config
from .catalog import TaskSpec

LOG_PATH = config.ROOT / "validation.log"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(line: str) -> None:
    stamp = _now()
    print(line)
    with LOG_PATH.open("a") as handle:
        handle.write(f"[{stamp}] {line}\n")


def _run(
    cmd: list[str], *, cwd: Path | None = None, timeout: int = 1800
) -> subprocess.CompletedProcess[str]:
    log(f"$ {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            cmd, 124, exc.stdout or "", f"timeout after {timeout}s"
        )
    if result.stdout.strip():
        log(result.stdout.strip()[-4000:])
    if result.stderr.strip():
        log("stderr: " + result.stderr.strip()[-4000:])
    log(f"exit={result.returncode}")
    return result


def _job_reward(jobs_dir: Path, job_name: str) -> tuple[float | None, Path | None]:
    candidates = sorted(
        jobs_dir.rglob("result.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    preferred = jobs_dir / job_name / "result.json"
    ordered = ([preferred] if preferred.is_file() else []) + [
        path for path in candidates if path != preferred
    ]
    for path in ordered:
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        for evaluation in data.get("stats", {}).get("evals", {}).values():
            for metric in evaluation.get("metrics", []):
                mean = metric.get("mean")
                if mean is not None:
                    return float(mean), path
    return None, None


def docker_build(spec: TaskSpec, task_dir: Path) -> tuple[bool, str]:
    env_image = f"factory-{spec.task_id}-env:latest"
    verifier_image = f"factory-{spec.task_id}-verifier:latest"
    env = _run(
        [
            "docker",
            "build",
            "-q",
            "-t",
            env_image,
            "-f",
            str(task_dir / "environment" / "Dockerfile"),
            str(task_dir / "environment"),
        ]
    )
    if env.returncode != 0:
        return False, env.stderr.strip()[-2000:]
    verifier = _run(
        [
            "docker",
            "build",
            "-q",
            "-t",
            verifier_image,
            "-f",
            str(task_dir / "tests" / "Dockerfile"),
            str(task_dir / "tests"),
        ]
    )
    if verifier.returncode != 0:
        return False, verifier.stderr.strip()[-2000:]
    return True, "both images built"


def harbor_trial(task_dir: Path, job_name: str) -> dict[str, object]:
    jobs_dir = config.JOBS_DIR
    jobs_dir.mkdir(parents=True, exist_ok=True)
    result = _run(
        [
            "harbor",
            "run",
            "-p",
            str(task_dir),
            "-a",
            "oracle",
            "-e",
            "docker",
            "-y",
            "--job-name",
            job_name,
            "--jobs-dir",
            str(jobs_dir),
            "-q",
        ],
        timeout=1800,
    )
    reward, result_path = _job_reward(jobs_dir, job_name)
    return {
        "exit_code": result.returncode,
        "reward": reward,
        "result_json": str(result_path.relative_to(config.ROOT))
        if result_path
        else None,
        "stdout_tail": result.stdout.strip()[-3000:],
        "stderr_tail": result.stderr.strip()[-3000:],
    }


def validate_task(spec: TaskSpec, negative: bool = True) -> dict[str, object]:
    task_dir = config.TASKS_DIR / spec.directory
    if not task_dir.is_dir():
        raise SystemExit(f"{spec.task_id}: missing task directory {task_dir}")

    log(f"===== {spec.task_id} ({spec.directory}) =====")
    built, detail = docker_build(spec, task_dir)
    if not built:
        log(f"{spec.task_id}: docker build FAILED: {detail}")
        return {
            "task_id": spec.task_id,
            "docker_build": "failed",
            "detail": detail,
            "positive": {"reward": None},
            "negative": {"reward": None},
            "passed": False,
        }

    positive = harbor_trial(task_dir, f"validate-{spec.task_id}-positive")
    log(f"{spec.task_id}: positive reward={positive['reward']}")

    negative_result: dict[str, object] = {"skipped": True, "reward": None}
    if negative:
        control_root = config.WORK_DIR / "negative" / spec.directory
        if control_root.exists():
            shutil.rmtree(control_root)
        shutil.copytree(task_dir, control_root)
        (control_root / "solution" / "solve.sh").write_text(
            "#!/bin/bash\n"
            "# Negative control: intentionally does nothing.\n"
            "exit 0\n"
        )
        (control_root / "solution" / "solve.sh").chmod(0o755)
        negative_result = harbor_trial(
            control_root, f"validate-{spec.task_id}-negative"
        )
        log(f"{spec.task_id}: negative reward={negative_result['reward']}")

    gate_positive = positive["reward"] == 1.0
    gate_negative = (negative_result["reward"] == 0.0) if negative else True
    passed = built and gate_positive and gate_negative
    log(
        f"{spec.task_id}: {'PASS' if passed else 'FAIL'} "
        f"(positive={positive['reward']}, negative={negative_result['reward']})"
    )
    return {
        "task_id": spec.task_id,
        "directory": spec.directory,
        "docker_build": "passed",
        "positive": positive,
        "negative": negative_result,
        "passed": passed,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", nargs="*", help="task ids or slugs")
    parser.add_argument("--n", type=int, default=len(catalog.TASKS))
    parser.add_argument("--skip-negative", action="store_true")
    parser.add_argument(
        "--report", type=Path, default=config.EVIDENCE_DIR / "validation.json"
    )
    args = parser.parse_args(argv)

    config.verify_baseline()
    specs = catalog.select(args.tasks, args.n)
    config.JOBS_DIR.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(f"# jsoncpp harbor factory validation\n# started {_now()}\n")

    started = time.time()
    results = [validate_task(spec, negative=not args.skip_negative) for spec in specs]
    report = {
        "started_at": _now(),
        "duration_sec": round(time.time() - started, 1),
        "harbor_version": subprocess.run(
            ["harbor", "--version"], text=True, capture_output=True
        ).stdout.strip(),
        "baseline_commit": config.BASELINE_COMMIT,
        "tasks": results,
        "passed": all(item["passed"] for item in results),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    log(f"validation report: {args.report} passed={report['passed']}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
