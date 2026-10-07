# Phase 4: Event Storming (3 Levels)

Alberto Brandolini의 Event Storming. 도메인 이벤트 → 커맨드, 정책, 읽기모델 → 애그리거트, 바운디드 컨텍스트의 3-level 진행. 각 레벨에 mini-gate를 둔다.

**관련 규칙:** `../common/terminology.md` §3, §6 (용어, 색상), `../common/question-format-guide.md` (질문 형식), `../common/stage-gate-protocol.md` §2 (mini-gate), `../common/visualization-protocol.md` §7 (시각화 검증), `../common/persona-tracking.md` (페르소나 ID), `../common/trace-link.md` (이벤트→스토리 추적), `../common/overconfidence-prevention.md` (자동 추출 candidate 표시).

---

## 1. Prerequisites

- Phase 3 완료, stories, personas, glossary 존재.
- ontology-state.md `current_phase: 04-eventstorming`.

---

## 2. Question File

**파일:** `<workspace>/ontology-docs/04-eventstorming/eventstorming-questions.md`

3 레벨을 한 파일에 묶음. 각 레벨은 mini-gate에서 답변 검증 → 다음 레벨 질문 활성화.

### 2.1 Level 4a: Big Picture

```markdown
# Phase 4: Event Storming Questions

## Level 4a: Big Picture

> 자동 추출된 도메인 이벤트 후보를 검토하고 누락, 중복, 시간순서를 확인합니다.

### 자동 추출 결과 (검토용)
{candidate events 목록 자동 생성, 시간순 정렬 시도}

- [candidate] E-cron-fired: 시각: 02:00 (story-001)
- [candidate] E-settlement-executed: story-001 step 1
- [candidate] E-settlement-amount-calculated: story-001 step 2
- [candidate] E-settlement-report-generated: story-001 step 3
- [candidate] E-merchant-notified: story-001 step 4
- ...

### Question 1
누락된 도메인 이벤트가 있나요?

(예: "정산 실패", "환불 발생", "정산 보류" 등 사실 발생을 과거형으로)

[Answer]:


### Question 2
중복 또는 잘못된 이벤트가 있나요?

(예: "E-cron-fired는 도메인 이벤트가 아닌 시스템 트리거이므로 제거")

[Answer]:


### Question 3
**외부 시스템에서 발생하는 이벤트**가 있나요?

(예: "결제 게이트웨이로부터 결제 승인됨", "은행으로부터 입금 확인됨")

[Answer]:


### Question 4
**시간성 핫스팟**: 논쟁, 불확실한 시간 관련 사항이 있나요?

(예: "정산 배치 후 환불이 들어오면 정산을 되돌리는가?", "야간에 결제 발생 시 어느 날 정산에 포함?")

[Answer]:
```

Level 4a mini-gate 통과 후 4b 질문 활성화.

### 2.2 Level 4b: Process Modeling

```markdown
## Level 4b: Process Modeling

> Big Picture 통과 후 진행. 각 이벤트를 일으키는 커맨드, 정책, 읽기모델을 식별합니다.

### 자동 추출 결과 (검토용)
- [candidate] C-execute-settlement → E-settlement-executed (story-001 step 1)
- [candidate] C-calculate-settlement-amount → E-settlement-amount-calculated
- [candidate] Pol-on-payment-failure → C-retry-payment (story-002에서 추정)
- [candidate] RM-today-settlement-summary (story-001 P-pgops가 보는 화면)
- ...

### Question 5
각 이벤트를 일으키는 **커맨드**가 맞게 식별되었나요?
누락 또는 잘못된 매핑이 있다면 알려주세요.

[Answer]:


### Question 6
**자동 정책(Policy)**: 한 이벤트가 자동으로 다른 커맨드를 발생시키는 규칙이 있나요?

(예: "결제 실패 → 자동 3회 재시도", "정산 완료 → 회계 시스템 자동 전송")

[Answer]:


### Question 7
**읽기모델(Read Model)**: 의사결정, UI에 필요한 데이터 뷰는?

(예: "오늘 정산 요약 대시보드", "미정산 거래 목록", "가맹점별 정산 이력")

[Answer]:


### Question 8
**액터 확인**: Phase 3 페르소나가 모든 커맨드에 매핑되나요?
빠진 액터가 있다면 알려주세요.

[Answer]:
```

