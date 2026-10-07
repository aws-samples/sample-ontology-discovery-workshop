# Phase 5: Ontology Synthesis

Phase 2, 3, 4 산출물을 통합한 정련된 온톨로지. 사용자가 도메인 용어와 관계를 검증하면서 최종 산출물 작성.

---

## 1. Prerequisites

- Phase 4 모든 레벨(A/B/C) 완료.
- candidate-inventory(2), personas/stories/glossary(3), events/commands/aggregates/bounded-contexts(4) 존재.
- ontology-state.md `current_phase: 05-ontology`.

---

## 2. 자동 통합 (사전 작업)

호스트 에이전트는 Phase 5 진입 시 다음을 자동 통합:

### 2.1 Entity 후보 통합
```
Phase 2 candidates (cand-*)
  + Phase 3 work-objects (WO-*)
  + Phase 4 aggregates (Agg-*)
  → 통합 후보 entity 목록
```

매칭 규칙:
- 같은 라벨 → 같은 entity로 통합.
- glossary.md에서 동의어로 매핑된 라벨 → 같은 entity.
- candidate-inventory의 속성 ↔ aggregate의 속성 → entity의 속성 후보.

### 2.2 Relationship 후보 통합
```
candidate-inventory의 FK 관계
  + story 시퀀스에서 추출된 의미 관계
  + aggregate 안의 포함 관계
  → 통합 관계 후보
```

타입 추론:
- DDL FK + 부모-자식 시맨틱 → `has-a` 또는 `part-of`.
- 시나리오에서 "X는 Y의 일부이다" → `part-of`.
- 시나리오에서 "X와 Y가 연결된다" → `related-to`.
- 명시적 상속, 서브타입 → `is-a`.

### 2.3 Crosswalk 후보
raw-schemas의 컬럼 → 통합 entity의 속성 매핑. 자동 생성, 사용자 검증.

### 2.4 Orphan 검출
- trace_links 비어있는 entity.
- 다른 어떤 노드도 참조하지 않는 entity.
- glossary에 없는 라벨.

---

## 3. Question file

**파일:** `<workspace>/ontology-docs/05-ontology/ontology-questions.md`

```markdown
# Phase 5: Ontology Synthesis Questions

## Auto-integrated Entities ({N}개)

| ID | 라벨 | 출처 | 식별자 후보 |
|---|---|---|---|
| Ent-Settlement | 정산 | cand-Settlement, Agg-Settlement | settlement_id |
| Ent-Merchant | 가맹점 | cand-Merchant, Agg-Merchant | merchant_id |
| Ent-Payout | 지급 | cand-Payout, story-001 WO | payout_id |

## Question 1
통합 엔티티 목록을 검토해주세요.

A. 모두 맞음
B. 누락된 엔티티 (자유 서술)
C. 잘못 통합됨 (분리 필요) (자유 서술)
D. 잘못 분리됨 (통합 필요) (자유 서술)
E. Other

[Answer]:


## Question 2
**is-a (상속/서브타입) 관계** 후보:

| 후보 | 출처 | 검토 |
|---|---|---|
| Ent-B2BMerchant is-a Ent-Merchant | OpenAPI subschema | ? |
| Ent-RecurringPayout is-a Ent-Payout | story-002 변형 | ? |

각 후보를 검토해주세요. 자유 서술로 답하시거나 "모두 맞음"이라고 적어주세요.

[Answer]:


## Question 3
**has-a / part-of 관계** 후보:

| 후보 | 카디널리티 | 출처 |
|---|---|---|
| Ent-Settlement has-a Ent-Payout | 1:1 또는 1:N (충돌) | DDL vs OpenAPI |
| Ent-Merchant part-of Ent-MerchantGroup | ?:1 | DDL |

[Answer]:


## Question 4
**비즈니스 관계 (related-to)** 후보:

| 후보 | 의미 | 출처 |
|---|---|---|
| Ent-Settlement related-to Ent-Merchant via merchant_id | 정산 대상 | DDL FK |
| Ent-Settlement related-to Ent-PaymentTx via tx_ids | 정산에 포함된 결제 거래 | story-001 |

[Answer]:


## Question 5
**동의어, 동음이의어** 정리:

자료원에서 발견된 다음 표현 쌍을 검토:

### 5.1 정산 vs Settlement
A. 같은 의미: 한국어를 우선 사용
B. 같은 의미: 영어를 우선 사용
C. 다른 의미: 정산은 ?, Settlement는 ?
D. Other

[Answer]:

### 5.2 ...
[Answer]:


## Question 6
**식별자(Identity)**: 각 entity의 자연키와 합성키:

### 6.1 Ent-Merchant
A. business_registration_no (사업자등록번호): 자연키
B. id (UUID): 합성키
C. 둘 다 식별자 (composite)
D. Other

[Answer]:

### 6.2 ...
[Answer]:


## Question 7
**핵심 속성**: 각 entity에서 도메인 의미가 있는 속성만(모든 컬럼이 아니라):

### 7.1 Ent-Settlement
- 자료원에서 발견: id, merchant_id, amount, settled_at, status, created_at, updated_at
- **핵심으로 표시할 항목**(자유 서술, 콤마 구분):

[Answer]:


## Question 8
**컨텍스트 간 매핑**: 같은 개념이 다른 컨텍스트에서 어떻게 나타나는가:

(예: "BC-Settlement의 Settlement"는 "BC-Accounting의 Revenue"와 같은 비즈니스 의미일 수 있음)

[Answer]:
```

