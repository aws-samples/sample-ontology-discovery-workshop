#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${ONTOLOGY_PYTHON:-$ROOT/viz-server/.venv/bin/python}"
if [ ! -x "$PYTHON" ]; then
  PYTHON="$(command -v python3)"
fi
if [ "$#" -eq 0 ]; then
  exec "$PYTHON" "$ROOT/viz-server/server.py" --data-dir "$ROOT/ontology-docs/viz-runtime"
fi
exec "$PYTHON" "$ROOT/viz-server/server.py" "$@"
