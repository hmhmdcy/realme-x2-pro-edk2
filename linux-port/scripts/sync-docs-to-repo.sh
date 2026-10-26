#!/bin/bash
# Use --files for incremental work; --copy-only retains the full maintenance path.
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
RK=${SAMURAI_REPO:-/home/cy122/edk2-samurai/repo}
MODE=copy
MSG=""
case "${1:---copy-only}" in
  --files)
    shift
    if [ "$#" -eq 0 ]; then echo 'Usage: sync-docs-to-repo.sh --files PATH [PATH ...]' >&2; exit 2; fi
    python3 "$SCRIPT_DIR/docs-health-check.py" --local-only --files "$@"
    python3 "$SCRIPT_DIR/sync-docs.py" --repo "$RK" --files "$@"
    exec python3 "$SCRIPT_DIR/docs-health-check.py" --repo "$RK" --files "$@"
    ;;
  --copy-only) if [ "$#" -gt 1 ]; then echo 'Unexpected arguments.' >&2; exit 2; fi ;;
  --publish)
    if [ "$#" -ne 2 ] || [ -z "$2" ]; then echo 'Usage: sync-docs-to-repo.sh --publish "commit message"' >&2; exit 2; fi
    MODE=publish
    MSG=$2
    ;;
  *) echo 'Usage: sync-docs-to-repo.sh [--files PATH [PATH ...] | --copy-only | --publish "commit message"]' >&2; exit 2 ;;
esac

if [ "$MODE" = publish ]; then
  if ! git -C "$RK" diff --cached --quiet; then
    echo 'Existing staged changes: preserve them and resolve staging before publishing docs.' >&2
    exit 1
  fi
  if [ "$(git -C "$RK" branch --show-current)" != master ]; then
    echo 'Expected master for the documented fork publish path.' >&2
    exit 1
  fi
fi

python3 "$SCRIPT_DIR/generate-session-index.py"
python3 "$SCRIPT_DIR/update-repo-state.py" --repo "$RK"
python3 "$SCRIPT_DIR/docs-health-check.py" --local-only
python3 "$SCRIPT_DIR/sync-docs.py" --repo "$RK"
python3 "$SCRIPT_DIR/docs-health-check.py" --repo "$RK"

if [ "$MODE" = publish ]; then
  python3 "$SCRIPT_DIR/sync-docs.py" --repo "$RK" --stage
  if git -C "$RK" diff --cached --quiet; then
    echo 'No documentation changes to commit.'
    exit 0
  fi
  git -C "$RK" commit -m "$MSG"
  git -C "$RK" push fork master
fi
