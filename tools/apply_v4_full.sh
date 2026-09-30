#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
rm -rf src/datamedicine 2>/dev/null || true
rm -rf web/src/pythontrader 2>/dev/null || true
rm -f pythontrader.pyproject.toml 2>/dev/null || true
printf 'PythonTrader v4 repository cleanup applied\n'