---

## 4. Validation

### 4.1 단순 검증
- 각 질문 응답이 비어있는지.
- Q5/Q6/Q7은 entity별 sub-question.

### 4.2 Cross-phase 정합성
- Q1에서 새 entity 추가 시 → 어느 출처에서 왔는지 추가 질문.
- Q5 결정이 glossary.md와 충돌 → glossary.md 갱신 필요.
- Q6 식별자가 candidate-inventory의 PK와 다른 경우 → crosswalk에 명시.

### 4.3 Orphan 검증
자동 검출된 orphan을 사용자에게 별도 표시:

```markdown
## Auto-detected Orphans ({N}개)

다음 노드는 trace_links가 없거나 다른 노드에서 참조되지 않습니다.

### Ent-LegacyAccount
- 출처: cand-LegacyAccount (DDL legacy_accounts 테이블)
- 다른 노드 참조: 없음
- 권고: A) 삭제 B) 유지(이유 추가) C) 다른 entity에 병합 D) Other

[Answer]:
```

이 항목들은 게이트 직전 처리.

---

## 5. Artifacts

### 5.1 `05-ontology/ontology.md`

```markdown
# Ontology

## Entities

### Ent-Settlement
- **라벨:** 정산 (Settlement)
- **식별자:** settlement_id (UUID, 합성키)
- **핵심 속성:**
  - merchant_id (FK→Ent-Merchant): high
  - amount (decimal): high
  - settled_at (timestamp): high
  - status (enum: pending|completed|failed): high
- **bounded_context:** BC-Settlement
- **trace_links:** [cand-Settlement, Agg-Settlement, story-001, E-settlement-created]

### Ent-Merchant
...

## Relationships

### Rel-Settlement-Merchant
- **type:** related-to
- **source:** Ent-Settlement
- **target:** Ent-Merchant
- **via:** merchant_id (FK)
- **cardinality:** N:1
- **business meaning:** 정산은 한 가맹점에 귀속
- **trace_links:** [DDL settlements.merchant_id, story-001]

### Rel-Settlement-Payout
- **type:** has-a
- **source:** Ent-Settlement
- **target:** Ent-Payout
- **cardinality:** 1:N
- **resolved_conflict:** DDL was correct, OpenAPI was simplified
- **trace_links:** [conflicts.md C1, Q3 응답]

## Concepts

### Con-Settlement-Cycle
- **라벨:** 정산 주기
- **정의:** 한 가맹점의 결제 → 정산 → 지급 한 사이클
- **포함:** Ent-PaymentTx, Ent-Settlement, Ent-Payout
- **trace_links:** [story-001]
```

### 5.2 `05-ontology/ontology.json`

기계용 + 시각화용 (Cytoscape 호환):

**v0.2 게시:** 아래는 이전 통합 그래프 형식의 예시다. 실제 웹의 T-box/A-box, Cypher를 사용하려면 `viz-server/README.md` 계약에 따라 `tbox.entities`, `tbox.relations`, `snapshot`, `queries`를 명시한다. 원본 인스턴스가 없으면 `snapshot`을 비워 두고 가상 자료로 대체하지 않는다. 호스트 AI가 `agent.py inspect → publish --expected-revision → quality`를 실행해 게시하고 변경 전후를 보존한다. 웹은 모델을 수정하지 않는다.

