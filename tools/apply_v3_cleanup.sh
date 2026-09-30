#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

rm -rf src/datamedicine
rm -rf web/src/pythontrader
rm -f pythontrader.pyproject.toml
rm -f tests/test_datamedicine.py
rm -rf docs/datamedicine

# Remove Python bytecode/caches from the working tree if present.
find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true

printf 'V3 cleanup complete.\n'
printf 'Removed legacy DataMedicine package, duplicated web backend and legacy pyproject alias.\n'