### 2.3 Level 4c: Software Design

```markdown
## Level 4c: Software Design

> Process Modeling 통과 후 진행. 애그리거트와 바운디드 컨텍스트를 식별합니다.

### 자동 추출 결과 (검토용)
- [candidate] Agg-Settlement: [E-settlement-executed, E-settlement-amount-calculated, E-settlement-report-generated]
- [candidate] Agg-Payout: [E-payout-initiated, E-payout-completed]
- [candidate] BC-Settlement: [Agg-Settlement, Agg-Payout]
- [candidate] BC-Payment: [E-payment-authorized, E-payment-failed] (외부 시스템)

### Question 9
**애그리거트 후보**(같이 생성, 변경되어야 하는 이벤트 묶음)를 검토해주세요.
누락, 잘못된 묶음이 있나요?

[Answer]:


### Question 10
**바운디드 컨텍스트 경계 신호**: 같은 용어가 다른 의미로 쓰이는 곳이 있나요?

자동 발견된 후보:
- "정산"이 BC-Settlement(가맹점-PG)와 BC-Payment(PG-카드사)에서 다른 의미로 사용 가능: 검증 필요

(누락, 잘못된 경계가 있다면 알려주세요)

[Answer]:


### Question 11
**애그리거트 이름이 도메인 언어로 적절한가요?**

(예: "Agg-Settlement → '정산 묶음', '정산 사이클' 중 어느 표현이 자연스러운가?")

[Answer]:
```

각 레벨 mini-gate에 ontology-state.md 갱신:
- 4a 진행 중 `current_step: gathering` (sub-step: `level-4a/awaiting-answers` 등으로 next_immediate_action에 명시).

---

## 3. Validation

각 레벨별로:

### Level 4a
- Q1 누락 이벤트가 페르소나, 스토리와 무관하면 → "이 이벤트는 어느 시나리오에 속하나요?"
- Q2 제거 요청 이벤트가 다른 이벤트의 trigger면 → "이 이벤트를 제거하면 후속 이벤트도 영향. 정말 제거?"
- Q4 핫스팟이 비어있으면 → "정말 모든 시간 관련 사항이 명확한가요?" (선택적)

### Level 4b
- Q5 커맨드가 액터(페르소나) 없이 단독이면 → "이 커맨드를 누가/무엇이 일으키나요?"
- Q6 정책의 trigger 이벤트와 emit 커맨드가 모두 정의되어 있는지.
- Q7 읽기모델의 데이터 출처가 candidate-inventory와 매칭되는지.

### Level 4c
- Q9 애그리거트 안의 이벤트들이 같은 트랜잭션 경계 내에서 일관성 유지 가능한지.
- Q10 컨텍스트 경계가 발견되면 glossary에 컨텍스트별 용어 분리 필요.

---

## 4. Artifacts (레벨별로 누적)

### Level 4a 산출
- `04-eventstorming/events.md`
- `04-eventstorming/hotspots.md` (Q4 + 후속 발견)
- `04-eventstorming/viz/event-flow.json` (시간순 좌→우)

### Level 4b 산출
- `04-eventstorming/commands.md`
- `04-eventstorming/policies.md`
- `04-eventstorming/read-models.md`
- 기존 viz/event-flow.json 갱신 (커맨드, 정책, 읽기모델 추가)

### Level 4c 산출
- `04-eventstorming/aggregates.md`
- `04-eventstorming/bounded-contexts.md`
- glossary.md 누적 갱신 (컨텍스트별 용어 분리)
- viz/event-flow.json 최종(애그리거트 그룹, 컨텍스트 컴파운드)

### 4.1 events.md 형식

