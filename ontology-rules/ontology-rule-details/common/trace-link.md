# Trace Link

본 워크플로우의 모든 노드는 `trace_links: [...]` 필드를 가진다. trace link는 한 개념이 어느 산출물에서 처음 나타났고, 어떤 다른 개념으로 진화했는지를 추적한다. trace 없는 노드는 "고립(orphan)" 처리되어 사용자 검증 대상이 된다.

---

## 1. Trace ID 형식

| 종류 | 예 | 비고 |
|---|---|---|
| story | `story-001` | Phase 3 stories/story-NNN-<slug>.md |
| persona | `P-merchant` | persona-tracking.md 참조 |
| candidate | `cand-Settlement` | Phase 2 candidate-inventory.md 항목 |
| event | `E-payment-settled` | Phase 4 events.md 항목 |
| command | `C-execute-batch` | Phase 4 commands.md |
| policy | `Pol-auto-retry` | Phase 4 policies.md |
| read-model | `RM-settlement-summary` | Phase 4 read-models.md |
| aggregate | `Agg-Settlement` | Phase 4 aggregates.md |
| bounded-context | `BC-Settlement` | Phase 4 bounded-contexts.md |
| entity | `Ent-Merchant` | Phase 5 ontology.md |
| relationship | `Rel-Merchant-has-Settlement` | Phase 5 |
| concept | `Con-Settlement-Cycle` | Phase 5 추상 개념 |
| activity | `Act-Q1-S1-A1` | Phase 3 stories 내부 (질문Q1, 시나리오S1, 활동A1) |
| work-object | `WO-invoice` | Phase 3 |

prefix는 워크플로우 전체에서 고정. 충돌 방지.

---

## 2. trace_links 필드 위치

### 2.1 마크다운 산출물
페르소나 카드, 이벤트 항목, 엔티티 항목 모두에:

```markdown
## P-merchant
- ...
- **trace_links:** [`story-001`, `cand-Merchant`, `E-merchant-onboarded`, `Ent-Merchant`]
```

### 2.2 viz JSON
```json
{
  "data": {
    "id": "E-payment-settled",
    "label": "결제 정산됨",
    "type": "domain-event",
    "trace_links": ["story-001", "cand-Settlement", "C-execute-batch"],
    "personas": ["P-pgops"]
  }
}
```

### 2.3 ontology-state.md
다루지 않음: state는 진행 추적용이고, trace는 산출물에 인라인.

---

## 3. Trace 체인 (필수 추적 경로)

### 3.1 표준 체인
```
Story (3) → Activity (3) → Domain Event (4) → Aggregate (4) → Entity (5) → Relationship (5)
```

### 3.2 페르소나 체인
```
personas-seed (1) → Persona (3) → Actor in Events (4) → Optional Entity (5)
```

### 3.3 데이터 체인 (brownfield)
```
raw-schemas (2) → candidate-inventory (2) → Entity (5) → Relationship (5)
```

### 3.4 Phase 5의 통합
모든 entity는 다음 중 최소 하나의 trace를 가져야 한다:
- candidate-inventory 항목 (`cand-*`)
- story-NNN
- aggregate (`Agg-*`)

trace 없는 entity는 `orphans.md`에 표시.

---

## 4. trace 자동 생성 규칙

### 4.1 Phase 3
- story 작성 시 → 등장한 모든 actor의 personas.md trace_links에 story ID append.
- story 내부 명사가 Phase 2 candidate-inventory와 매칭되면 → story의 work-object trace_links에 `cand-*` 추가.

### 4.2 Phase 4
- 자동 추출 이벤트의 trace_links 초기값 = 추출 출처 story.
- aggregate trace_links = 묶인 이벤트들의 union.

### 4.3 Phase 5
- entity trace_links = 통합 출처(Phase 2 candidate + Phase 3 work-object + Phase 4 aggregate).
- relationship trace_links = 출처 events, stories.

---

## 5. 시각화에서의 trace

`viz-server`의 trace 필터:
- 노드 클릭 → 해당 노드의 trace_links에 포함된 다른 노드들을 강조 (다른 노드는 회색조).
- "Trace forward" 토글: 현재 노드에서 시작해 trace_links를 거슬러 entity까지 강조.
- "Trace backward" 토글: 현재 노드에 도달하는 모든 출처 강조.

---

## 6. Orphan Detection

Phase 5 종료 단계에서 호스트 에이전트는 다음을 검사:

```python
# 의사코드
for node in all_nodes:
    if node.type == "entity" and len(node.trace_links) == 0:
        orphans.append(node)
    if node.type == "concept" and not any_referenced(node):
        orphans.append(node)
```

발견 항목은 `05-ontology/orphans.md`:

```markdown
# Orphans (검토 권고)

다음 노드는 추적 링크가 없거나 다른 노드에서 참조되지 않습니다.
정말 필요한지 사용자 검증이 필요합니다.

## Ent-LegacyAccount
- 출처 추정: 어디에서도 발견 안 됨
- 권고: A) 삭제 B) 유지(이유 추가) C) 다른 entity에 병합

[Answer]:
```

이 자체가 명확화 질문 파일 형식이라, Phase 5 게이트 직전에 사용자 응답을 받는다.

---

## 7. trace 무결성 검증 시점

- 각 phase 종료 직전: 새로 만든 노드의 trace_links가 비어있으면 경고.
- Phase 5 종료 직전: orphan 검출.
- 사용자 "Request Changes" 후 산출물 수정 시: 수정된 노드의 trace_links도 같이 갱신.

---

## 8. Anti-pattern

금지: trace_links 빈 배열 그대로 두기: 최소 자기 출처 phase는 기록.
금지: trace ID prefix 임의 변경: §1 표 고정.
금지: trace 깨진 채로 phase 진행: 게이트에서 차단.
금지: ID 변경 시 다른 산출물의 trace 갱신 안 함: `persona-tracking.md` §6과 동일 원칙.
