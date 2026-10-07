# Phase 2: Data Structure Survey

"사실로서의 현재 데이터" 인벤토리. 스토리텔링이 추측이 되지 않도록 자료원을 먼저 캡처. brownfield는 자동 스캔, greenfield는 빈 인벤토리 + 사용자 가설 입력.

**중요: 모든 자료원 접근은 읽기 전용. 변경, 삭제 절대 금지.** (`core-workflow.md` §0.4)

---

## 1. Prerequisites

- Phase 1 완료, `01-intent/discovery-intent.md` 존재.
- ontology-state.md `current_phase: 02-data-survey`.

---

## 2. Question file

**파일:** `<workspace>/ontology-docs/02-data-survey/data-sources-questions.md`

Phase 0에서 탐지된 `detected_sources`를 기반으로 질문 작성.

```markdown
# Phase 2: Data Structure Survey Questions

> Phase 0에서 다음 자료원이 탐지되었습니다:
> {detected_sources 목록}
>
> 각 자료원에 대해 접근, 신뢰도, 범위를 확인합니다.
> 답변 후 "done"이라고 알려주세요.

## Question 1
**DB 스키마** 접근 방법은?

A. 위에서 탐지된 schemas/ddl.sql 사용 (자동 스캔)
B. 다른 스키마 파일 첨부 (경로 알려주세요)
C. DB 직접 연결 가능 (연결 정보는 별도 안전 채널로)
D. 접근 불가: 사용자가 candidate-inventory.md에 수동 작성
E. Other (please describe after [Answer]: tag below)

[Answer]:


## Question 2
**API 스펙** 위치는?

(파일 경로 또는 "없음")

[Answer]:


## Question 3
**도메인 모델 코드** 위치는?

(예: "domain/", "src/entities/" 또는 "없음")

[Answer]:


## Question 4
**기존 ERD, 문서**가 있다면 경로는?

(예: "docs/erd.md", "docs/glossary.md" 또는 "없음")

[Answer]:


## Question 5
**자료원별 신뢰도**를 알려주세요.

### 5.1 DB 스키마
A. 최신: 운영 환경과 동일
B. 약간 오래됨: 미반영 변경 일부 있음
C. 부정확함: 알려진 오류 있음
D. 적용 안 됨: 자료원 없음
E. Other

[Answer]:

### 5.2 API 스펙
A. 최신
B. 약간 오래됨
C. 부정확함
D. 적용 안 됨
E. Other

[Answer]:

### 5.3 도메인 모델 코드
A. 최신
B. 약간 오래됨
C. 부정확함
D. 적용 안 됨
E. Other

[Answer]:


## Question 6
**민감정보, 접근 제한**이 있다면 알려주세요.

(예: "운영 DB 직접 연결 금지", "PII 컬럼: customers.phone, customers.ssn")

[Answer]:
```

작성 후 사용자 알림. ontology-state.md 갱신.

---

## 3. Validation

### 3.1 단순 검증
- Q1=D인데 다른 자료원 모두 "없음" → 빈 인벤토리 모드 안내(greenfield 동등).
- Q2/Q3/Q4 경로가 실제 존재하는지 호스트 에이전트가 사전 확인.
- Q5 sub-question 답변이 Q1~4 답변과 정합한지 확인 (D 선택했는데 신뢰도 답변 있음 → 명확화).

### 3.2 모순 검증
- Q1=A인데 schemas/ddl.sql이 없는 경우 → 명확화.
- Phase 1 in-scope에 등장한 도메인 영역이 자료원에 전혀 없으면 → "이 자료원이 정말 in-scope를 다루나요?" 명확화.

---

## 4. Artifacts

> **필수: Hard gate:** 본 §4 진행 전에 §2 질문 파일의 Q1~Q6 응답이 모두 `[Answer]:` 줄에 채워져 있고 §3 검증을 통과해야 한다.
> 답변 없이 자동 스캔 시작 절대 금지: 어느 자료원에 접근 가능한지, 어떤 신뢰도인지, 민감정보 제한이 있는지를 사용자가 명시해야 안전한 읽기 전용 스캔이 가능하다.
> 미응답 상태에서 본 §4를 시도하면 `current_step: awaiting-answers`로 되돌리고 사용자에게 알림.

