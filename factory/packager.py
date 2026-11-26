"""Lint all task packages, check an optional dashboard template, and build the zip."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from . import catalog, config

SUBMISSION_DIR = config.ROOT / "submission"


def run_lint(task_dirs: list[Path]) -> tuple[int, object, str]:
    result = subprocess.run(
        ["harbor", "lint", "--json", *map(str, task_dirs)],
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        findings = json.loads(result.stdout) if result.stdout.strip() else []
    except json.JSONDecodeError:
        findings = {"unparsed_stdout": result.stdout, "stderr": result.stderr}
    return result.returncode, findings, result.stdout + result.stderr


def template_check(template: Path, task_dirs: list[Path]) -> dict[str, object]:
    if not template.is_file():
        return {"provided": str(template), "exists": False}
    with zipfile.ZipFile(template) as archive:
        names = [name for name in archive.namelist() if not name.endswith("/")]
    ours = {
        path.name
        for task_dir in task_dirs
        for path in task_dir.rglob("*")
        if path.is_file()
    }
    missing = sorted({Path(name).name for name in names} - ours)
    return {
        "provided": str(template),
        "exists": True,
        "template_entries": len(names),
        "template_top_level": sorted({name.split("/", 1)[0] for name in names}),
        "missing_basenames": missing,
        "note": (
            "Dashboard template contents were compared by basename. The canonical "
            "Harbor layout is used for entries the template does not define."
        ),
    }


def build_zip(task_dirs: list[Path], output: Path) -> list[str]:
    output.parent.mkdir(parents=True, exist_ok=True)
    included: list[str] = []
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in ("README.md", "ARCHITECTURE.md", "BASELINE.txt", "validation.log"):
            path = config.ROOT / name
            if path.is_file():
                archive.write(path, name)
                included.append(name)
        for extra in sorted((config.EVIDENCE_DIR).glob("*.json")):
            arcname = f"evidence/{extra.name}"
            archive.write(extra, arcname)
            included.append(arcname)
        for extra in sorted((config.EVIDENCE_DIR / "rewards").glob("*")):
            if extra.is_file():
                arcname = f"evidence/rewards/{extra.name}"
                archive.write(extra, arcname)
                included.append(arcname)
        for extra in sorted(SUBMISSION_DIR.glob("*.pptx")):
            arcname = f"submission/{extra.name}"
            archive.write(extra, arcname)
            included.append(arcname)
        for extra in sorted((config.ROOT / "gate").glob("*.md")):
            arcname = f"gate/{extra.name}"
            archive.write(extra, arcname)
            included.append(arcname)
        for task_dir in task_dirs:
            for path in sorted(task_dir.rglob("*")):
                if not path.is_file():
                    continue
                arcname = str(Path("tasks") / task_dir.name / path.relative_to(task_dir))
                archive.write(path, arcname)
                included.append(arcname)
    return included


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", nargs="*", help="task ids or slugs")
    parser.add_argument("--n", type=int, default=len(catalog.TASKS))
    parser.add_argument("--template", type=Path, help="dashboard template zip")
    parser.add_argument(
        "--output", type=Path, default=SUBMISSION_DIR / "jsoncpp-harbor-tasks.zip"
    )
    parser.add_argument("--allow-lint-findings", action="store_true")
    parser.add_argument("--lint-only", action="store_true")
    args = parser.parse_args(argv)

    config.verify_baseline()
    specs = catalog.select(args.tasks, args.n)
    task_dirs = [config.TASKS_DIR / spec.directory for spec in specs]
    missing = [str(path) for path in task_dirs if not path.is_dir()]
    if missing:
        raise SystemExit(f"missing task directories: {missing}")

    exit_code, findings, raw = run_lint(task_dirs)
    config.EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (config.EVIDENCE_DIR / "lint.json").write_text(json.dumps(findings, indent=2) + "\n")
    (config.EVIDENCE_DIR / "lint.txt").write_text(raw)
    has_findings = bool(findings) and findings != []
    print(f"packager: harbor lint exit={exit_code} findings={len(findings) if isinstance(findings, list) else 'unparsed'}")
    if has_findings:
        print(json.dumps(findings, indent=2)[:4000])
    if exit_code != 0 or (has_findings and not args.allow_lint_findings):
        print("packager: refusing to package while lint is not clean", file=sys.stderr)
        return 1
    if args.lint_only:
        print("packager: lint-only, not writing a zip")
        return 0

    check = template_check(args.template, task_dirs) if args.template else {"provided": None}
    (config.EVIDENCE_DIR / "template_check.json").write_text(
        json.dumps(check, indent=2) + "\n"
    )

    included = build_zip(task_dirs, args.output)
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "harbor_version": subprocess.run(
            ["harbor", "--version"], text=True, capture_output=True
        ).stdout.strip(),
        "baseline_commit": config.BASELINE_COMMIT,
        "tasks": [path.name for path in task_dirs],
        "lint_exit_code": exit_code,
        "lint_findings": findings,
        "template_check": check,
        "zip": str(args.output),
        "zip_entries": len(included),
    }
    (SUBMISSION_DIR / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"packager: wrote {args.output} ({len(included)} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
