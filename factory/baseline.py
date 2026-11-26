"""Baseline acquisition, extraction, and patch preflight."""

from __future__ import annotations

import shutil
import subprocess
import tarfile
from pathlib import Path

from . import config


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd, cwd=cwd, text=True, capture_output=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(cmd)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def extract_baseline(dest: Path) -> Path:
    """Extract the vendored archive, stripping the top-level `jsoncpp/` directory."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    with tarfile.open(config.BASELINE_ARCHIVE) as archive:
        members = []
        for member in archive.getmembers():
            parts = Path(member.name).parts
            if len(parts) <= 1:
                continue
            member.name = str(Path(*parts[1:]))
            members.append(member)
        archive.extractall(dest, members=members, filter="data")
    return dest


def refresh_baseline_from_upstream(commit: str = config.BASELINE_COMMIT) -> None:
    """Clone upstream, verify the commit, and regenerate the vendored archive."""
    clone = config.WORK_DIR / "upstream-jsoncpp"
    config.WORK_DIR.mkdir(parents=True, exist_ok=True)
    if clone.exists():
        shutil.rmtree(clone)
    _run(["git", "clone", "--quiet", config.BASELINE_REPO, str(clone)])
    _run(["git", "checkout", "--quiet", commit], cwd=clone)
    head = _run(["git", "rev-parse", "HEAD"], cwd=clone).stdout.strip()
    if head != commit:
        raise RuntimeError(f"upstream HEAD {head} != pinned commit {commit}")
    config.BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "git",
            "archive",
            "--format=tar.gz",
            f"--prefix=jsoncpp/",
            commit,
            "-o",
            str(config.BASELINE_ARCHIVE),
        ],
        cwd=clone,
    )
    print(f"wrote {config.BASELINE_ARCHIVE} ({config.sha256(config.BASELINE_ARCHIVE)})")


def copy_tree(src: Path, dest: Path) -> Path:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    return dest


def apply_patch(source: Path, patch: Path, dest: Path) -> Path:
    """Copy `source` to `dest` and apply a -p1 patch there."""
    copy_tree(source, dest)
    with patch.open("rb") as handle:
        result = subprocess.run(
            ["patch", "-p1", "--forward", "--batch"],
            cwd=dest,
            stdin=handle,
            text=False,
            capture_output=True,
            check=False,
        )
    if result.returncode != 0:
        raise RuntimeError(
            f"patch did not apply: {patch}\n"
            f"{result.stdout.decode(errors='replace')}\n"
            f"{result.stderr.decode(errors='replace')}"
        )
    return dest


def markers_present(root: Path, markers: list[tuple[str, str]]) -> list[str]:
    """Return the markers that ARE found in `root`."""
    found: list[str] = []
    for relpath, needle in markers:
        path = root / relpath
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        if needle in text:
            found.append(f"{relpath}: {needle!r}")
    return found


def markers_missing(root: Path, markers: list[tuple[str, str]]) -> list[str]:
    """Return the markers that are NOT found in `root`."""
    found = set(markers_present(root, markers))
    return [
        f"{relpath}: {needle!r}"
        for relpath, needle in markers
        if f"{relpath}: {needle!r}" not in found
    ]
