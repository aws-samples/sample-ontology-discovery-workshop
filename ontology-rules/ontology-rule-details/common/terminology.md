# Terminology

본 워크플로우 내 핵심 용어들의 정의. 호스트 에이전트와 사용자가 같은 단어를 같은 의미로 사용하기 위한 사전.

---

## 1. 사람, 역할

### Actor
도메인에서 활동을 수행하는 주체. 사람, 시스템, 외부 서비스를 포함.

### Persona
Actor의 대표 유형. ID 형식 `P-<slug>`. 한 도메인에 보통 3~7명.
- **외부 페르소나**: 시스템 사용자 (가맹점주, 고객 등)
- **내부 페르소나**: 운영팀, 개발자 등
- **시스템 페르소나**: 자동 배치, 외부 API (예: `P-system-batch`)

상세: `persona-tracking.md`

---

## 2. Domain Storytelling 표기법 (Stefan Hofer)

### Activity
한 페르소나가 수행하는 동작. 동사로 표현. 화살표 위에 번호로 시퀀스 표시.

예: `1. 정산 요청한다`, `2. 정산 결과 확인한다`.

### Work Object
활동의 대상이 되는 명사. 데이터, 문서, 물리 객체.

예: `정산 요청서`, `정산 보고서`, `결제 거래 내역`.

### Domain Story
Actor + Activity + Work Object의 시퀀스. `stories/story-NNN-<slug>.md`.

상세: `stages/03-domain-storytelling.md`

---

## 3. Event Storming 표기법 (Alberto Brandolini)

### Domain Event
"일이 일어났다"는 과거형 사실. 오렌지 스티커.

예: `결제 정산됨`, `가맹점 등록됨`, `정산 실패함`.

### Command
이벤트를 일으키는 명령. 파랑 스티커. 보통 동사 명령형.

예: `정산 실행하라`, `가맹점 등록하라`.

### Policy (Reactive Logic)
한 이벤트에 자동으로 반응해 다른 커맨드를 발생시키는 규칙. 라일락(연보라) 스티커.

예: `결제 실패 → 자동 재시도 명령`.

### Read Model
의사결정, UI에 필요한 데이터 뷰. 연두 스티커.

예: `오늘 정산 요약`, `미정산 거래 목록`.

### Aggregate
같이 생성, 변경되어야 하는 일관성 경계. 노랑(테두리) 스티커. 트랜잭션 단위.

예: `Settlement` (정산 + 정산 내역들).

### Bounded Context
같은 용어가 다른 의미를 갖는 경계. 분홍 컴파운드 영역.

예: `Settlement Context` vs `Payment Context`. 양쪽에서 `정산`이 나오지만 다른 데이터.

### Hotspot
논쟁, 불확실, 미해결. 자주(Magenta) 스티커.

예: "정산 실패 시 책임은 PG인가 가맹점인가?"

상세: `stages/04-event-storming.md`

---

## 4. Ontology

### Entity
도메인에서 식별 가능한 사물. 기본키(자연, 합성)를 가진다.

예: `Merchant`, `Settlement`, `Payout`.

### Concept
추상 개념, 범주. 식별자가 없거나 의미가 강한 명사.

예: `Settlement Cycle`, `Payment Period`.

### Relationship
엔티티 간 연결.
- `is-a`: 상속, 서브타입 (예: `B2B Merchant is-a Merchant`)
- `has-a` / `part-of`: 소유, 구성 (예: `Settlement has-a Payout`)
- `related-to`: 비즈니스 관계 (예: `Settlement related-to Merchant via merchant_id`)

### Crosswalk
원본 자료원(raw schemas)과 ontology 간 매핑.

예: `schemas.settlements.merchant_id → Ent-Merchant.id`.

상세: `stages/05-ontology-synthesis.md`

---

## 5. 워크플로우 메타 용어

### Phase
워크플로우의 6단계 중 하나. 0~5.

### Stage Gate
phase 종료 시 사용자 명시적 승인 지점. 표준 응답: Continue / Request Changes / Re-visualize / (Phase 5만) Drill back.

### Mini-gate
Phase 4의 3-level 안에서 각 레벨 종료 시 mini gate(Continue / Request Changes만).

### Question File
`{phase}-questions.md`. 모든 사용자 질문이 들어가는 파일.

### Trace Link
한 노드의 출처, 진화 경로. ID 배열. 상세: `trace-link.md`

### Audit Log
`audit.md`. 모든 사용자 입력의 원문 ISO 8601 타임스탬프 기록.

### State File
`ontology-state.md`. 워크플로우 진행 상태(YAML).

### Resume Protocol
모든 진입점이 첫 액션으로 수행하는 state 확인, 재개 안내 절차. 상세: `session-continuity.md`

### Candidate
자동 추출된 항목으로 사용자 검증 전 상태. 상세: `overconfidence-prevention.md`

### Confidence
자동 추출 신뢰도 등급(`high` / `medium` / `low`).

### Greenfield / Brownfield
- **Greenfield**: 기존 시스템, 자료원 없는 신규 도메인
- **Brownfield**: 기존 시스템, DB, 코드가 존재. Phase 2에서 자동 스캔.

---

## 6. 색상 사전 (Event Storming + 워크플로우 시각화)

| 의미 | 색상 | CSS hex | 사용 |
|---|---|---|---|
| Domain Event | 오렌지 | `#FF9800` | 업무에서 발생한 사건 |
| Command | 파랑 | `#42A5F5` | 이벤트를 일으키는 행위 |
| Policy | 라일락 | `#BA68C8` | 자동 정책 |
| Read Model | 연두 | `#AED581` | 의사결정 입력 데이터 |
| Aggregate | 노랑 (테두리) | `#FFEB3B` | 트랜잭션 경계 |
| Bounded Context | 분홍 (컴파운드) | `#F48FB1` | 의미 경계 |
| Hotspot | 자주 | `#D81B60` | 논쟁점 |
| Persona | 노랑 | `#FFD54F` | 사람, 시스템 actor |
| Activity | 회색 | `#9E9E9E` | 동작 |
| Work Object | 초록 | `#81C784` | 대상 명사 |
| Entity | 흰색 (검정 테두리) | `#FFFFFF` | 온톨로지 엔티티 |
| Concept | 파스텔 파랑 | `#90CAF9` | 추상 개념 |

---

## 7. 한국어, 영어 표기

본 워크플로우는 한국어 우선 + 핵심 키워드 영어 병기:
- 산출물 본문: 한국어 우선
- ID, prefix: 영어 (`P-`, `E-`, `Ent-` 등)
- 코드, JSON 키: 영어
- 파일 이름: 영어 (`personas.md`, `events.md`)

도메인 용어는 사용자가 결정. glossary.md에 한국어, 영어 매핑 기록.

---

## 8. 약어

| 약어 | 의미 |
|---|---|
| DDD | Domain-Driven Design |
| BC | Bounded Context |
| ES | Event Storming |
| DST | Domain Storytelling |
| LLM | Large Language Model |
| RAG | Retrieval Augmented Generation |
| PII | Personally Identifiable Information |
| PoC | Proof of Concept |
| NFR | Non-Functional Requirements (본 워크플로우는 다루지 않음) |
