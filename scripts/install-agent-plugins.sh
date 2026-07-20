#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

"${SCRIPT_DIR}/install-codex-plugin.sh"
"${SCRIPT_DIR}/install-claude-plugin.sh"
