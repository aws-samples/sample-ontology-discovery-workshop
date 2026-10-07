# Persona Tracking

페르소나는 Phase 1에서 정의하고 Phase 5까지 동일한 ID를 사용한다. 단계 사이의 추적 링크가 유지되도록 ID를 관리한다.

---

## 1. ID 형식

`P-<kebab-slug>`: 영문 소문자, 숫자, 하이픈만.

예:
- `P-merchant` (가맹점주)
- `P-pgops` (PG 운영팀)
- `P-finance` (회계팀)
- `P-customer-support` (고객지원)
- `P-system-batch` (시스템 자동 배치)

**금지:**
- 한국어 ID (label은 한국어 OK, ID는 영문)
- 공백, 언더스코어
- 시작이 숫자

### 1.1 한국어 라벨 → 영문 슬러그 파생 규칙

호스트 에이전트는 다음 우선순위로 슬러그를 결정한다:

1. **사용자가 명시 제공** → 그대로 사용 (가장 우선).
2. **도메인에 통용 영문 표현이 있음** → 그것을 채택.
   - 가맹점주 → `merchant`
   - 회계팀 → `finance`
   - 고객지원 → `customer-support`
   - 운영팀 → `ops`
3. **약어 + 역할** 조합으로 짧게.
   - PG 운영팀 → `pgops` (PG + ops 결합)
   - 정산 배치 시스템 → `settlement-batch` 또는 `system-batch`
4. **무리한 직역 금지**: 의미가 흐려지면 `P-domain-role` 형태로 명시.
   - "정산팀 신입" 같이 원문 의미가 모호하면 `P-settlement-junior`처럼 풀어 쓰는 대신 사용자에게 슬러그 확정 요청.

**slugify 규칙:**
- 모두 소문자.
- 공백, 언더스코어, 점은 하이픈으로.
- 영숫자, 하이픈 외 문자 제거.
- 연속 하이픈은 하나로 축약.
- 시작, 끝 하이픈 제거.

**중요:** 자동 파생한 슬러그는 Phase 3 페르소나 카드 작성 직전 사용자에게 표 형식으로 확인 요청. 사용자 승인 전까지 `[candidate]` 표시(`overconfidence-prevention.md`).

```
다음 페르소나 ID로 파생했습니다. 맞나요?

| 시드 라벨 | 파생 ID | 근거 |
|---|---|---|
| 가맹점주 | P-merchant | 통용 영문 |
| PG 운영팀 | P-pgops | 약어 + 역할 |
| 자동 정산 배치 | P-settlement-batch | 직역 |

다른 ID를 원하시면 알려주세요. (예: "PG 운영팀은 P-pg-ops로")
```

---

## 2. 페르소나 카드 형식

`{workspace}/ontology-docs/03-storytelling/personas.md`:

```markdown
# Personas

## P-merchant
- **이름:** 가맹점주
- **역할:** 정산 대상자, 결제 수단 관리자
- **목표:** 매출 정산을 정확히 받기, 정산 이슈 빠르게 확인
- **관여 시나리오:** [story-001, story-003]
- **외부/내부:** 외부 (회사 외부 사용자)
- **trace_links:**
  - phase 1 (seed): personas-seed.md
  - phase 2 (data): merchants 테이블
  - phase 3 (this file)
  - phase 4 (events): E-merchant-onboarded, E-payout-completed
  - phase 5 (entity): Merchant
- **노트:** B2B 가맹점만 대상. B2C 종단 고객은 별도 페르소나.

## P-pgops
- ...
```

각 카드는:
- ID (`P-...`): 헤더의 한 단계 (예: `## P-merchant`)
- 이름 (label)
- 역할
- 목표
- 관여 시나리오 (story IDs)
- 외부/내부 구분
- trace_links (phase별 등장 위치)
- 자유 노트

---

## 3. 진화 경로

```
Phase 1: personas-seed.md
   - Q4 응답에서 자유 텍스트로 추출한 시드 페르소나
   - ID는 임시(`P-seed-1`, `P-seed-2`)일 수 있음

Phase 3: personas.md
   - personas-seed + Phase 3 Q4 응답의 새 actor + 시나리오에서 발견된 actor
   - 임시 ID를 안정 ID(`P-merchant` 등)로 확정
   - 시드 ID와 새 ID 사이 매핑 표는 audit.md에 기록

Phase 4:
   - 기존 페르소나 그대로 사용
   - 시스템 자동 액터(예: `P-system-batch`)는 Phase 4에서 새로 발견될 수 있음

Phase 5:
   - 페르소나가 도메인 엔티티가 될지 판정
     - 도메인 엔티티(예: 가맹점주는 시스템에 저장됨) → entity Merchant 생성, P-merchant.trace_links에 추가
     - 외부 액터(예: 시스템 운영팀)는 엔티티화하지 않음
```

ID는 절대 재할당하지 않는다. 페르소나가 의미상 분리되면 새 ID 발급, 통합되면 둘 중 하나의 ID를 alias로 명시.

---

## 4. ontology-state.md의 personas 필드

```yaml
personas:
  - id: P-merchant
    name: 가맹점주
    role: "정산 대상자"
    introduced_phase: 01-intent
  - id: P-pgops
    name: PG 운영팀
    role: "정산 처리, 이슈 대응"
    introduced_phase: 03-storytelling
```

phase 종료 시마다 `personas` 필드 갱신. 추가/이름변경/role 변경 모두 audit.md에 원문 + 변경 사유 기록.

---

## 5. 페르소나 필터 (시각화)

`viz-server`는 페르소나 ID로 그래프를 필터링할 수 있어야 한다. 노드의 `data.personas` 배열에 관여 페르소나 ID들이 포함된다.

예: `P-pgops`만 선택 → `data.personas`에 `P-pgops`가 포함된 노드와 그 노드를 연결하는 엣지만 컬러로, 나머지는 회색조.

---

## 6. 페르소나 ID 변경 시 절차

사용자가 ID를 바꾸려 하면(예: `P-pgops` → `P-pg-settlement-team`):

1. audit.md에 변경 요청 원문 기록.
2. 영향받는 모든 산출물 검색:
   - personas.md
   - stories/*.md (관여 시나리오)
   - 04-eventstorming/* (events, commands에서 actor)
   - 05-ontology/* (entity trace_links)
   - viz-runtime/persona-index.json
3. 사용자에게 영향 범위 보고 후 일괄 변경 동의 받기.
4. 변경 후 viz 재렌더링.
5. ontology-state.md `personas` 필드 갱신.
6. audit.md에 변경 결과 기록.

---

## 7. Anti-pattern

금지: 같은 사람, 역할에 두 페르소나 ID 부여: 통합하라.
금지: 페르소나 카드에 trace_links 누락: phase 종료 시 검증.
금지: Phase 4, 5에서 새 페르소나 발견 시 personas-seed로 거슬러 추가 안 함: Phase별 분리는 OK, 다만 personas.md에는 모두 포함되어야 한다.
금지: 시스템, 외부 서비스를 페르소나로 만들지 않고 활동에만 표시: 어떤 actor가 활동을 하는지가 중요하므로 페르소나로 모델링.
