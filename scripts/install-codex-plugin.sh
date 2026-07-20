#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)
SOURCE=${ONTOFORGE_MARKETPLACE_SOURCE:-${PROJECT_ROOT}}
MARKETPLACE=ontoforge
PLUGIN=ontoforge-workshop

if ! codex plugin marketplace list --json 2>/dev/null \
    | grep -Eq "\"name\"[[:space:]]*:[[:space:]]*\"${MARKETPLACE}\""; then
  codex plugin marketplace add "${SOURCE}"
fi

codex plugin add "${PLUGIN}@${MARKETPLACE}"
