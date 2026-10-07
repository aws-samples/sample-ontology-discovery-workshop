# Graph Health Review

Phase 5를 마치기 전에 그래프의 연결 집중, 책임 혼재, 고립 노드를 검사한다. 검사 결과를 사용자에게 보여주고 수정할 항목을 확인한다.

## v0.2 실행 연결

`viz-server/quality.py`가 게시된 T-box와 A-box에서 아래 깊이별 구조 휴리스틱을 실제 계산한다. `GET /api/quality` 또는 `python3 viz-server/agent.py --data-dir ... quality`로 동일한 보고서를 읽는다. 이 결과는 **구조 후보 검출**이며 도메인 의미를 확정하거나 자동 리팩터하지 않는다.

웹은 경고, 근거, 권고, 대상을 표시한다. 사용자 검토 후 로컬 AI가 수정하거나, `quality_decisions`에 `status: accepted|suppressed`, 현재 `revision`, `actor`, 비어 있지 않은 `reason`을 기록해 다시 게시한다. 그래프가 바뀌면 기존 예외는 재검토한다. 구체적 JSON 계약은 `viz-server/README.md`를 따른다.

중복 ID, 관계 끝점, 미정의 타입, 속성 타입, enum, 식별자, 카디널리티도 별도로 검사한다. 500개 초과 엔티티의 유사도 비교는 생략 사실을 보고하며, 조건별 enum 책임은 `conditional_relationships` 근거가 있을 때만 검출한다. `is-a`는 연결 집중 계산에서는 제외하지만 고립 여부에서는 연결로 인정한다.

---

## 1. 적용 시점

- **메인:** Phase 5 §5(Visualization) 직전 = §4(Artifacts) 직후 자동 실행.
- **선택:** Phase 2(Data Survey), Phase 4 Level 4c(Software Design) 종료 시도 동일 분석 가능. 다만 v0.1.0은 Phase 5만 강제.
- **온디맨드:** 사용자가 `/onto-graph-review` 또는 자연어로 명시적 요청 시 언제든 가능 (선택 명령).

---

## 2. 자동 검증 8가지

호스트 에이전트는 `ontology.json`을 읽어 다음 휴리스틱을 모두 적용한다.

### 2.1 Hot Node Detection
- **degree 계산:** node별 in_degree + out_degree.
- **is-a 엣지 분리 카운트:** type subtype 패턴 (예: Lesson is-a Content)의 is-a 엣지는 **degree 합산에서 제외**. 도메인 hierarchical 구조는 hot node가 아님.
- **non-isa-degree** = total degree − is-a edge 수.
- **임계값:** top entity의 **non-isa-degree**가 다음 둘 다 만족 → hot node 후보.
  - 평균 non-isa-degree의 **3배 이상**.
  - 전체 non-isa-degree의 **25% 이상**.
- **추가 신호 (모두 동시 만족 시 hot node 확정):**
  - 4개 이상 BC와 직접 연결 (검증 §2.2와 cross-check)
  - 직접 self-loop 2종 이상 (검증 §2.7 cross-check)
  - 5+ value enum discriminator 보유 (검증 §2.8 cross-check)
- **단순 hub vs hot node 구분:** Subject, Unit, Grade 같은 reference master는 다수 entity에서 참조되어 in-degree만 높음. 이는 정상. **out-degree와 in-degree의 균형**이 안 좋고(>2:1 또는 <1:2) **여러 BC와 연결**될 때만 hot node로 판정.

### 2.2 책임 혼재 (Multi-BC concentration)
- 한 entity가 **4개 이상의 다른 bounded context**의 entity와 직접 연결 → 책임 분리 후보.
- 예외: 외부 reference entity(Student 등)는 본질적으로 다른 BC들과 연결되므로 제외.

### 2.3 Orphan
- trace_links 빈 배열 또는 다른 어떤 노드도 이 entity를 참조하지 않음 → 삭제, 통합 후보.
- 이미 Phase 5에 `orphans.md`가 별도로 다루지만, graph health에서 한 번 더 cross-check.

### 2.4 Singleton
- `degree == 0` 인 entity (BC, concept 제외) → 진짜 필요한지 확인.

### 2.5 Symmetric Duplicate (의심 통합 후보)
- 두 entity의 라벨이 동의어 후보 (Levenshtein 거리 작거나 한국어/영어 매핑) **AND** 관계 집합이 80% 이상 동일 → 통합 후보.
- glossary.md의 동의어 항목과 cross-check.

### 2.6 Dead End
- `in_degree > 0` AND `out_degree == 0` 이지만 라이프사이클 terminal(deprecated 등) 표시도 없음 → 의도 확인.

### 2.7 Deep Recursion
- 한 entity로의 재귀 관계(self-loop)가 3종 이상 → 책임 분할 후보. (예: Content → Content via prerequisite, related, replaces 3종은 임계값 도달).
- 이 경우 link entity로 reify 권고.

### 2.8 Type Discriminator Hot
- entity의 핵심 속성에 enum discriminator가 있고(예: `content_type`, `event_type`, `status`) 그 enum 값에 따라 **다른 관계, 속성을 가지는 패턴** 발견 → type subtype 권고.
- 신호:
  - DDL CHECK 제약, OpenAPI enum + 5개 이상 값.
  - 시나리오에서 enum 값별로 다른 활동, 관계 등장.
  - candidate-inventory에 `type별 다른 속성` 메모.

---

## 3. 결과 산출물

### 3.1 `05-ontology/graph-health.md`

