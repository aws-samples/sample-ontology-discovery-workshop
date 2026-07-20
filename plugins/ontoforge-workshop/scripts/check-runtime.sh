#!/bin/sh
set -eu

PROJECT_ROOT=${1:-$(git rev-parse --show-toplevel)}

test -f "${PROJECT_ROOT}/requirements.txt" || {
  echo "not an OntoForge repository: ${PROJECT_ROOT}" >&2
  exit 1
}
test -f "${PROJECT_ROOT}/src/ontology_workshop/server.py" || {
  echo "missing OntoForge server source under ${PROJECT_ROOT}" >&2
  exit 1
}
test -x "${PROJECT_ROOT}/.venv/bin/python" || {
  echo "missing project virtualenv: ${PROJECT_ROOT}/.venv/bin/python" >&2
  exit 1
}

"${PROJECT_ROOT}/.venv/bin/python" -c \
  "import fastapi, kuzu, textual, uvicorn; print('OntoForge runtime dependencies: ok')"

if curl -fsS http://127.0.0.1:8000/workflow/state >/dev/null 2>&1; then
  echo "OntoForge server: reachable at http://127.0.0.1:8000"
else
  echo "OntoForge server: stopped"
fi
