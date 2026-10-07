#!/usr/bin/env bash
# Ontology Discovery Workflow — sync source rules to adapters
# 단일 소스(ontology-rules/core-workflow.md)에서 어댑터들로 동기화.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

SOURCE="$ROOT/ontology-rules/core-workflow.md"
KIRO_TARGET="$ROOT/.kiro/steering/ontology-discovery-rules/core-workflow.md"

if [ ! -f "$SOURCE" ]; then
  echo "ERROR: source rules not found: $SOURCE" >&2
  exit 1
fi

echo "Syncing $SOURCE → $KIRO_TARGET"

# Kiro에는 본문 그대로 복사 (header 1줄만 다르므로 awk로 변환)
{
  echo "# Ontology Discovery Workflow: Kiro Steering 진입점"
  echo
  echo "> Kiro CLI는 \`.kiro/steering/\` 아래 마크다운을 자동으로 컨텍스트에 로드한다."
  echo "> 이 파일은 \`ontology-rules/core-workflow.md\`(단일 소스)와 동기화된 복사본이다."
  echo "> 직접 수정하지 마세요. \`scripts/sync.sh\` 실행 시 덮어써집니다."
  echo
  # 원본 첫 헤더(`# Ontology Discovery Workflow — Core Rules`) 이후 본문 추가
  awk 'NR>1' "$SOURCE"
} > "$KIRO_TARGET"

echo "✅ Sync complete."
echo
echo "Note: ontology-rule-details/ 디렉토리는 워크플로우 실행 시 호스트 에이전트가"
echo "      ontology-rules/ontology-rule-details/에서 동적으로 로드하므로 별도 동기화 불필요."
