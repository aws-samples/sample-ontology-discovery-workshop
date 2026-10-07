#!/usr/bin/env bash
# Ontology Discovery Workflow — installation verifier
# 필수 파일 존재 여부, 어댑터 일관성, viz-server 라이브러리 존재 등을 검사.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORKSPACE="${1:-$ROOT}"
WORKSPACE="${WORKSPACE/#\~/$HOME}"

PASS=0
FAIL=0
WARN=0

ok() { echo "  ✓ $1"; PASS=$((PASS+1)); }
ng() { echo "  ✗ $1"; FAIL=$((FAIL+1)); }
wn() { echo "  ⚠ $1"; WARN=$((WARN+1)); }

echo "Verifying: $WORKSPACE"
echo

# ============================================================
echo "[1/5] ontology-rules/ 단일 소스"
# ============================================================
RULES="$WORKSPACE/ontology-rules"
if [ -d "$RULES" ]; then
  ok "ontology-rules/ exists"
else
  ng "ontology-rules/ missing"
fi

[ -f "$RULES/core-workflow.md" ] && ok "core-workflow.md" || ng "core-workflow.md missing"
[ -f "$RULES/VERSION" ] && ok "VERSION" || wn "VERSION missing"

COMMON_FILES=(
  process-overview.md
  question-format-guide.md
  stage-gate-protocol.md
  visualization-protocol.md
  persona-tracking.md
  trace-link.md
  session-continuity.md
  content-validation.md
  overconfidence-prevention.md
  terminology.md
  welcome-message.md
  graph-health-review.md
)
for f in "${COMMON_FILES[@]}"; do
  if [ -f "$RULES/ontology-rule-details/common/$f" ]; then
    ok "common/$f"
  else
    ng "common/$f missing"
  fi
done

STAGE_FILES=(
  00-workspace-detection.md
  01-discovery-intent.md
  02-data-structure-survey.md
  03-domain-storytelling.md
  04-event-storming.md
  05-ontology-synthesis.md
)
for f in "${STAGE_FILES[@]}"; do
  if [ -f "$RULES/ontology-rule-details/stages/$f" ]; then
    ok "stages/$f"
  else
    ng "stages/$f missing"
  fi
done

# ============================================================
echo
echo "[2/5] viz-server/"
# ============================================================
VIZ="$WORKSPACE/viz-server"
[ -f "$VIZ/server.py" ] && ok "server.py" || ng "server.py missing"
[ -f "$VIZ/index.html" ] && ok "index.html" || ng "index.html missing"
[ -f "$VIZ/app.js" ] && ok "app.js" || ng "app.js missing"
[ -f "$VIZ/styles.css" ] && ok "styles.css" || ng "styles.css missing"

LIB_FILES=(cytoscape.min.js layout-base.min.js cose-base.min.js cytoscape-fcose.min.js cytoscape-cose-bilkent.min.js)
for f in "${LIB_FILES[@]}"; do
  if [ -f "$VIZ/lib/$f" ]; then
    ok "lib/$f"
  else
    wn "lib/$f missing — run scripts/install.sh --with-libs"
  fi
done

for f in model.py quality.py query_engine.py cypher_export.py store.py agent.py requirements.txt; do
  [ -f "$VIZ/$f" ] && ok "$f" || ng "$f missing"
done

if command -v node >/dev/null 2>&1; then
  if node --check "$VIZ/app.js"; then ok "app.js syntax"; else ng "app.js syntax"; fi
fi

if [ -x "$VIZ/.venv/bin/python" ]; then
  if "$VIZ/.venv/bin/python" -c 'import kuzu; assert kuzu.__version__ == "0.11.3"' 2>/dev/null; then
    ok "optional Cypher engine: Kuzu 0.11.3"
  else
    wn "Cypher engine unavailable or unverified version"
  fi
else
  echo "  (optional Cypher engine not installed; visualization and quality review remain available)"
fi

# Python 확인
if command -v python3 >/dev/null 2>&1; then
  if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
    ok "python3 available: $(python3 --version 2>&1)"
  else
    ng "Python 3.10+ is required"
  fi
else
  ng "python3 not found — viz-server cannot run"
fi

# ============================================================
echo
echo "[3/5] Adapters"
# ============================================================
[ -f "$WORKSPACE/.claude/skills/ontology-discovery/SKILL.md" ] \
  && ok ".claude/skills/ontology-discovery/SKILL.md" \
  || wn ".claude/ adapter missing"

[ -f "$WORKSPACE/.claude/commands/onto-discover.md" ] \
  && ok ".claude/commands/onto-discover.md" \
  || wn ".claude/commands/ missing"

[ -f "$WORKSPACE/.kiro/steering/ontology-discovery-rules/core-workflow.md" ] \
  && ok ".kiro/steering/ontology-discovery-rules/core-workflow.md" \
  || wn ".kiro/steering/ adapter missing"

[ -f "$WORKSPACE/AGENTS.md" ] \
  && ok "AGENTS.md" \
  || wn "AGENTS.md missing"

# ============================================================
echo
echo "[4/5] Workflow state (있으면 검사)"
# ============================================================
STATE="$WORKSPACE/ontology-docs/ontology-state.md"
if [ -f "$STATE" ]; then
  ok "ontology-state.md exists"
  if grep -q "current_phase:" "$STATE" 2>/dev/null; then
    ok "current_phase field present"
  else
    ng "current_phase field missing in state"
  fi
  if grep -q "next_immediate_action:" "$STATE" 2>/dev/null; then
    ok "next_immediate_action field present"
  else
    ng "next_immediate_action field missing"
  fi
else
  echo "  (no state file — workflow not yet started; OK)"
fi

# ============================================================
echo
echo "[5/5] Adapter consistency"
# ============================================================
if [ -f "$RULES/core-workflow.md" ] && [ -f "$WORKSPACE/.kiro/steering/ontology-discovery-rules/core-workflow.md" ]; then
  # 본문 비교: ontology-rules의 §1 phase 표가 kiro 어댑터에도 있는지 단순 grep
  if grep -q "Workspace Detection" "$WORKSPACE/.kiro/steering/ontology-discovery-rules/core-workflow.md"; then
    ok "Kiro adapter has phase table"
  else
    wn "Kiro adapter may be out of sync. Run scripts/sync.sh"
  fi
fi

# ============================================================
echo
echo "============================================================"
echo "Result: $PASS passed, $WARN warnings, $FAIL failures"
if [ "$FAIL" -gt 0 ]; then
  echo "Status: ❌ FAIL"
  exit 1
fi
if [ "$WARN" -gt 0 ]; then
  echo "Status: ⚠️  PASS (with warnings)"
else
  echo "Status: ✅ PASS"
fi
