# Phase 0: Workspace Detection

**Always runs.** 자동 탐지만, 사용자 질문 없음.

**관련 규칙:** `../common/session-continuity.md` (state 초기화 형식), `../common/overconfidence-prevention.md` (탐지 결과 표시).

---

## 1. Prerequisites

- `<workspace>` (사용자 프로젝트 디렉토리)에서 실행 중.
- ontology-state.md 부재 (있으면 Resume Protocol).
- 사용자가 welcome-message에 "Yes" 응답함.

---

## 2. 자동 탐지 절차

호스트 에이전트는 다음 항목을 순차 탐지하고 결과를 모은다.

### 2.1 디렉토리 시그널
- `migrations/` 디렉토리 → DB 마이그레이션
- `db/`, `database/`, `schemas/` → DB 정의
- `domain/`, `entities/`, `models/` → 도메인 모델 코드
- `api/`, `apis/`, `openapi/`, `swagger/` → API 정의

### 2.2 파일 시그널
- `*.sql`, `schema.sql`, `*.ddl` → DB 스키마
- `openapi.yaml`, `openapi.yml`, `openapi.json`, `swagger.json`, `swagger.yaml` → API 스펙
- `*.entity.ts`, `*.entity.js`, `*.model.ts`, `*Entity.java`, `models.py` → 도메인 모델 코드
- `er-diagram.*`, `erd.*` → 기존 ERD
- `glossary.md`, `domain-glossary.md` → 기존 용어집

### 2.3 빈 워크스페이스
모든 시그널 없음 → greenfield.

---

## 3. 결과 분류

```yaml
brownfield: bool
detected_sources:
  - path: schemas/ddl.sql
    type: db_schema
  - path: openapi.yaml
    type: api_spec
  - path: domain/
    type: model_code
```

**brownfield 판정**: detected_sources 1개 이상.

**탐지 명령 예 (호스트 에이전트가 실행)**

```bash
# DB 스키마
find . -maxdepth 4 -type f \( -name "*.sql" -o -name "*.ddl" \) 2>/dev/null

# API
find . -maxdepth 4 -type f \( -name "openapi.yaml" -o -name "openapi.yml" -o -name "openapi.json" -o -name "swagger.json" -o -name "swagger.yaml" \) 2>/dev/null

# 모델 코드
find . -maxdepth 4 -type d \( -name "domain" -o -name "entities" -o -name "models" \) 2>/dev/null

# 기존 ERD
find . -maxdepth 4 -type f \( -name "er-diagram.*" -o -name "erd.*" \) 2>/dev/null
```

`.git`, `node_modules`, `.venv`, `__pycache__`, `dist`, `build`, `target` 등은 제외.

---

## 4. 산출물

이 단계는 자료원 본문을 읽지 않는다(읽기는 Phase 2). 단지 **존재 여부와 경로**만 기록.

`<workspace>/ontology-docs/ontology-state.md` 초기 작성:

```yaml
current_phase: 00-workspace-detection
current_step: starting
awaiting_input_file: ""
unanswered_questions: []
last_gate_response: ""
last_user_action_iso: 2026-05-26T14:00:00Z
next_immediate_action: |
  Workspace detection complete. Inform user and proceed to Phase 1 (Discovery Intent).

discovery_intent_summary: ""
key_decisions: []

personas: []

viz_server_pid: 0
viz_server_url: ""
viz_last_rendered: ""
viz_data_source: ""

brownfield: true
data_sources_scanned: []
detected_sources:
  - path: schemas/ddl.sql
    type: db_schema
  - path: openapi.yaml
    type: api_spec
depth: ""
```

`<workspace>/ontology-docs/audit.md` 초기 작성:

```markdown
# Ontology Discovery: Audit Log

## Phase 00: Workspace Detection
**Time:** 2026-05-26T14:00:00Z
**Stage:** 00-workspace-detection/starting
**User input (raw):**
> (welcome-message에 "Yes" 응답)

**AI response summary:** Workspace 탐지. brownfield={bool}. detected_sources={N}개. Phase 1 진입 동의 요청 예정.
**Context:** workspace={path}
---
```

다음 단계용 디렉토리 미리 생성:
```bash
mkdir -p ontology-docs/01-intent
mkdir -p ontology-docs/02-data-survey
mkdir -p ontology-docs/03-storytelling/stories
mkdir -p ontology-docs/04-eventstorming
mkdir -p ontology-docs/05-ontology
mkdir -p ontology-docs/viz-runtime
```

---

## 5. Visualization

**Skip.** 이 phase는 그래프가 없다.

---

## 6. Gate

자동 게이트(미니 알림 형식, 사용자 응답 필요):

```
확인: Phase 0: Workspace Detection 완료.

탐지 결과:
- 모드: {brownfield | greenfield}
- 발견된 자료원 ({N}개):
  - schemas/ddl.sql (DB schema)
  - openapi.yaml (API spec)
  - domain/ (model code)

다음 Phase 1: Discovery Intent & Scope로 진행하겠습니다.
워크플로우 의도, 범위를 묻는 질문 파일을 작성합니다.

진행할까요? (Yes / No)
```

응답:
- **Yes** → ontology-state.md 갱신(`current_phase: 01-intent`), audit 기록 후 Phase 1 진입.
- **No** → 사용자 의도 확인. 종료 또는 조정.

---

## 7. 실패 대응

- 권한 없는 디렉토리 접근 실패 → 무시하고 다음 디렉토리. audit에 기록.
- find 명령 미지원 OS → Python `pathlib`로 대체.
- workspace에 쓰기 권한 없음 → 사용자 안내 후 종료.