```markdown
# Graph Health Review

**검증 시각:** {ISO 8601}
**그래프 통계:** N개 노드, M개 엣지, 평균 degree X.Y

## 발견된 안티패턴

### Hot Node: Ent-{Name} (degree N)
- 전체 degree의 P%, 평균의 K배.
- 연결된 BC 수: X.
- **권고:** {type subtype | link reify | 책임 분리 | 유지(도메인 본질적 hub)}.

### 혼재 책임: Ent-{Name}
- 4개 BC 직접 연결: ...
- **권고:** ...

### Orphan: Ent-{Name}
- ...

(검출되지 않은 항목은 표시 안 함)

## 리팩터 후보 (사용자 선택)

A. {옵션 1: 예: Type subtype으로 분할}
B. {옵션 2: 예: Link entity reify}
C. {옵션 3: 유지 (도메인 본질적 hub)}
D. Other
```

### 3.2 추가 viz JSON
실행 보고서의 경고 ID와 요소 ID로 시각화에 자동 스타일을 적용한다. 구조 오류는 빨간색, 경고는 주황색, 검토 예외는 회색 점선이다. 기존 `health_warning: true`도 로컬 AI가 기록한 별도 경고로 지원한다.

### 3.3 ontology-state.md 갱신
```yaml
graph_health_checked_at: 2026-05-28T11:00:00Z
graph_health_warnings: 2     # 발견된 안티패턴 수
graph_health_user_decision: pending  # pending | accepted | refactored | suppressed
```

---

## 4. 사용자 결정 흐름

검증 후 호스트 에이전트는 다음 형식으로 사용자에게 보고:

```
Graph Health Review 결과

주의: 발견된 안티패턴 N개:

1. Hot Node: Ent-Content (degree 18, 전체의 35%)
   - 연결된 BC: 4개 (ContentCatalog, Curriculum, Recommendation, MetaQuality)
   - 의미 다른 책임 혼재 의심: 분류, 메타, 라이프사이클, 추천, 진도
   - content_type enum 5종 (lesson|question|video|activity|assessment) → type subtype 신호
   - 권고:
     A. Type subtype으로 분할 (Lesson, Question, Video, Activity, Assessment)
     B. ContentMeta type별 link entity로 reify (메타 link 책임 분리)
     C. A + B 둘 다
     D. 유지 (Content가 도메인 본질적 hub) + 운영 영역에서 인덱스, 캐싱
     E. Other

2. Deep Recursion: Ent-Content (3종 self-loop: prerequisite, related, replaces)
   - 권고: link entity reify (옵션 B 또는 C에 포함)

이 안티패턴들을 어떻게 처리할까요?
1. 자동 리팩터 (옵션 선택 시 워크플로우가 적용)
2. 결정만 기록 (다음 phase에 사용자가 직접 적용)
3. Suppress (도메인 본질적 hub로 인정: 향후 재검증 시 제외)
```

### 4.1 자동 리팩터 선택 시
호스트 에이전트가 ontology.md, ontology.json, crosswalk.md를 갱신. audit, graph-health.md에 변경 이력. 다시 graph health 재검증(루프).

### 4.2 결정만 기록 시
graph-health.md에 결정, 사유만 적고 다음 phase로.

### 4.3 Suppress 시
ontology-state.md `graph_health_user_decision: suppressed`. 다음 검증부터 해당 hot node는 경고에서 제외 (단, 새로운 안티패턴은 계속 검증).

### 4.4 사용자가 "그래프 보고 결정"이라 답하면
viz-server에서 `health_warning` 강조된 뷰를 보여준 후 다시 결정 요청.

---

## 5. False Positive 완화

휴리스틱은 보수적으로: **반드시 사용자에게 결정 요청**, 자동으로 리팩터 강제 안 함. 다음 패턴은 자동 false positive로 처리해 경고 안 함:

- **외부 reference entity** (Phase 1에서 외부 BC로 명시): degree 검사 제외.
- **Concept entity**: 추상 개념은 degree 0이어도 정상.
- **Bounded Context node**: 컴파운드 라벨이라 degree 0이 정상.
- **Audit, State 같은 워크플로우 메타 entity**: 도메인 entity가 아님.

---

## 6. 깊이별 강도

`ontology-state.md`의 `depth`에 따라 검증 강도 조절:

| depth | 적용 검증 |
|---|---|
| Minimal | 2.1(hot node) + 2.3(orphan)만 |
| Standard | 2.1, 2.2, 2.3, 2.4, 2.7 (5종) |
| Comprehensive | 2.1~2.8 모두 |

---

## 7. v0.1.0의 한계 (향후 개선)

- 시각, 구조 리뷰만, **의미 리뷰 없음**: "이 entity 이름이 도메인에 정말 적절한가?" 같은 검증은 사용자만 가능.
- LLM-기반 자동 리팩터 제안: 현재는 사람이 해석, 결정. 향후 LLM이 BC 재분배, entity 분할안을 후보로 생성하는 자동화 가능.
- 그래프DB 운영 영역 분석 부재: super-node를 어떻게 인덱스로 풀지는 별도 영역.

---

## 8. Anti-pattern (이 규칙 자체)

금지: degree만 보고 자동 분할 강제 → 도메인 본질적 hub를 잘못 분리할 위험.
금지: 사용자 결정 없이 ontology.json 자동 수정 → audit 추적 없는 변경.
금지: depth=Minimal에서 8가지 모두 검증 → 작은 PoC에 과도한 마찰.
금지: 시각화 강조만 하고 graph-health.md 산출물 안 만듦 → 결정 기록 손실.