```json
{
  "metadata": {
    "phase": "05-ontology",
    "rendered_at": "...",
    "personas_index": ["P-merchant", "P-pgops", "P-system-batch"],
    "available_filters": ["persona", "bounded_context", "is-a", "trace_link"],
    "available_layouts": ["fcose", "cose-bilkent", "concentric"]
  },
  "elements": {
    "nodes": [
      {
        "data": {
          "id": "Ent-Settlement",
          "label": "정산",
          "type": "entity",
          "bounded_context": "BC-Settlement",
          "personas": ["P-pgops", "P-system-batch"],
          "key_attributes": ["merchant_id", "amount", "settled_at", "status"],
          "identifier": "settlement_id",
          "trace_links": ["cand-Settlement", "Agg-Settlement", "story-001", "E-settlement-created"],
          "phase_introduced": "05"
        },
        "classes": "entity"
      }
    ],
    "edges": [
      {
        "data": {
          "id": "Rel-Settlement-Merchant",
          "source": "Ent-Settlement",
          "target": "Ent-Merchant",
          "label": "related-to (merchant_id)",
          "type": "related-to",
          "cardinality": "N:1",
          "trace_links": ["DDL.settlements.merchant_id", "story-001"]
        }
      },
      {
        "data": {
          "id": "Rel-Settlement-Payout",
          "source": "Ent-Settlement",
          "target": "Ent-Payout",
          "label": "has-a",
          "type": "has-a",
          "cardinality": "1:N"
        }
      }
    ]
  }
}
```

### 5.3 `05-ontology/crosswalk.md`

raw-schemas → ontology 매핑:

```markdown
# Crosswalk: raw-schemas ↔ ontology

## schemas/ddl.sql

### settlements (DDL table)
| Column | Ontology Mapping | Confidence | Note |
|---|---|---|---|
| id | Ent-Settlement.settlement_id | high | PK |
| merchant_id | Rel-Settlement-Merchant via | high | FK |
| amount | Ent-Settlement.amount | high | |
| settled_at | Ent-Settlement.settled_at | high | |
| status | Ent-Settlement.status | high | enum |
| created_at | (system) | low | 도메인 의미 없음 |
| updated_at | (system) | low | 도메인 의미 없음 |

### merchants (DDL table)
...

## openapi.yaml

### components.schemas.Settlement
| Field | Ontology Mapping | Note |
|---|---|---|
| payout | Rel-Settlement-Payout (1:N으로 resolved) | OpenAPI 단순화였음 |
```

### 5.4 `05-ontology/orphans.md`

```markdown
# Orphans (검토 결과)

## 처리됨

### Ent-LegacyAccount → 삭제
- 사용자 결정: A. 삭제 (Q orphan-1)
- 사유: 마이그레이션 완료된 레거시 테이블, 이번 워크플로우 범위 밖.
- audit: {timestamp}

## 보류 (검토 권고만)

### Ent-PromoCode → 유지(이유: 향후 도입 예정)
- 사용자 결정: B. 유지
- 사유: Phase 1 out-of-scope의 "로열티" 영역이었지만 사용자가 향후 추가 가능성 명시.
```

### 5.5 `05-ontology/viz/ontology-graph.json`

ontology.json과 동일하지만 viz용 추가 필드:
- 노드 위치 힌트(컨텍스트 그룹별 클러스터링)
- 페르소나 빈도 히트맵 가중치
- is-a 트리 구조 메타

---

## 5.5. Graph Health Review (자동, Visualization 직전)

§5(Artifacts)에서 ontology.md / ontology.json 작성 직후, **자동 그래프 health 분석**을 수행한다. 상세 규칙: `../common/graph-health-review.md`.

### 5.5.1 자동 분석 8종

호스트 에이전트는 ontology.json을 읽어 다음을 평가:

| # | 검증 | 임계값 |
|---|---|---|
| 1 | Hot Node | top entity의 degree가 평균의 3배 이상 + 전체 degree의 25% 이상 |
| 2 | 책임 혼재 | 4개 이상 BC 직접 연결 (외부 ref 제외) |
| 3 | Orphan | trace_links 빈 배열 또는 어떤 노드도 참조 안 함 |
| 4 | Singleton | degree 0 entity (BC, concept 제외) |
| 5 | Symmetric Duplicate | 라벨 동의어 + 관계 80% 일치 |
| 6 | Dead End | in_degree>0 AND out_degree=0 (lifecycle terminal 아닐 때) |
| 7 | Deep Recursion | 같은 entity로의 self-loop 3종 이상 |
| 8 | Type Discriminator Hot | enum discriminator 5+ 값, 값별 다른 관계, 속성 |

### 5.5.2 산출물

- `05-ontology/graph-health.md`: 발견된 안티패턴별 권고
- `viz/ontology-graph.json`의 hot node에 `health_warning: true` 메타 추가
- `ontology-state.md`의 `graph_health_*` 필드 갱신

### 5.5.3 사용자 결정