```markdown
# Domain Events

## E-settlement-executed
- **이름:** 정산 실행됨
- **시간순:** 02:00 daily
- **트리거 커맨드:** C-execute-settlement
- **출처 시나리오:** story-001
- **trace_links:** [story-001, cand-Settlement]
- **외부/내부:** 내부
- **속성:** settlement_id, executed_at, executor (P-system-batch)

## E-payment-authorized
- **이름:** 결제 승인됨
- **시간순:** 결제 발생 시점 (수시)
- **외부/내부:** 외부 (결제 게이트웨이)
- **trace_links:** [story-002]
- ...
```

### 4.2 commands.md 형식

```markdown
# Commands

## C-execute-settlement
- **이름:** 정산 실행하라
- **수행자:** P-system-batch (자동, cron 02:00)
- **결과 이벤트:** E-settlement-executed
- **선행 조건:** 어제 결제 거래 데이터 확정
- **trace_links:** [story-001]
```

### 4.3 policies.md 형식

```markdown
# Policies

## Pol-payment-failure-retry
- **이름:** 결제 실패 자동 재시도
- **트리거:** E-payment-failed
- **emit:** C-retry-payment
- **조건:** 재시도 카운트 < 3
- **trace_links:** [story-002]
```

### 4.4 read-models.md 형식

```markdown
# Read Models

## RM-today-settlement-summary
- **이름:** 오늘 정산 요약
- **사용자:** P-pgops 대시보드
- **데이터 출처:** Agg-Settlement
- **갱신 주기:** 실시간
- **trace_links:** [story-001]
```

### 4.5 aggregates.md

```markdown
# Aggregates

## Agg-Settlement
- **이름:** 정산
- **루트 엔티티:** Settlement (cand-Settlement에서 진화)
- **포함 이벤트:** E-settlement-executed, E-settlement-amount-calculated, E-settlement-report-generated, E-merchant-notified
- **불변식(invariants):**
  - 정산 금액 = 거래 합계 - 수수료
  - 한 정산은 한 정산 주기에만 속함
- **trace_links:** [story-001, cand-Settlement]
```

### 4.6 bounded-contexts.md

```markdown
# Bounded Contexts

## BC-Settlement
- **이름:** 정산 컨텍스트
- **포함 애그리거트:** Agg-Settlement, Agg-Payout
- **언어:**
  - "정산" = 가맹점-PG 간 일일 정산 처리
  - "수수료" = PG가 가맹점에서 차감하는 수수료
- **외부 컨텍스트와의 관계:**
  - BC-Payment: customer-supplier (BC-Payment가 결제 데이터 공급)

## BC-Payment (외부)
- **이름:** 결제 컨텍스트 (외부 시스템)
- **포함 이벤트:** E-payment-authorized, E-payment-failed (외부 시스템에서 발생, 본 도메인은 수신만)
- **언어:**
  - "정산" = PG-카드사 간 정산 (다른 의미!)
  - "거래" = 단일 결제 거래
- **trace_links:** [story-002, hotspot-1]
```

### 4.7 hotspots.md

```markdown
# Hotspots (논쟁점, 미해결)

## H1: 환불의 정산 처리
- **출처:** Q4, story-001
- **문제:** 정산 배치 후 환불이 들어오면 정산을 되돌리는가, 다음 정산에서 차감하는가?
- **영향:** Agg-Settlement 불변식, 회계 시스템 인터페이스
- **권고:** Phase 5 ontology에서 "Settlement Cycle" 개념으로 풀 수 있을 듯.

## H2: 정산 vs 정산 (동음이의)
- **출처:** Q10
- **문제:** BC-Settlement와 BC-Payment에서 "정산"이 다른 의미.
- **결정:** glossary.md에 컨텍스트별로 분리 등재.
```

### 4.8 viz/event-flow.json

시간순 좌→우 레이아웃을 위해 노드의 `position.x`를 시간 순서로 설정. Cytoscape `preset` 레이아웃 사용 가능.

