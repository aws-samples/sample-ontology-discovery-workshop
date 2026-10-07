# AGENTS.md: Ontology Discovery Workflow

> 이 파일은 Codex / GitHub Copilot CLI / 기타 에이전트의 진입점이다.
> Claude Code는 `.claude/skills/ontology-discovery/SKILL.md`를, Kiro CLI는 `.kiro/steering/ontology-discovery-rules/`를 사용한다.

## 워크숍 개요

업무 시나리오와 자료를 바탕으로 그래프 모델을 만드는 워크숍이다. 로컬 AI가 모델을 작성하고 사용자는 웹에서 확인한다.

활성화 트리거:
- 사용자가 "/onto-discover", "ontology discovery", "온톨로지 발견", "도메인 모델링", "이벤트 스토밍", "도메인 스토리텔링" 등의 키워드 사용
- 자연어 트리거: "Using ontology-discovery, ..."

## 진입 시 첫 액션 (강제)

워크플로우 트리거 감지 시 **다른 작업 전에**:

1. **rule-details 경로 탐색**:
   - `<workspace>/.aidlc/ontology-rule-details/`
   - `<workspace>/.ontology/ontology-rule-details/`
   - `<workspace>/.kiro/steering/ontology-discovery-rules/ontology-rule-details/`
   - `<workspace>/ontology-rules/ontology-rule-details/`
   - 첫 존재 경로 사용. 모두 부재 시 `scripts/install.sh` 안내 후 종료.

2. **`{rule-details}/../core-workflow.md` 로드**, 모든 MUST 규칙 준수.

3. **`common/` 12개 파일 로드**:
   - process-overview, question-format-guide, stage-gate-protocol,
     visualization-protocol, persona-tracking, trace-link,
     session-continuity, content-validation, overconfidence-prevention,
     terminology, welcome-message, graph-health-review

4. **Resume Protocol** (`session-continuity.md` §1):
   - `<workspace>/ontology-docs/ontology-state.md` 존재 확인.
   - 존재 → 재개 안내 메시지 출력 + 사용자 응답 대기.
   - 부재 → welcome-message 출력 + Phase 0 동의 요청.

## 안전 규칙

- 모든 자료원(DB, API, 코드) 접근은 **읽기 전용**.
- 도메인 용어는 사용자 검증 없이 확정 표시 금지.
- `audit.md`는 append-only.
- compact, 세션 종료 후 첫 메시지는 Resume Protocol.

## 6단계

| # | Phase | Always? |
|---|---|---|
| 0 | Workspace Detection | ✓ |
| 1 | Discovery Intent & Scope | ✓ |
| 2 | Data Structure Survey | ✓ (brownfield 자동 스캔) |
| 3 | Domain Storytelling | ✓ |
| 4 | Event Storming (3 levels) | ✓ |
| 5 | Ontology Synthesis | ✓ |

각 단계 종료 시 `Continue / Request Changes / Re-visualize` 게이트.

## 시각화

`viz-server/server.py`는 Python 3.10 이상에서 실행한다. 시각화는 표준 라이브러리를 사용하고 Cypher 조회에는 Kuzu를 설치한다. 포트 5173~5183을 탐색하며 `127.0.0.1`에 바인딩한다. 실행 시 PID와 URL을 출력한다.

## 산출물

- `<workspace>/ontology-docs/{ontology-state.md, audit.md, 01-intent/, ..., 05-ontology/, viz-runtime/}`

## 자세한 규칙

`ontology-rules/core-workflow.md`와 `ontology-rules/ontology-rule-details/` 본문을 따른다.

## 라이센스

MIT-0. awslabs/aidlc-workflows의 패턴(3-phase, opt-in extension, audit, state, question file)을 참조.
