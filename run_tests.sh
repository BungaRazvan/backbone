#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON:-python3}"

if [ -x "./venv/bin/python" ]; then
  PYTHON_BIN="./venv/bin/python"
fi

COVERAGE=0
for arg in "$@"; do
  if [ "$arg" = "--coverage" ]; then
    COVERAGE=1
  fi
done

if [ "$COVERAGE" -eq 1 ]; then
  set -- "$@" --cov=. --cov-report=term-missing
fi

"$PYTHON_BIN" -m pytest "$@"
