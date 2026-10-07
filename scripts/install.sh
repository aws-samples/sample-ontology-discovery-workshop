#!/usr/bin/env bash
# Ontology Discovery Workflow — installer
# 사용 예:
#   bash install.sh --target=all
#   bash install.sh --target=claude-code --workspace=/path/to/project
#   bash install.sh --target=kiro --no-libs

set -euo pipefail

# ============================================================
# 기본값
# ============================================================
TARGET="all"
WORKSPACE="$(pwd)"
DOWNLOAD_LIBS="ask"
ADD_HOOK="ask"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKFLOW_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ============================================================
# 인자 파싱
# ============================================================
for arg in "$@"; do
  case "$arg" in
    --target=*) TARGET="${arg#*=}" ;;
    --workspace=*) WORKSPACE="${arg#*=}"
                   # tilde expansion (bash는 --foo=~/... 형태에서 자동 확장 안 함)
                   WORKSPACE="${WORKSPACE/#\~/$HOME}" ;;
    --no-libs) DOWNLOAD_LIBS="no" ;;
    --with-libs) DOWNLOAD_LIBS="yes" ;;
    --no-hook) ADD_HOOK="no" ;;
    --with-hook) ADD_HOOK="yes" ;;
    -h|--help)
      cat <<EOF
Ontology Discovery Workflow installer

Usage: bash install.sh [options]

Options:
  --target=<claude-code|kiro|all>    설치 대상 (기본: all)
  --workspace=<path>                  대상 디렉토리 (기본: 현재 디렉토리)
  --with-libs / --no-libs             Cytoscape.js 다운로드 여부
  --with-hook / --no-hook             SessionStart hook 추가 여부
  -h, --help                          도움말
EOF
      exit 0
      ;;
    *) echo "Unknown arg: $arg" >&2; exit 2 ;;
  esac
done

# ============================================================
# 검증
# ============================================================
if [ ! -d "$WORKFLOW_ROOT/ontology-rules" ]; then
  echo "ERROR: $WORKFLOW_ROOT/ontology-rules not found. Wrong workflow root?" >&2
  exit 3
fi
if [ ! -d "$WORKSPACE" ]; then
  echo "ERROR: workspace dir not found: $WORKSPACE" >&2
  exit 3
fi

case "$TARGET" in
  claude-code|kiro|all) ;;
  *) echo "ERROR: invalid --target: $TARGET (use claude-code|kiro|all)" >&2; exit 2 ;;
esac

echo "Ontology Discovery Workflow Installer"
echo "  workflow root: $WORKFLOW_ROOT"
echo "  workspace:     $WORKSPACE"
echo "  target:        $TARGET"
echo

# ============================================================
# ontology-rules/ 복사 (단일 소스)
# ============================================================
echo "[1/4] Copying ontology-rules/ to workspace..."
mkdir -p "$WORKSPACE/ontology-rules"
if [ "$(cd "$WORKSPACE" && pwd)" != "$WORKFLOW_ROOT" ]; then
  cp -R "$WORKFLOW_ROOT/ontology-rules/." "$WORKSPACE/ontology-rules/"
fi
echo "  → $WORKSPACE/ontology-rules/"

# ============================================================
# viz-server/ 복사
# ============================================================
echo "[2/4] Copying viz-server/ to workspace..."
mkdir -p "$WORKSPACE/viz-server"
if [ "$(cd "$WORKSPACE" && pwd)" != "$WORKFLOW_ROOT" ]; then
  tar --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' \
    -C "$WORKFLOW_ROOT/viz-server" -cf - . | tar -C "$WORKSPACE/viz-server" -xf -
  mkdir -p "$WORKSPACE/scripts"
  cp "$WORKFLOW_ROOT/scripts/serve.sh" "$WORKFLOW_ROOT/scripts/verify.sh" "$WORKSPACE/scripts/"
fi
echo "  → $WORKSPACE/viz-server/"

