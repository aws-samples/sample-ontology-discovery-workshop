# Phase 1: Discovery Intent & Scope

워크플로우의 "왜, 무엇을, 누구를 위해"를 사용자에게 묻는 단계. 이후 모든 phase의 깊이, 우선순위를 결정.

---

## 1. Prerequisites

- Phase 0 완료, ontology-state.md 존재.
- `current_phase: 01-intent`.
- detected_sources 정보 존재(brownfield 판정).

---

## 2. Question file

**파일:** `<workspace>/ontology-docs/01-intent/intent-questions.md`

```markdown
# Phase 1: Discovery Intent & Scope Questions

> 답변 방법: 각 질문 아래 `[Answer]:` 줄에 답을 작성하신 뒤, 채팅에 "done" 또는 "끝"이라고 알려주세요.

## Question 1
온톨로지를 발견하려는 **도메인 영역**을 한 줄로 요약해주세요.

(자유 서술, 예: "결제 정산", "물류 배송", "환자 진료 워크플로우")

[Answer]:


## Question 2
이 온톨로지의 **1차 사용 목적**은 무엇입니까? (복수 선택, 콤마로 구분)

A. LLM RAG (검색 증강 생성)
B. 그래프 DB 적재 (Neo4j, Neptune 등)
C. 검색, 추천 시스템
D. 문서, 스키마 정렬, 표준화
E. 시스템 설계, 도메인 모델링
F. Other (please describe after [Answer]: tag below)

[Answer]:


## Question 3
**깊이**는 어느 정도까지 가야 할까요?

A. Minimal: 핵심 엔티티, 관계만 (빠른 PoC용)
B. Standard: 권장. 페르소나, 이벤트, 애그리거트까지
C. Comprehensive: 모든 컨텍스트, 정책, 읽기모델, crosswalk 포함
D. Other (please describe after [Answer]: tag below)

[Answer]:


## Question 4
**1차 사용자 페르소나**(이 도메인의 주요 등장 인물, 시스템)를 자유롭게 적어주세요.
정확한 이름은 Phase 3에서 다듬게 됩니다. 지금은 떠오르는 대로.

(예: "가맹점주, PG 운영팀, 회계팀, 고객지원, 자동 정산 배치 시스템")

[Answer]:


## Question 5
**In-scope 경계**: 이번 워크플로우가 다룰 범위를 자유롭게 적어주세요.

(예: "B2B 정산만, 일일 배치 흐름. 결제 발생부터 가맹점 입금까지.")

[Answer]:


## Question 6
**Out-of-scope**: 명시적으로 제외할 영역이 있다면.

(예: "환불, 분쟁, B2C 결제, 로열티, 프로모션 정산.")

[Answer]:


## Question 7
**결과 시한**은?

A. 1주 (PoC, Minimal 깊이 권장)
B. 1개월 (Standard 깊이 권장)
C. 분기 (Comprehensive 가능)
D. 무관

[Answer]:
```

작성 후 사용자 알림:
```
질문 7개를 ontology-docs/01-intent/intent-questions.md에 작성했습니다.
파일을 열어 [Answer]: 줄에 답을 작성하신 뒤 "done"이라고 알려주세요.
```

ontology-state.md 갱신:
- `current_step: awaiting-answers`
- `awaiting_input_file: ontology-docs/01-intent/intent-questions.md`
- `unanswered_questions: [Q1, Q2, Q3, Q4, Q5, Q6, Q7]`

---

## 3. Validation

사용자 알림 후 파일 재읽기, 답변 추출.

### 3.1 단순 검증
- Q1, Q4, Q5, Q6: 비어있으면 사용자 안내, 미응답 질문에 추가.
- Q2: 알파벳, 콤마 외 문자 있으면 명확화. "F. Other"인 경우 추가 텍스트 확인.
- Q3, Q7: A/B/C/D 단일 글자 외 → 명확화.

### 3.2 모순 검증
- Q3=C (Comprehensive) + Q7=A (1주) → clarification questions:
  ```
  Comprehensive 깊이는 보통 4~6주가 필요합니다.
  A. 깊이를 Standard로 변경
  B. 시한을 1개월로 연장
  C. Comprehensive를 핵심 컨텍스트 1개에만
  D. Other
  ```
