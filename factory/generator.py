"""Generate Harbor task packages from the catalogue, with a novelty gate.

For every task the generator:
  1. proves the capability is absent from the pinned baseline (so a patch is real),
  2. applies the reference patch to a scratch tree,
  3. proves the expected symbols are present,
  4. builds jsoncpp and runs the hidden test against the patched tree,
  5. renders the Harbor package (separate verifier, baked tests, artifact transfer).

Step 1 is the gate that would have rejected the three originally proposed tasks:
at commit 93acc7b, control-character rejection, rejectDupKeys and 17-digit
precision already exist.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import baseline, catalog, config
from .catalog import TaskSpec


def _render(template: Path, values: dict[str, str]) -> str:
    text = template.read_text()
    for key, value in values.items():
        text = text.replace(f"@{key}@", value)
    return text


def _toml_string(value: str) -> str:
    return json.dumps(value)


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


def _chmod(path: Path) -> None:
    path.chmod(0o755)


def preflight(spec: TaskSpec, baseline_src: Path, work: Path) -> dict[str, object]:
    """Prove the patch is necessary and sufficient before Docker is involved."""
    still_present = baseline.markers_present(baseline_src, spec.absent_markers)
    if still_present:
        raise SystemExit(
            f"{spec.task_id}: novelty gate failed. These markers already exist in "
            f"the pinned baseline, so the task is a no-op:\n  "
            + "\n  ".join(still_present)
        )

    patch = config.ASSETS_DIR / spec.task_id / "patch.diff"
    if not patch.is_file():
        raise SystemExit(f"{spec.task_id}: missing patch {patch}")

    tree = baseline.apply_patch(baseline_src, patch, work / spec.task_id)
    missing = baseline.markers_missing(tree, spec.present_markers)
    if missing:
        raise SystemExit(
            f"{spec.task_id}: patched tree is missing expected markers:\n  "
            + "\n  ".join(missing)
        )

    build = work / f"{spec.task_id}-build"
    configure = _run(
        [
            "cmake",
            "-S",
            str(tree),
            "-B",
            str(build),
            "-DJSONCPP_LIB_BUILD_SHARED=OFF",
            "-DJSONCPP_WITH_TESTS=OFF",
            "-DCMAKE_BUILD_TYPE=Release",
        ]
    )
    if configure.returncode != 0:
        raise SystemExit(f"{spec.task_id}: cmake configure failed\n{configure.stderr}")
    compile_lib = _run(["cmake", "--build", str(build), "-j", "16"])
    if compile_lib.returncode != 0:
        raise SystemExit(f"{spec.task_id}: build failed\n{compile_lib.stderr}")

    lib = build / "lib" / "libjsoncpp.a"
    for hidden in spec.hidden_tests:
        source = config.ASSETS_DIR / spec.task_id / hidden
        binary = work / f"{spec.task_id}-{Path(hidden).stem}"
        compile_test = _run(
            [
                "g++",
                "-std=c++17",
                "-O2",
                f"-I{tree / 'include'}",
                str(source),
                str(lib),
                "-pthread",
                "-o",
                str(binary),
            ]
        )
        if compile_test.returncode != 0:
            raise SystemExit(
                f"{spec.task_id}: hidden test {hidden} failed to compile\n"
                f"{compile_test.stderr}"
            )
        run_test = _run([str(binary)])
        if run_test.returncode != 0:
            raise SystemExit(
                f"{spec.task_id}: hidden test {hidden} failed on the patched tree\n"
                f"{run_test.stdout}\n{run_test.stderr}"
            )

    return {
        "task_id": spec.task_id,
        "novelty_gate": "passed",
        "patch_applied": True,
        "library_build": "passed",
        "hidden_tests": {hidden: "passed" for hidden in spec.hidden_tests},
    }


def render_task(spec: TaskSpec, source_archive: Path) -> Path:
    dest = config.TASKS_DIR / spec.directory
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "environment").mkdir(parents=True)
    (dest / "solution").mkdir()
    (dest / "tests" / "hidden").mkdir(parents=True)

    asset_dir = config.ASSETS_DIR / spec.task_id
    (dest / "instruction.md").write_text((asset_dir / "instruction.md").read_text())

    values = {
        "TASK_NAME": _toml_string(spec.task_name),
        "TASK_VERSION": _toml_string("1.0.0"),
        "DESCRIPTION": _toml_string(spec.description),
        "AUTHOR": _toml_string(spec.author),
        "TITLE": spec.title,
        "TASK_ID": dest.name,
        "FEATURE": spec.feature,
        "DIFFICULTY": spec.difficulty,
        "CATEGORY": spec.category,
        "TAGS": json.dumps(spec.tags),
        "EXPERT_MIN": str(spec.expert_min),
        "JUNIOR_MIN": str(spec.junior_min),
        "VERIFIER_TIMEOUT": str(int(spec.verifier_timeout)),
        "AGENT_TIMEOUT": str(int(spec.agent_timeout)),
        "BUILD_TIMEOUT": str(int(spec.build_timeout)),
        "HIDDEN_TEST": spec.hidden_tests[0],
    }

    (dest / "task.toml").write_text(
        _render(config.TEMPLATES_DIR / "task.toml.tmpl", values)
    )
    (dest / "README.md").write_text(
        _render(config.TEMPLATES_DIR / "task-README.md.tmpl", values)
    )

    env_dockerfile = dest / "environment" / "Dockerfile"
    shutil.copy2(config.TEMPLATES_DIR / "environment.Dockerfile", env_dockerfile)
    shutil.copy2(source_archive, dest / "environment" / source_archive.name)

    tests_dockerfile = dest / "tests" / "Dockerfile"
    shutil.copy2(config.TEMPLATES_DIR / "tests.Dockerfile", tests_dockerfile)
    test_sh = dest / "tests" / "test.sh"
    shutil.copy2(config.TEMPLATES_DIR / "test.sh", test_sh)
    _chmod(test_sh)
    for hidden in spec.hidden_tests:
        shutil.copy2(asset_dir / hidden, dest / "tests" / "hidden" / hidden)

    solve_sh = dest / "solution" / "solve.sh"
    shutil.copy2(config.TEMPLATES_DIR / "solve.sh", solve_sh)
    _chmod(solve_sh)
    shutil.copy2(asset_dir / "patch.diff", dest / "solution" / "patch.diff")

    # Dockerfiles are static; make the executable bits explicit on the files that
    # Harbor runs, since git preserves them but zip extraction may not.
    _chmod(tests_dockerfile)
    _chmod(env_dockerfile)
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="jsoncpp", choices=["jsoncpp"])
    parser.add_argument("--n", type=int, default=len(catalog.TASKS))
    parser.add_argument("--tasks", nargs="*", help="task ids or slugs")
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument("--refresh-baseline", action="store_true")
    parser.add_argument(
        "--report", type=Path, default=config.EVIDENCE_DIR / "generation_report.json"
    )
    args = parser.parse_args(argv)

    if args.refresh_baseline:
        baseline.refresh_baseline_from_upstream()
    meta = config.verify_baseline()
    specs = catalog.select(args.tasks, args.n)
    if not specs:
        raise SystemExit("no tasks selected")

    config.WORK_DIR.mkdir(parents=True, exist_ok=True)
    config.TASKS_DIR.mkdir(parents=True, exist_ok=True)

    baseline_src = baseline.extract_baseline(config.WORK_DIR / "baseline-src")
    results = []
    for spec in specs:
        print(f"generate: {spec.task_id} ({spec.difficulty}) {spec.feature}")
        if args.skip_preflight:
            preflight_result: dict[str, object] = {"skipped": True}
        else:
            preflight_result = preflight(spec, baseline_src, config.WORK_DIR / "preflight")
        dest = render_task(spec, config.BASELINE_ARCHIVE)
        print(f"  wrote {dest.relative_to(config.ROOT)}")
        results.append(
            {
                "task_id": spec.task_id,
                "directory": dest.name,
                "task_name": spec.task_name,
                "difficulty": spec.difficulty,
                "feature": spec.feature,
                "preflight": preflight_result,
            }
        )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "baseline_commit": meta["commit"],
        "baseline_archive_sha256": meta["archive_sha256"],
        "harbor_schema_version": "1.4",
        "tasks": results,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(f"generate: wrote {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
