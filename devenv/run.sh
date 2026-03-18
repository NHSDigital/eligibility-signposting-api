#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD="python"
else
  echo "ERROR: Python is required but neither 'python3' nor 'python' is available on PATH." >&2
  exit 1
fi

exec "$PYTHON_CMD" "$SCRIPT_DIR/run.py" "$@"
