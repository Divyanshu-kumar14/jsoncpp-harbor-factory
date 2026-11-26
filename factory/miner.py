"""Mine the pinned jsoncpp baseline for function hotspots and upstream issue context.

Two real signals are collected:
  1. Function definitions per source file, via ast-grep (with a regex fallback).
  2. Upstream GitHub issues/PRs matching the capability keywords, via `gh api`.

Nothing here is synthesised: if a tool is unavailable the report says so and the
corresponding section is empty.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import baseline, catalog, config

FUNCTION_RE = re.compile(
    r"(?<![\w:])((?:[A-Za-z_]\w*::)*[A-Za-z_]\w*)\s*\((?!\s*\*)"  # name(
)

KEYWORDS = [
    "utf8",
    "utf-8",
    "unicode",
    "duplicate",
    "precision",
    "round",
    "pointer",
    "reader",
    "writer",
    "parser",
    "overflow",
]


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def _ast_grep_functions(path: Path) -> list[dict[str, object]]:
    """Return function definitions using ast-grep's typed `function_definition` node."""
    rule = """id: function-definitions
language: cpp
rule:
  kind: function_definition
"""
    result = _run(
        [
            "ast-grep",
            "scan",
            "--inline-rules",
            rule,
            "--json=stream",
            str(path),
        ]
    )
    if result.returncode != 0:
        return []
    functions = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            match = json.loads(line)
        except json.JSONDecodeError:
            continue
        text = match.get("text", "")
        name_match = FUNCTION_RE.search(text)
        if not name_match:
            continue
        functions.append(
            {
                "name": name_match.group(1),
                "line": match.get("range", {}).get("start", {}).get("line", 0) + 1,
                "signature": text.split("{", 1)[0].strip()[:200],
            }
        )
    return functions


def _regex_functions(path: Path) -> list[dict[str, object]]:
    functions = []
    for number, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        if "(" not in line or line.lstrip().startswith(("//", "*")):
            continue
        match = FUNCTION_RE.search(line)
        if not match:
            continue
        if line.rstrip().endswith(";"):
            continue
        functions.append(
            {"name": match.group(1), "line": number, "signature": line.strip()[:200]}
        )
    return functions


def mine_functions(source: Path) -> dict[str, object]:
    use_ast_grep = shutil.which("ast-grep") is not None
    files = sorted((source / "src" / "lib_json").glob("*.cpp"))
    files += sorted((source / "include" / "json").glob("*.h"))
    per_file: dict[str, list[dict[str, object]]] = {}
    for path in files:
        found = _ast_grep_functions(path) if use_ast_grep else []
        if not found:
            found = _regex_functions(path)
        if found:
            per_file[str(path.relative_to(source))] = found
    return {
        "engine": "ast-grep" if use_ast_grep else "regex-fallback",
        "files": per_file,
        "total_functions": sum(len(v) for v in per_file.values()),
    }


def scrape_issues(limit: int = 100) -> dict[str, object]:
    if shutil.which("gh") is None:
        return {"available": False, "reason": "gh CLI not installed", "issues": []}
    result = _run(
        [
            "gh",
            "api",
            f"repos/open-source-parsers/jsoncpp/issues?state=all&per_page={limit}&sort=updated",
        ]
    )
    if result.returncode != 0:
        return {
            "available": False,
            "reason": result.stderr.strip()[:400],
            "issues": [],
        }
    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {"available": False, "reason": f"bad JSON: {exc}", "issues": []}

    matched = []
    for issue in raw:
        if "pull_request" in issue:
            continue
        haystack = f"{issue.get('title', '')} {issue.get('body') or ''}".lower()
        hits = [word for word in KEYWORDS if word in haystack]
        if not hits:
            continue
        matched.append(
            {
                "number": issue.get("number"),
                "title": issue.get("title"),
                "state": issue.get("state"),
                "created_at": issue.get("created_at"),
                "url": issue.get("html_url"),
                "keywords": hits,
            }
        )
    matched.sort(key=lambda item: item.get("number") or 0, reverse=True)
    return {"available": True, "issues": matched}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="jsoncpp", choices=["jsoncpp"])
    parser.add_argument("--source", type=Path, help="use an existing checkout")
    parser.add_argument("--skip-issues", action="store_true")
    parser.add_argument(
        "--output", type=Path, default=config.EVIDENCE_DIR / "mining_report.json"
    )
    args = parser.parse_args(argv)

    config.verify_baseline()
    if args.source:
        source = args.source
    else:
        source = baseline.extract_baseline(config.WORK_DIR / "baseline-src")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo": config.BASELINE_REPO,
        "commit": config.BASELINE_COMMIT,
        "source": str(source),
        "functions": mine_functions(source),
        "issues": {"available": False, "issues": []}
        if args.skip_issues
        else scrape_issues(),
        "catalogue": [
            {
                "task_id": spec.task_id,
                "feature": spec.feature,
                "difficulty": spec.difficulty,
                "category": spec.category,
                "absence_probe": [f"{path}: {needle!r}" for path, needle in spec.absent_markers],
            }
            for spec in catalog.TASKS
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")

    functions = report["functions"]
    print(
        f"miner: {functions['total_functions']} functions across "
        f"{len(functions['files'])} files using {functions['engine']}"
    )
    for path, items in list(functions["files"].items())[:6]:
        print(f"  {path}: {len(items)} functions")
    issues = report["issues"]
    if issues["available"]:
        print(f"miner: {len(issues['issues'])} matching upstream issues")
        for issue in issues["issues"][:5]:
            print(f"  #{issue['number']} {issue['title']}")
    else:
        print(f"miner: issue scrape skipped ({issues['reason']})")
    print(f"miner: wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
