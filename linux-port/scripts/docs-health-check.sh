#!/bin/bash
# Read-only documentation validation; default also checks the repository mirror.
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec python3 "$SCRIPT_DIR/docs-health-check.py" "$@"