`graph-health-review.md` §4의 보고 형식으로 사용자에게 결정 요청:
- **자동 리팩터**: 호스트 에이전트가 옵션을 ontology.md/json에 적용 후 §5.5 재실행 (루프, 최대 3회)
- **결정만 기록**: graph-health.md에 결정, 사유 기록, 다음 phase에 사용자가 직접 적용
- **Suppress**: 도메인 본질적 hub로 인정, ontology-state에 표시

자동 리팩터를 선택하면 변경 이유와 변경 전후 degree를 `audit.md`에 기록한다. 예: Content degree 18에서 Lesson 4, Question 3으로 변경.

### 5.5.4 깊이별 강도

| depth | 적용 검증 |
|---|---|
| Minimal | 1, 3 (hot node + orphan) |
| Standard | 1, 2, 3, 4, 7 (5종) |
| Comprehensive | 1~8 모두 |

### 5.5.5 통과 조건

다음 중 하나를 만족하면 §6(Visualization)로 진입:
- 안티패턴 0건
- 모든 안티패턴이 사용자 결정(refactor / 기록 / suppress)으로 처리됨
- 사용자가 "Skip health review" 명시 (audit 기록)

미처리 안티패턴이 남으면 phase gate 진입 금지.

---

## 6. Visualization

`visualization-protocol.md`:
- 기본: 엔티티-관계 그래프.
- 토글: T-box / A-box, 레이아웃 선택, 컨텍스트, 페르소나, 타입 필터. 전용 is-a 트리, 페르소나 빈도 히트맵은 구현된 것으로 주장하지 않는다.
- 노드 클릭 → trace 체인 (story → event → entity) 하이라이트.
- **§5.5 구조 오류는 빨간색, 경고는 주황색 강조**. 오른쪽 품질 패널에서 근거와 권고를 확인한다.

```
Phase 5 시각화가 준비되었습니다.
   {viz_url}

좌측: 실제 Cypher, 실행 이력, 모델 변경 전후.
중앙: T-box/A-box 그래프, 컨텍스트, 페르소나, 단계 필터.
우측: 엔티티, 관계 타입, 품질 경고, Node/Relation inspector.
노드 클릭으로 Trace 체인을 확인하세요.
```

---

## 7. Gate (Phase 5 = 워크플로우 마지막)

```
확인: Phase 5: Ontology Synthesis 완료.

산출물:
- ontology-docs/05-ontology/ontology.md (인간용 정리본)
- ontology-docs/05-ontology/ontology.json (기계용)
- ontology-docs/05-ontology/crosswalk.md (raw-schemas ↔ ontology)
- ontology-docs/05-ontology/orphans.md (고립 노드 결정)
- ontology-docs/05-ontology/viz/ontology-graph.json

시각화: {viz_url}

통계:
- {N}개 entity, {N}개 relationship, {N}개 concept
- {N}개 bounded context
- {N}개 trace_link 체인
- {N}개 orphan 처리

다음 중 선택해주세요:
1. Continue: 워크플로우 종료, 산출물 최종화
2. Request Changes: 통합 결과 수정
3. Re-visualize: 다른 모드(트리뷰/히트맵)로 다시 보기
4. Drill back to Phase 4: Event Storming으로 회귀
```

---

## 8. 응답 처리

- **Continue** →
  - ontology-state.md `current_phase: completed`, `current_step: completed`.
  - audit.md에 워크플로우 종료 기록.
  - 사용자에게 종료 메시지: 산출물 위치, 다음 단계 권고(예: Neo4j 적재, OWL 변환).
  - viz-server는 살려둠. 사용자가 명시적으로 종료할 때까지.
- **Request Changes** → 어느 부분 수정인지 물음 → 갱신 → viz reload → 게이트 재진입.
- **Re-visualize** → query 변경.
- **Drill back to Phase 4** → `04-event-storming.md` §7 절차.

---

## 9. 워크플로우 종료 메시지

```
Ontology Discovery 완료

산출물 위치:
  {workspace}/ontology-docs/

파일:
- 05-ontology/ontology.md (업무 용어와 모델 설명)
- 05-ontology/ontology.json (타입 정의와 인스턴스)
- 05-ontology/crosswalk.md (raw-schemas와의 매핑)
- glossary.md, audit.md (도메인 용어 사전, 결정 이력)

웹 내보내기 메뉴에서 스키마, 데이터, 전체 모델의 Cypher 파일을 저장할 수 있습니다.
변경 내용과 결정 근거는 audit.md에서 확인합니다.

시각화 서버는 계속 실행 중입니다 ({viz_url}).
종료하려면 PID {viz_server_pid}를 직접 kill 하세요.
```
