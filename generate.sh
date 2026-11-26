#!/usr/bin/env bash
# One-command reproduction of the jsoncpp Harbor task factory.
#
#   ./generate.sh --repo jsoncpp --n 3
#   ./generate.sh --repo jsoncpp --n 3 --skip-validate
#   ./generate.sh --refresh-baseline --n 3
#
# Stages: miner -> generator (+ novelty/preflight gate) -> lint -> validator
# (oracle 1 / no-op 0) -> packager (zip).
set -euo pipefail
cd "$(dirname "$0")"

REPO="jsoncpp"
N="3"
DO_VALIDATE=1
DO_PACKAGE=1
SKIP_PREFLIGHT=0
REFRESH=0
TEMPLATE=""

usage() {
    cat <<'EOF'
Usage: ./generate.sh [options]

  --repo jsoncpp        Only jsoncpp is supported.
  --n N                 Number of catalogue tasks to generate (default 3).
  --tasks ID...         Generate specific task ids/slugs instead of the first N.
  --skip-validate       Skip docker build + Harbor 1/0 gate.
  --skip-package        Skip the submission zip.
  --skip-preflight      Skip the local novelty/build/test preflight.
  --refresh-baseline    Re-clone upstream at the pinned commit and rebuild the archive.
  --template PATH       Optional dashboard template zip for a completeness check.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --repo) REPO="$2"; shift 2 ;;
        --n) N="$2"; shift 2 ;;
        --tasks) shift; TASKS=(); while [[ $# -gt 0 && "$1" != --* ]]; do TASKS+=("$1"); shift; done ;;
        --skip-validate) DO_VALIDATE=0; shift ;;
        --skip-package) DO_PACKAGE=0; shift ;;
        --skip-preflight) SKIP_PREFLIGHT=1; shift ;;
        --refresh-baseline) REFRESH=1; shift ;;
        --template) TEMPLATE="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

[[ "$REPO" == "jsoncpp" ]] || { echo "--repo must be jsoncpp" >&2; exit 2; }
command -v docker >/dev/null || { echo "docker is required" >&2; exit 1; }
command -v python3 >/dev/null || { echo "python3 is required" >&2; exit 1; }

if ! command -v harbor >/dev/null 2>&1 || [[ "$(harbor --version 2>/dev/null || true)" != "0.25.0" ]]; then
    echo "== installing harbor==0.25.0 via uv =="
    command -v uv >/dev/null || { echo "uv is required to install harbor" >&2; exit 1; }
    uv tool install --force harbor==0.25.0
fi
echo "== harbor $(harbor --version) / docker $(docker --version | awk '{print $3}' | tr -d ',') =="

ARGS=(--repo "$REPO" --n "$N")
if [[ "$REFRESH" == "1" ]]; then ARGS+=(--refresh-baseline); fi
if [[ "$SKIP_PREFLIGHT" == "1" ]]; then ARGS+=(--skip-preflight); fi

echo "== miner =="
python3 -m factory.miner --repo "$REPO"

echo "== generator =="
python3 -m factory.generator "${ARGS[@]}"

echo "== lint =="
LINT_ARGS=(--n "$N")
if [[ -n "${TASKS:-}" ]]; then LINT_ARGS=(--tasks "${TASKS[@]}"); fi
python3 -m factory.packager "${LINT_ARGS[@]}" --lint-only

if [[ "$DO_VALIDATE" == "1" ]]; then
    echo "== validator (oracle expects 1, no-op expects 0) =="
    VAL_ARGS=(--n "$N")
    if [[ -n "${TASKS:-}" ]]; then VAL_ARGS=(--tasks "${TASKS[@]}"); fi
    python3 -m factory.validator "${VAL_ARGS[@]}"
fi

if [[ "$DO_PACKAGE" == "1" ]]; then
    echo "== packager =="
    PKG_ARGS=(--n "$N")
    if [[ -n "${TASKS:-}" ]]; then PKG_ARGS=(--tasks "${TASKS[@]}"); fi
    if [[ -n "$TEMPLATE" ]]; then PKG_ARGS+=(--template "$TEMPLATE"); fi
    python3 -m factory.packager "${PKG_ARGS[@]}"
fi

echo "== done =="
