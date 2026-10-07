---
description: 업무 시나리오와 자료를 바탕으로 그래프 모델을 만드는 워크숍을 시작하거나 재개합니다.
---

# /onto-discover

데이터 간 관계성을 사용자와 발견하는 6단계 워크플로우를 시작/재개합니다.

## 동작

1. `ontology-discovery` 스킬을 invoke합니다.
2. 스킬이 Resume Protocol을 수행:
   - `<workspace>/ontology-docs/ontology-state.md`가 있으면 → 재개 안내.
   - 없으면 → 새 워크플로우(welcome message + Phase 0 동의 요청).

## 6단계

| # | Phase | 자동 시각화 |
|---|---|---|
| 0 | Workspace Detection | skip |
| 1 | Discovery Intent & Scope | skip |
| 2 | Data Structure Survey (brownfield 자동 스캔) | sources × candidates |
| 3 | Domain Storytelling | persona-centered story flow |
| 4 | Event Storming (3 levels) | colored timeline + aggregates |
| 5 | Ontology Synthesis | entity-relationship + traces |

각 phase는 stage gate에서 멈춥니다: `Continue / Request Changes / Re-visualize` (Phase 5는 `Drill back to Phase 4` 추가).

## 산출물

- `<workspace>/ontology-docs/`
  - `ontology-state.md` (진행 상태 YAML)
  - `audit.md` (append-only 사용자 입력 원문)
  - `01-intent/` ~ `05-ontology/` (단계별 마크다운, JSON)
  - `viz-runtime/` (시각화 통합 데이터)

## 안전 규칙

- 자료원(DB, API, 코드)은 **읽기 전용**.
- 도메인 용어는 사용자 검증 없이 확정 표시 금지.
- `audit.md`는 절대 덮어쓰지 않음.
- compact, 세션 종료 후 첫 메시지에 Resume Protocol로 재개.

## 자세한 규칙

`ontology-rules/core-workflow.md`와 `ontology-rules/ontology-rule-details/` 참조.