### 4.1 자료원 자동 스캔 (읽기 전용)

호스트 에이전트는 사용자 응답(§2)에서 접근 가능 표시된 자료원만 읽는다.

#### 4.1.1 DB 스키마 (DDL)
- `CREATE TABLE` 블록 추출 → 후보 엔티티.
- 컬럼 → 속성. PRIMARY KEY → 식별자. FOREIGN KEY → 관계 후보.
- INDEX, UNIQUE 등은 메타로 보존.

#### 4.1.2 OpenAPI/Swagger
- `components.schemas.*` → 후보 엔티티.
- `paths.*` → 사용 시나리오 힌트(Phase 3 입력).
- `required` 필드 → confidence high.

#### 4.1.3 도메인 모델 코드
- 클래스명 → 후보 엔티티.
- 필드 → 속성.
- 메서드명 → 활동, 커맨드 힌트(Phase 3, 4 입력).
- 상속 관계 → is-a 후보.
- 컴포지션 → has-a 후보.

### 4.2 `02-data-survey/data-sources.md`

```markdown
# Data Sources

## DB 스키마
- **경로:** schemas/ddl.sql
- **신뢰도:** {Q5.1}
- **읽기 결과:** {N}개 테이블
- **접근 메모:** {Q6 관련 부분}

## API 스펙
- **경로:** {Q2 응답}
- **신뢰도:** {Q5.2}
- **읽기 결과:** {N}개 스키마, {N}개 엔드포인트

## 도메인 모델 코드
- **경로:** {Q3 응답}
- **신뢰도:** {Q5.3}
- **읽기 결과:** {N}개 클래스

## 기존 ERD/문서
- **경로:** {Q4 응답}
- **읽기 결과:** {요약 1~2줄}

## 민감정보, 접근 제한
{Q6 응답 그대로}
```

### 4.3 `02-data-survey/raw-schemas/`

원본 자료원 사본을 보존(향후 변경 추적용). 단순 복사:
- `raw-schemas/ddl.sql`
- `raw-schemas/openapi.yaml`
- `raw-schemas/models-summary.md` (모델 코드 요약. 코드 자체 복사는 라이센스 이슈로 금지, 클래스명, 필드만 추출)

### 4.4 `02-data-survey/candidate-inventory.md`

```markdown
# Candidate Inventory (자동 추출)

> 주의: 모든 항목은 **candidate**입니다. 사용자 검증 후 다음 phase로.

## Entities (table/class/schema 기반)

### [candidate] Settlement
- **자료원:** schemas/ddl.sql:42, openapi.yaml#/components/schemas/Settlement
- **confidence:** high (DDL primary key 명시 + OpenAPI required)
- **속성:**
  - id (uuid, PK): high
  - merchant_id (uuid, FK→merchants): high
  - amount (decimal): high
  - settled_at (timestamp): high
  - status (varchar): high
- **관계 후보:**
  - related-to Merchant (FK merchant_id)
- **사용자 결정 필요:** 도메인 용어로 "정산"이 더 적절한가?

### [candidate] Merchant
...

### [candidate] Payout
...

## Relationships (FK + 모델 컴포지션 기반)

- [candidate] Settlement → Merchant via merchant_id (1:N)
- [candidate] Settlement → Payout via settlement_id (1:1, OpenAPI)

## 사용자 결정이 필요한 항목

1. Settlement vs 정산: 도메인 용어 결정
2. Settlement-Payout 카디널리티 (DDL은 1:N 시사, OpenAPI는 1:1)
3. Q5에서 "부정확" 표시된 자료원: 어느 쪽을 신뢰할까?
```

### 4.5 `02-data-survey/conflicts.md`

자료원 간 충돌만 모음:

