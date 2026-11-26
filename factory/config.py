"""Shared paths and baseline verification for the jsoncpp task factory."""

from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FACTORY_DIR = ROOT / "factory"
ASSETS_DIR = FACTORY_DIR / "assets"
TEMPLATES_DIR = FACTORY_DIR / "templates"
BASELINE_DIR = ROOT / "baseline"
TASKS_DIR = ROOT / "tasks"
EVIDENCE_DIR = ROOT / "evidence"
WORK_DIR = ROOT / ".work"
JOBS_DIR = EVIDENCE_DIR / "jobs"

BASELINE_REPO = "https://github.com/open-source-parsers/jsoncpp"
BASELINE_COMMIT = "93acc7b155048f1a66c43235cc205519f1e7a6ea"
BASELINE_ARCHIVE = BASELINE_DIR / "jsoncpp-93acc7b.tar.gz"
BASELINE_META = BASELINE_DIR / "BASELINE.txt"
ROOT_BASELINE_TXT = ROOT / "BASELINE.txt"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_baseline_meta() -> dict[str, str]:
    meta: dict[str, str] = {}
    for line in ROOT_BASELINE_TXT.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        meta[key.strip()] = value.strip()
    return meta


def verify_baseline() -> dict[str, str]:
    """Fail loudly if the vendored archive is missing or does not match BASELINE.txt."""
    meta = read_baseline_meta()
    if meta.get("commit") != BASELINE_COMMIT:
        raise SystemExit(
            f"BASELINE.txt commit {meta.get('commit')!r} does not match the "
            f"factory's pinned commit {BASELINE_COMMIT!r}"
        )
    if not BASELINE_ARCHIVE.is_file():
        raise SystemExit(
            f"missing {BASELINE_ARCHIVE}. Run ./generate.sh --refresh-baseline"
        )
    actual = sha256(BASELINE_ARCHIVE)
    expected = meta.get("archive_sha256", "")
    if actual != expected:
        raise SystemExit(
            f"baseline archive checksum mismatch\n  expected {expected}\n  actual   {actual}"
        )
    return meta