```json
{
  "metadata": {
    "phase": "04-eventstorming",
    "rendered_at": "...",
    "personas_index": ["P-system-batch", "P-pgops", "P-merchant"],
    "available_filters": ["persona", "bounded_context", "aggregate", "trace_link"],
    "available_layouts": ["preset", "fcose", "cose-bilkent"]
  },
  "elements": {
    "nodes": [
      {
        "data": {
          "id": "BC-Settlement",
          "label": "BC: 정산",
          "type": "bounded-context",
          "trace_links": ["story-001"],
          "phase_introduced": "04"
        },
        "classes": "bounded-context"
      },
      {
        "data": {
          "id": "Agg-Settlement",
          "label": "Agg: 정산",
          "type": "aggregate",
          "parent": "BC-Settlement",
          "trace_links": ["story-001", "cand-Settlement"],
          "phase_introduced": "04"
        },
        "classes": "aggregate"
      },
      {
        "data": {
          "id": "E-settlement-executed",
          "label": "정산 실행됨",
          "type": "domain-event",
          "parent": "Agg-Settlement",
          "personas": ["P-system-batch"],
          "trace_links": ["story-001"],
          "phase_introduced": "04"
        },
        "position": { "x": 100, "y": 200 },
        "classes": "event"
      }
    ],
    "edges": []
  }
}
```

---

## 5. Visualization

각 레벨 종료 시 viz 자동 갱신. 사용자 안내:

```
Level 4{a|b|c} 시각화: {viz_url}

이번 레벨 추가:
- {N}개 도메인 이벤트 (오렌지)
- {N}개 커맨드 (파랑): 4b
- {N}개 애그리거트 (노랑 테두리): 4c
- {N}개 바운디드 컨텍스트 (분홍 컴파운드): 4c

레이아웃 토글 "preset"으로 시간순 좌→우 보기를 켤 수 있습니다.
```

---

## 6. Mini-Gate / Phase Gate

### Level 4a Mini-Gate
```
확인: Level 4a: Big Picture 완료.

산출물:
- ontology-docs/04-eventstorming/events.md ({N}개)
- ontology-docs/04-eventstorming/hotspots.md ({N}개)
- ontology-docs/04-eventstorming/viz/event-flow.json (Level 4a 그래프)

시각화: {viz_url}

다음 중 선택해주세요:
1. Continue: Level 4b (Process Modeling)
2. Request Changes: 이벤트 목록 수정
```

### Level 4b Mini-Gate
같은 형식, "Continue → Level 4c".

### Level 4c Phase Gate (표준)
```
확인: Phase 4: Event Storming 완료.

산출물 ({N}개 파일):
- events.md, commands.md, policies.md, read-models.md
- aggregates.md, bounded-contexts.md, hotspots.md
- glossary.md 갱신
- viz/event-flow.json 최종

시각화: {viz_url}

검증 우선순위:
- 반드시: 애그리거트 이름, 바운디드 컨텍스트 경계
- 권장: 핫스팟 해결, 외부 컨텍스트 매핑

다음 중 선택해주세요:
1. Continue: Phase 5 (Ontology Synthesis)
2. Request Changes: 이번 phase 산출물 수정
3. Re-visualize: 다른 레이아웃, 필터로
```

---

## 7. 응답 처리

각 mini-gate / phase gate에서:
- **Continue** → ontology-state.md 갱신, 다음 레벨/phase 진입.
- **Request Changes** → 어느 레벨의 어느 산출물 수정할지 묻기 → 갱신 → 다시 게이트.
- **Re-visualize** → viz 옵션 변경.

**audit.md 의무:** Phase 4는 mini-gate가 3번(Level 4a/4b/4c) 있어 audit 항목이 phase당 최소 4건 발생한다(질문 응답 + mini-gate 응답들 + 최종 phase gate 응답). 모든 사용자 입력을 ISO 8601 + 원문으로 `<workspace>/ontology-docs/audit.md`에 append. 형식, 예시는 `../common/session-continuity.md` §3. 요약, 덮어쓰기 절대 금지.
