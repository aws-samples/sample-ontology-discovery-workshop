#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)
SOURCE=${ONTOFORGE_MARKETPLACE_SOURCE:-${PROJECT_ROOT}}
MARKETPLACE=ontoforge
PLUGIN=ontoforge-workshop

if ! claude plugin marketplace list --json 2>/dev/null \
    | grep -Eq "\"name\"[[:space:]]*:[[:space:]]*\"${MARKETPLACE}\""; then
  claude plugin marketplace add "${SOURCE}" --scope user
else
  claude plugin marketplace update "${MARKETPLACE}"
fi

if claude plugin list --json 2>/dev/null \
    | grep -Eq "\"id\"[[:space:]]*:[[:space:]]*\"${PLUGIN}@${MARKETPLACE}\""; then
  claude plugin update "${PLUGIN}@${MARKETPLACE}"
else
  claude plugin install "${PLUGIN}@${MARKETPLACE}" --scope user
fi