# ============================================================
# 라이브러리 다운로드
# ============================================================
LIB_DIR="$WORKSPACE/viz-server/lib"
NEED_LIBS=()
[ -f "$LIB_DIR/cytoscape.min.js" ] || NEED_LIBS+=("cytoscape.min.js")
[ -f "$LIB_DIR/layout-base.min.js" ] || NEED_LIBS+=("layout-base.min.js")
[ -f "$LIB_DIR/cose-base.min.js" ] || NEED_LIBS+=("cose-base.min.js")
[ -f "$LIB_DIR/cytoscape-fcose.min.js" ] || NEED_LIBS+=("cytoscape-fcose.min.js")
[ -f "$LIB_DIR/cytoscape-cose-bilkent.min.js" ] || NEED_LIBS+=("cytoscape-cose-bilkent.min.js")

if [ ${#NEED_LIBS[@]} -gt 0 ]; then
  if [ "$DOWNLOAD_LIBS" = "ask" ]; then
    echo
    echo "다음 라이브러리가 viz-server/lib/에 없습니다:"
    printf '  - %s\n' "${NEED_LIBS[@]}"
    read -r -p "지금 다운로드할까요? [Y/n] " ans || ans="n"
    case "$ans" in
      [Nn]*) DOWNLOAD_LIBS="no" ;;
      *) DOWNLOAD_LIBS="yes" ;;
    esac
  fi

  if [ "$DOWNLOAD_LIBS" = "yes" ]; then
    if ! command -v curl >/dev/null 2>&1; then
      echo "WARN: curl not found, skipping library download." >&2
    else
      echo "[3/4] Downloading libraries..."
      mkdir -p "$LIB_DIR"
      [ ! -f "$LIB_DIR/cytoscape.min.js" ] && \
        curl -fsSL -o "$LIB_DIR/cytoscape.min.js" \
          "https://unpkg.com/cytoscape@3.28.1/dist/cytoscape.min.js" || true
      [ ! -f "$LIB_DIR/layout-base.min.js" ] && \
        curl -fsSL -o "$LIB_DIR/layout-base.min.js" \
          "https://unpkg.com/layout-base@2.0.1/layout-base.js" || true
      # cose-base는 fcose와 cose-bilkent의 공통 의존성. extension보다 먼저 로드되어야 함.
      [ ! -f "$LIB_DIR/cose-base.min.js" ] && \
        curl -fsSL -o "$LIB_DIR/cose-base.min.js" \
          "https://unpkg.com/cose-base@2.2.0/cose-base.js" || true
      [ ! -f "$LIB_DIR/cytoscape-fcose.min.js" ] && \
        curl -fsSL -o "$LIB_DIR/cytoscape-fcose.min.js" \
          "https://unpkg.com/cytoscape-fcose@2.2.0/cytoscape-fcose.js" || true
      [ ! -f "$LIB_DIR/cytoscape-cose-bilkent.min.js" ] && \
        curl -fsSL -o "$LIB_DIR/cytoscape-cose-bilkent.min.js" \
          "https://unpkg.com/cytoscape-cose-bilkent@4.1.0/cytoscape-cose-bilkent.js" || true
      echo "  Libraries in $LIB_DIR"
    fi
  else
    echo "Skipped library download. See viz-server/lib/README.md for manual download."
  fi
else
  echo "[3/4] Libraries already present, skipping."
fi

# ============================================================
# 어댑터 설치
# ============================================================
echo "[4/4] Installing adapters (target=$TARGET)..."

install_claude_code() {
  echo "  → Installing Claude Code adapter..."
  if [ "$(cd "$WORKSPACE" && pwd)" = "$WORKFLOW_ROOT" ]; then return; fi
  mkdir -p "$WORKSPACE/.claude/skills/ontology-discovery"
  mkdir -p "$WORKSPACE/.claude/commands"
  cp "$WORKFLOW_ROOT/.claude/skills/ontology-discovery/SKILL.md" \
    "$WORKSPACE/.claude/skills/ontology-discovery/SKILL.md"
  cp "$WORKFLOW_ROOT/.claude/commands/onto-discover.md" \
    "$WORKSPACE/.claude/commands/onto-discover.md"
}

