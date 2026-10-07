---
name: ontology-discovery
description: "데이터 간 관계성을 사용자와 발견하는 워크플로우. 도메인 스토리텔링 → 이벤트 스토밍 → 온톨로지 6단계로 진행하며, 단계마다 자동 시각화. 사용자가 '/onto-discover', 'ontology discovery', '온톨로지 발견', '도메인 모델링' 같은 문구를 쓰거나, 데이터 관계, 도메인 모델링, 이벤트 스토밍, 도메인 스토리텔링, 지식 그래프 작업을 요청할 때 사용한다."
---

# Ontology Discovery Workflow

이 스킬은 `ontology-rules/core-workflow.md`의 진행 규칙을 읽는 진입점이다.

## 진입 시 첫 액션 (강제)

스킬이 invoke되면 **다른 작업 전에** 다음을 수행한다:

1. **rule-details 경로 탐색** (다음 순서로 처음 존재하는 디렉토리 사용):
   - `<workspace>/.aidlc/ontology-rule-details/`
   - `<workspace>/.ontology/ontology-rule-details/`
   - `<workspace>/.kiro/steering/ontology-discovery-rules/ontology-rule-details/`
   - `<workspace>/ontology-rules/ontology-rule-details/`
   - 위 경로 모두 부재이면 사용자에게 `scripts/install.sh` 실행 안내 후 종료.

2. **`{rule-details}/../core-workflow.md` 본문을 읽는다.** 본문의 모든 MUST 규칙을 따른다.

3. **`common/` 12개 파일을 모두 로드**한다 (요약 금지, 본문 참조):
   - `process-overview.md`, `question-format-guide.md`, `stage-gate-protocol.md`,
     `visualization-protocol.md`, `persona-tracking.md`, `trace-link.md`,
     `session-continuity.md`, `content-validation.md`, `overconfidence-prevention.md`,
     `terminology.md`, `welcome-message.md`, `graph-health-review.md`

4. **Resume Protocol 수행** (`session-continuity.md` §1):
   - `<workspace>/ontology-docs/ontology-state.md` 존재 확인.
   - 존재하면 → 재개 안내 메시지 출력 후 사용자 응답 대기.
   - 부재하면 → `welcome-message.md` 출력 후 Phase 0 동의 요청.

## 동작 원칙

- 모든 phase별 동작은 `stages/{NN-...}.md` 본문 참조. 어댑터는 그 본문을 따른다.
- 산출물은 `<workspace>/ontology-docs/`.
- 시각화 서버는 `viz-server/server.py`.
- `audit.md`는 append-only, 모든 사용자 입력 원문 보존.
- 도메인 용어는 사용자 검증 없이 확정 표시 금지.
- 자료원(DB, API, 코드)은 읽기 전용, 변경 절대 금지.

## 본 어댑터를 직접 수정하지 마세요

이 SKILL.md는 단순 진입점이다. 워크플로우 로직 변경은 `ontology-rules/core-workflow.md`와 `ontology-rule-details/`에서. `scripts/sync.sh`로 어댑터들 자동 동기화.
