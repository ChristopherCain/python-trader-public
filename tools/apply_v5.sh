#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

find src tests scripts -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
find src tests scripts -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true

echo "PythonTrader v5 reliability overlay applied"
