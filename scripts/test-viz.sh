#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${ONTOLOGY_PYTHON:-$ROOT/viz-server/.venv/bin/python}"
if [ ! -x "$PYTHON" ]; then
  PYTHON="$(command -v python3)"
fi
export PYTHONDONTWRITEBYTECODE=1
cd "$ROOT"
bash scripts/verify.sh
"$PYTHON" tests/viz-server/check_contracts.py
"$PYTHON" tests/viz-server/check_cypher_export.py
