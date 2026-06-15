#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_BIN="${PYTHON:-python3}"

if [ -x "./venv/bin/python" ]; then
  PYTHON_BIN="./venv/bin/python"
fi

COVERAGE=0
ARGS=()

for arg in "$@"; do
  if [ "$arg" = "--coverage" ]; then
    COVERAGE=1
  else
    ARGS+=("$arg")
  fi
done

if [ "$COVERAGE" -eq 1 ]; then
  ARGS+=("--cov=." "--cov-report=term-missing")
fi

exec "$PYTHON_BIN" -m pytest "${ARGS[@]}"