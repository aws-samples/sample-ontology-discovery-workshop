# Kiro Steering: Ontology Discovery Workflow

이 디렉토리는 Kiro CLI에서 Ontology Discovery Workflow를 자동 활성화하는 steering 파일을 담습니다.

## 동작

Kiro CLI는 워크스페이스의 `.kiro/steering/` 아래 마크다운 파일들을 자동으로 컨텍스트에 로드합니다. 따라서 이 파일들이 있는 워크스페이스에서 새 채팅을 시작하면 Kiro는 자동으로 워크플로우 규칙을 알고 있습니다.

## 검증

Kiro CLI에서 다음 명령으로 확인:

```
/context show
```

다음 항목이 보이면 정상:
- `.kiro/steering/ontology-discovery-rules/core-workflow.md`

## 트리거

사용자가 다음 중 하나를 입력하면 워크플로우 활성화:
- "Using ontology-discovery, ..."
- "온톨로지 발견 시작"
- "도메인 모델링"
- "이벤트 스토밍"

## 단일 소스

`core-workflow.md`는 `<workflow-root>/ontology-rules/core-workflow.md`의 복사본입니다. 두 파일은 `scripts/sync.sh`로 동기화됩니다. **이 파일을 직접 수정하지 마세요.** `ontology-rules/core-workflow.md`를 수정한 뒤 sync 스크립트를 실행하세요.

## 관련 파일

- `core-workflow.md`: 메인 진입 규칙 (자동 로드)
- 상세 규칙은 `<workspace>/ontology-rules/ontology-rule-details/`에 위치하며 워크플로우 실행 시 호스트 에이전트가 동적으로 로드합니다.

## Kiro Spec Mode와의 관계

본 워크플로우는 Kiro의 Spec Mode와 별개로 동작합니다. Kiro가 Spec Mode 전환을 제안해도 거절하고 워크플로우의 6-phase 구조를 따라야 합니다(`core-workflow.md` §0.6).