install_kiro() {
  echo "  → Installing Kiro steering..."
  if [ "$(cd "$WORKSPACE" && pwd)" = "$WORKFLOW_ROOT" ]; then return; fi
  mkdir -p "$WORKSPACE/.kiro/steering/ontology-discovery-rules"
  cp "$WORKFLOW_ROOT/.kiro/steering/ontology-discovery-rules/core-workflow.md" \
    "$WORKSPACE/.kiro/steering/ontology-discovery-rules/core-workflow.md"
  cp "$WORKFLOW_ROOT/.kiro/steering/ontology-discovery-rules/README.md" \
    "$WORKSPACE/.kiro/steering/ontology-discovery-rules/README.md"
}

install_agents() {
  echo "  → Installing AGENTS.md..."
  if [ -f "$WORKSPACE/AGENTS.md" ]; then
    echo "    AGENTS.md already exists; appending header link only."
    if ! grep -q "Ontology Discovery Workflow" "$WORKSPACE/AGENTS.md" 2>/dev/null; then
      {
        echo
        echo "## Ontology Discovery Workflow"
        echo
        echo "Refer to ontology-rules/core-workflow.md for the full ontology-discovery workflow."
      } >> "$WORKSPACE/AGENTS.md"
    fi
  else
    cp "$WORKFLOW_ROOT/AGENTS.md" "$WORKSPACE/AGENTS.md"
  fi
}

case "$TARGET" in
  claude-code) install_claude_code ;;
  kiro)        install_kiro ;;
  all)         install_claude_code; install_kiro; install_agents ;;
esac

# ============================================================
# Hook 설치 (Claude Code 한정)
# ============================================================
if [ "$TARGET" = "claude-code" ] || [ "$TARGET" = "all" ]; then
  if [ "$ADD_HOOK" = "ask" ]; then
    echo
    echo "Claude Code SessionStart hook을 추가하면 새 세션 시작 시"
    echo "ontology-state.md와 audit.md 마지막 50줄을 자동으로 컨텍스트에 주입합니다."
    echo "Resume Protocol은 hook 없이도 동작합니다(첫 액션이 state 확인이므로)."
    read -r -p "hook을 추가할까요? [y/N] " ans || ans="n"
    case "$ans" in
      [Yy]*) ADD_HOOK="yes" ;;
      *)     ADD_HOOK="no" ;;
    esac
  fi
  if [ "$ADD_HOOK" = "yes" ]; then
    SETTINGS="$WORKSPACE/.claude/settings.json"
    if [ -f "$SETTINGS" ]; then
      echo "  $SETTINGS already exists. Please merge .claude/settings.json.example manually."
      cp "$WORKFLOW_ROOT/.claude/settings.json.example" "$WORKSPACE/.claude/settings.json.example"
    else
      cp "$WORKFLOW_ROOT/.claude/settings.json.example" "$SETTINGS"
      echo "  → $SETTINGS"
    fi
  fi
fi

# ============================================================
# 안내
# ============================================================
echo
echo "✅ 설치 완료."
echo
echo "다음 단계:"
echo "  1. cd $WORKSPACE"
case "$TARGET" in
  claude-code|all)
    echo "  2. Claude Code: 새 세션에서 '/onto-discover' 실행"
    ;;
esac
case "$TARGET" in
  kiro|all)
    echo "  3. Kiro CLI: 새 채팅에서 'Using ontology-discovery, ...' 입력"
    ;;
esac
echo
echo "산출물 위치: $WORKSPACE/ontology-docs/ (워크플로우 시작 시 자동 생성)"
echo
echo "읽기 전용 Cypher 조회 엔진 설치 (선택, Python 3.10+):"
echo "  python3 -m venv '$WORKSPACE/viz-server/.venv'"
echo "  '$WORKSPACE/viz-server/.venv/bin/python' -m pip install -r '$WORKSPACE/viz-server/requirements.txt'"
echo "서버 실행: bash '$WORKSPACE/scripts/serve.sh'"