- Q5(scope)에 등장한 도메인 용어가 Q6(out-of-scope)에도 있으면 명확화.
- Q4 페르소나가 비어있는데 Q5 scope에 사람 언급 없음 → "이 도메인 사용자는 누구입니까?" 후속 질문.

### 3.3 명확화 처리
`<workspace>/ontology-docs/01-intent/intent-clarification-questions.md` 작성, 동일 패턴 응답 대기. 해결 전까지 다음 step 금지.

---

## 4. Artifacts

### 4.1 `01-intent/discovery-intent.md`

```markdown
# Discovery Intent

## Domain
{Q1 응답}

## Purpose (1차 사용)
{Q2 응답을 풀어 쓴 목록}
- LLM RAG: ...
- 그래프 DB 적재: ...

## Depth
**{Q3 옵션}**: {옵션 설명}

## Personas (seed)
{Q4 응답을 줄바꿈 구분 목록으로}

상세 페르소나 카드는 Phase 3에서 작성됩니다.

## Scope
### In-scope
{Q5 응답}

### Out-of-scope
{Q6 응답}

## Timeline
{Q7 옵션}: {옵션 설명}

## Decisions Reasoning
- 깊이: {Q3 이유, 시한과의 정합성 설명}
- Scope/Out-of-scope 충돌 검증: 통과 / clarification으로 해결됨
```

### 4.2 `01-intent/personas-seed.md`

Q4 응답에서 추출. 임시 ID 부여.

```markdown
# Personas (Seed)

> Phase 1 임시 시드. 정식 페르소나 카드는 Phase 3에서 확정.

## P-seed-1
- **임시 라벨:** 가맹점주
- **role:** (Phase 3에서 채워질 예정)

## P-seed-2
- **임시 라벨:** PG 운영팀
- **role:** (Phase 3에서 채워질 예정)

## P-seed-3
- **임시 라벨:** 자동 정산 배치 시스템
- **role:** (Phase 3에서 채워질 예정)
```

### 4.3 ontology-state.md 갱신

```yaml
discovery_intent_summary: "{Q1} 도메인. 목적={Q2}. 깊이={Q3}. {Q5 짧게 요약}"
depth: standard                  # Q3 응답 정규화
key_decisions:
  - phase: 01
    decision: "depth={Q3}"
    reason: "{Q3 응답 이유 + Q7 시한과의 정합성}"
  - phase: 01
    decision: "in-scope={Q5 요약}, out-of-scope={Q6 요약}"
    reason: "사용자 명시"
personas:
  - id: P-seed-1
    name: {Q4 첫 항목}
    role: ""
    introduced_phase: 01-intent
  ...
```

---

## 5. Visualization

**Skip.** 이 phase는 그래프가 없다.

---

## 6. Gate

표준 게이트(`stage-gate-protocol.md` §1):

```
확인: Phase 1: Discovery Intent & Scope 완료.

산출물:
- ontology-docs/01-intent/discovery-intent.md
- ontology-docs/01-intent/personas-seed.md

결정 요약:
- 도메인: {Q1}
- 깊이: {Q3}
- 시드 페르소나: {N개}

시각화: (Phase 1은 시각화 없음. Phase 2부터 그래프가 등장합니다.)

다음 중 선택해주세요:
1. Continue: Phase 2 (Data Structure Survey)
2. Request Changes: 의도, 범위 수정
```

---

## 7. 응답 처리

- **Continue** → Phase 2 진입. ontology-state.md `current_phase: 02-data-survey`.
- **Request Changes** → 사용자에게 어떤 부분 수정할지 묻기 → discovery-intent.md 수정 → 다시 게이트.

**audit.md 의무:** 모든 사용자 입력(질문 응답, 게이트 응답, 시각화 확인 답변 등)은 `<workspace>/ontology-docs/audit.md`에 ISO 8601 타임스탬프 + 원문으로 append. 형식, 예시는 `../common/session-continuity.md` §3. 요약, 덮어쓰기 절대 금지.