```markdown
# Conflicts

## C1: Settlement-Payout 카디널리티
- **자료원 A** (schemas/ddl.sql): payouts.settlement_id FK → 1:N
- **자료원 B** (openapi.yaml): Settlement.payout 단일 필드 → 1:1

**가능한 해석:**
- A) DDL이 진실, OpenAPI는 단순화
- B) OpenAPI 변경 후 DDL 미반영
- C) 두 자료원이 다른 시점 모델

이 충돌은 Phase 3 storytelling이나 Phase 4 event storming에서 해결될 수 있습니다.
지금 바로 결정하실 필요는 없습니다.
```

### 4.6 `02-data-survey/viz/data-survey.json`

Cytoscape JSON. 노드 = 자료원, 후보 엔티티. 엣지 = "이 자료원에서 추출됨" + "관계 후보".

```json
{
  "metadata": {
    "phase": "02-data-survey",
    "rendered_at": "...",
    "personas_index": [],
    "available_filters": ["source", "confidence"],
    "available_layouts": ["fcose", "concentric"]
  },
  "elements": {
    "nodes": [
      {
        "data": {
          "id": "src-ddl",
          "label": "schemas/ddl.sql",
          "type": "data-source",
          "trace_links": [],
          "phase_introduced": "02"
        },
        "classes": "data-source"
      },
      {
        "data": {
          "id": "cand-Settlement",
          "label": "Settlement",
          "type": "entity",
          "candidate": true,
          "confidence": "high",
          "trace_links": ["src-ddl", "src-openapi"],
          "phase_introduced": "02"
        },
        "classes": "entity"
      }
    ],
    "edges": [
      {
        "data": {
          "id": "e-src-cand-Settlement",
          "source": "src-ddl",
          "target": "cand-Settlement",
          "label": "extracted from",
          "type": "trace-link"
        }
      },
      {
        "data": {
          "id": "e-cand-merchant-cand-Settlement",
          "source": "cand-Settlement",
          "target": "cand-Merchant",
          "label": "merchant_id",
          "type": "related-to"
        }
      }
    ]
  }
}
```

### 4.7 viz-runtime/current.json
data-survey.json 그대로 복사. metadata.rendered_at 갱신.

---

## 5. Visualization

`visualization-protocol.md` §2 절차로 viz-server 시작/갱신. 사용자에게 URL 안내.

```
Phase 2 시각화가 준비되었습니다.
   {viz_url}

자료원별로 후보 엔티티가 색깔 구분되어 표시됩니다.
같은 이름이 다른 자료원에서 발견된 경우 점선으로 매칭 후보를 표시합니다.
```

---

## 6. Gate

```
확인: Phase 2: Data Structure Survey 완료.

산출물:
- ontology-docs/02-data-survey/data-sources.md
- ontology-docs/02-data-survey/candidate-inventory.md ({N}개 후보 엔티티)
- ontology-docs/02-data-survey/conflicts.md ({N}건 충돌)
- ontology-docs/02-data-survey/raw-schemas/ (원본 보존)
- ontology-docs/02-data-survey/viz/data-survey.json

시각화: {viz_url}

사용자 결정이 필요한 항목 ({N}개):
1. {도메인 용어 매핑}
2. {카디널리티 충돌}
...

다음 중 선택해주세요:
1. Continue: Phase 3 (Domain Storytelling)
2. Request Changes: candidate-inventory 수정 / 자료원 추가
3. Re-visualize: 다른 레이아웃, 필터로 다시 보기
4. Re-survey: 자료원 추가 스캔 (예: 누락된 마이그레이션 폴더)
```

---

## 7. 응답 처리

- **Continue** → ontology-state.md `current_phase: 03-storytelling`. data_sources_scanned 갱신.
- **Request Changes** → 수정 요청 받기 → 산출물 갱신 → viz reload → 다시 게이트.
- **Re-visualize** → viz query만 변경.
- **Re-survey** → 추가 자료원 받기 → 자동 스캔 → candidate-inventory 갱신 → viz reload → 다시 게이트.

모든 응답은 audit.md에 기록.
