# Ontology Discovery Workflow: Core Rules

워크숍 진행 규칙은 이 파일에서 관리한다. Claude Code와 Codex의 진입 파일은 이 규칙을 참조하고, Kiro 사본은 `scripts/sync.sh`로 갱신한다.

업무 시나리오와 기존 자료를 바탕으로 엔티티와 관계를 정리한다. 모델 작성은 로컬 AI가 맡고 사용자는 웹에서 결과를 확인한다.

---

## 0. MANDATORY SETUP (모든 진입점의 첫 액션)

호스트 에이전트(Claude Code, Kiro CLI, Codex 등)는 이 워크플로우의 어떤 진입점이든 활성화되면 다음을 **순서대로** 수행해야 한다.

### 0.1 Rule Details 경로 탐색

다음 경로를 순서대로 시도하여 처음 존재하는 디렉토리를 rule-details 루트로 사용한다.

1. `<workspace>/.aidlc/ontology-rule-details/`
2. `<workspace>/.ontology/ontology-rule-details/`
3. `<workspace>/.kiro/steering/ontology-discovery-rules/ontology-rule-details/`
4. `<workspace>/ontology-rules/ontology-rule-details/` (개발 중인 본 레포 자체)

존재하는 첫 경로를 사용. 없으면 사용자에게 설치 안내 후 종료.

### 0.2 Common Rules 항상 로드

다음 12개 파일은 워크플로우 시작 시 **모두 로드**한다(요약 금지, 본문 참조).

- `common/process-overview.md`
- `common/question-format-guide.md`
- `common/stage-gate-protocol.md`
- `common/visualization-protocol.md`
- `common/persona-tracking.md`
- `common/trace-link.md`
- `common/session-continuity.md`
- `common/content-validation.md`
- `common/overconfidence-prevention.md`
- `common/terminology.md`
- `common/welcome-message.md`
- `common/graph-health-review.md`     # Phase 5 §5.5에서 자동 실행

### 0.3 Resume Protocol (필수, 모든 진입점)

호스트 에이전트는 어떤 동작도 하기 전에 다음을 수행한다:

1. `<workspace>/ontology-docs/ontology-state.md` 존재 여부 확인.
2. **존재하는 경우**: `common/session-continuity.md` §1.1의 **canonical 재개 메시지**를 출력하고 사용자 응답 대기. 다른 작업 절대 금지.
3. **존재하지 않는 경우**: `common/welcome-message.md`를 1회 출력하고 Phase 0(Workspace Detection) 진입 동의를 요청한다.

**재개 메시지의 정확한 본문은 `common/session-continuity.md` §1.1을 참조한다.** 이 문서와 본 문서 사이에 차이가 있으면 `session-continuity.md`가 우선한다.

### 0.4 Production Safety 룰 준수

자료원 자동 스캔(특히 Phase 2)은 **읽기 전용**. DDL 적용, DB 변경, 외부 API 호출 절대 금지. 사용자 자료원이 운영 환경일 가능성을 항상 가정한다(상세: 사용자 글로벌 룰 `amazon-production-safety-do-not-delete.md`).

### 0.5 Inclusive Language

`master/slave/whitelist/blacklist/whiteday/blackday` 사용 금지. 대안: `primary/replica`, `allowlist/denylist`, `clear day/blocked day`.

---

## 1. Workflow Phases (6단계)

| # | Phase | Always? | Visualization |
|---|---|---|---|
| 0 | Workspace Detection | ✓ | skip |
| 1 | Discovery Intent & Scope | ✓ | skip |
| 2 | Data Structure Survey | ✓ (brownfield: 자동 스캔, greenfield: 빈 인벤토리) | sources × candidates |
| 3 | Domain Storytelling | ✓ | persona-centered story flow |
| 4 | Event Storming (3 levels) | ✓ | colored timeline + aggregates |
| 5 | Ontology Synthesis | ✓ | entity-relationship + traces |

**각 phase 6-step 패턴:**
1. **Prerequisites**: 이전 phase 산출물 확인
2. **Question file**: `[Answer]:` 태그 양식
3. **Validation**: 답변 모순/모호 검증, 필요 시 명확화 질문 파일 생성
4. **Artifacts**: 마크다운 + JSON 산출물 작성
5. **Visualization**: viz-server 자동 실행/갱신
6. **Gate**: `Continue / Request Changes / Re-visualize`

각 phase 상세는 `ontology-rule-details/stages/{0N-...}.md` 참조.

---

## 2. Phase 4의 3-Level Mini-Gate

Phase 4 Event Storming은 한 phase 안에 3 레벨 mini-gate를 둔다:

- **Level 4a: Big Picture** (Q1-Q4): 시간순 도메인 이벤트
- **Level 4b: Process Modeling** (Q5-Q8): 커맨드, 정책, 읽기모델, 액터
- **Level 4c: Software Design** (Q9-Q11): 애그리거트, 바운디드 컨텍스트

각 레벨 종료 시 mini-gate(`Continue / Request Changes`). 4c 종료 시 phase gate.

상세: `ontology-rule-details/stages/04-event-storming.md`.

---

## 3. Phase 5의 Drill-back

Phase 5 종료 게이트는 `Continue (워크플로우 종료) / Request Changes / Drill back to Phase 4` 3택. Drill back 선택 시 Phase 4 Level 4c 진입점으로 회귀, 재진입 시 audit에 회귀 사유 기록.

상세: `ontology-rule-details/stages/05-ontology-synthesis.md`.

---

## 4. Audit & State 의무

### 4.1 ontology-state.md (단일 파일, edit/replace 가능)

`<workspace>/ontology-docs/ontology-state.md`. 풀 스키마는 `common/session-continuity.md`. 모든 phase 전환, user action 직후 **반드시 갱신**.

### 4.2 audit.md (append-only)

`<workspace>/ontology-docs/audit.md`. 모든 사용자 입력을 **원문 그대로** ISO 8601 타임스탬프와 함께 append. 절대 요약, 덮어쓰기 금지. 형식은 `common/session-continuity.md`.

---

## 5. 산출 디렉토리 표준

```
<workspace>/ontology-docs/
├── ontology-state.md
├── audit.md
├── 01-intent/
├── 02-data-survey/
├── 03-storytelling/
├── 04-eventstorming/
├── 05-ontology/
├── feedback-pending.md          # 시각화 서버가 작성하는 사용자 피드백 큐
└── viz-runtime/
    ├── current.json             # 현재 단계의 통합 그래프
    ├── persona-index.json
    └── trace-links.json
```

---

## 6. Question Format (요약, 상세는 common/question-format-guide.md)

**하이브리드 입력 모델:**
- 호스트가 인터랙티브 select 도구를 지원(예: Claude Code `AskUserQuestion`) → single, multi-select, 짧은 텍스트는 인터랙티브.
- 자유 서술, per-item 다수, long-form → 파일 기반 (`{phase}-questions.md`).
- 호스트가 인터랙티브 미지원(Kiro CLI, Codex 등) → 모든 질문 파일 기반.

**입력 방식 무관 공통 규칙:**
- 응답은 항상 `{phase}-questions.md`의 `[Answer]:` 줄과 `audit.md`에 동시 기록.
- 모든 선택형에 **"Other (please describe after [Answer]: tag below)"** 마지막 옵션 의무.
- 모순/모호 발견 시 `{phase}-clarification-questions.md` 추가 또는 인터랙티브 명확화 질문.
- 사용자 응답 전까지 다음 step 금지.

---

## 7. Visualization (요약, 상세는 common/visualization-protocol.md)

- 각 phase의 산출물 작성 직후, viz-server를 자동 실행/갱신한다.
- 서버는 `viz-server/server.py`(Python 3.10+ 표준 라이브러리, 실제 Cypher만 선택적 Kuzu), 포트 5173~5183 자동 탐색.
- PID/URL을 `ontology-state.md`에 기록 → compact 후에도 안전 재연결.
- 사용자는 브라우저에서 그래프 확인 → 워크플로우는 stage gate에서 응답 대기.
- 페르소나, 단계, bounded context 필터와 trace 탐색을 제공한다.
- 모델링, 사용자 결정, 도메인 수정은 로컬 AI가 담당한다. 웹에는 모델 변경 API나 LLM 호출을 추가하지 않는다.
- Phase 5는 타입 정의(`tbox`)와 실제 자료 인스턴스(`snapshot`)를 구분해서 게시한다. 인스턴스를 추측하거나 이전 통합 그래프를 임의로 A-box로 변환하지 않는다.
- `viz-server/agent.py inspect`로 현재 `document_revision` 확인 후 `publish --expected-revision`으로 원자적으로 게시한다. 첫 게시만 예상 버전을 생략한다. 변경 작성자, 사유를 명시한다.
- 브라우저 왼쪽은 실제 Cypher, 실행 이력, 변경 전후, 오른쪽은 T-box/A-box 개수, 타입 목록, 품질 경고, Inspector다. Cypher는 원본 DB가 아닌 현재 A-box의 읽기 전용 복제본에서만 실행한다.
- `agent.py quality`의 구조 검사와 도메인 전문가의 의미 검증을 구분한다. 예외 사유는 사용자 확인 후 해당 그래프 버전에만 기록한다.
- 결과 모델은 `agent.py export-cypher` 또는 웹 내보내기 메뉴에서 스키마, 데이터, 전체 모델로 저장한다. 내보내기는 DB에 실행하지 않는다.

**검증 의무 (3-Layer):**
- Layer 1: Server 자가진단: stage gate 직전 `GET /health`로 데이터, lib, 렌더 결과 확인.
- Layer 2: Client 렌더 보고: 브라우저가 cytoscape build 결과를 자동 `POST /render-status`.
- Layer 3: Stage gate 사용자 명시 확인: "그래프가 정상적으로 보이나요? Yes/No/Skip viz".

`degraded` / `last_client_render.ok: false` / 사용자 "No" 응답 시 진단 모드 진입 후에만 다음 phase 허용.

---

## 8. Stage Gate (요약, 상세는 common/stage-gate-protocol.md)

phase 종료 시 호스트 에이전트는 다음을 출력한다:

```
확인: Phase {N}: {Phase Name} 완료.

산출물:
- {file1}
- {file2}
...

시각화: {viz_url}

다음 중 선택해주세요:
1. Continue: 다음 단계로 진행
2. Request Changes: 수정 사항을 알려주세요
3. Re-visualize: 다른 레이아웃, 필터로 다시 보기
{Phase 5만} 4. Drill back to Phase 4
```

사용자 응답 받기 전까지 다음 작업 금지. 응답은 audit.md에 원문 기록.

---

## 9. Trace Link 의무 (요약, 상세는 common/trace-link.md)

- 모든 노드는 `trace_links: []` 필드를 가진다.
- Phase 3 페르소나, activity, work-object → Phase 4 events, commands → Phase 5 entities, relationships로 추적 가능.
- Trace 없는 노드는 Phase 5 `orphans.md`에 표시 → 사용자 검증 필요.

---

## 10. Persona ID 일관성 (요약, 상세는 common/persona-tracking.md)

- ID 형식: `P-<kebab-slug>` (예: `P-merchant`, `P-pgops`).
- Phase 1 personas-seed → Phase 3 personas → Phase 5 entities (Actor 엔티티화 시) 동일 ID 유지.
- 페르소나 카드: id, name, role, goals, scenarios, trace_links.

---

## 11. Overconfidence Prevention (요약, 상세는 common/overconfidence-prevention.md)

- 자동 추출 결과는 모두 **"candidate"** 표시.
- 도메인 용어는 **사용자 검증 없이 확정 표시 절대 금지**.
- 마크다운에서 "확정/Confirmed" 표현은 게이트 통과 후에만 사용.

---

## 12. Content Validation (요약, 상세는 common/content-validation.md)

파일 작성 전에 다음을 검증:
- Mermaid 코드블록 문법
- JSON 스키마(viz-runtime은 Cytoscape 호환)
- YAML 문법(state 파일)
- 한국어 UTF-8 인코딩

---

## 13. Reference 매트릭스

| 주제 | 참조 파일 |
|---|---|
| 워크플로우 개요 | `common/process-overview.md` |
| 질문 형식 | `common/question-format-guide.md` |
| 게이트 프로토콜 | `common/stage-gate-protocol.md` |
| 시각화 | `common/visualization-protocol.md` |
| 페르소나 | `common/persona-tracking.md` |
| 추적 링크 | `common/trace-link.md` |
| 세션 연속성 | `common/session-continuity.md` |
| 콘텐츠 검증 | `common/content-validation.md` |
| 과신 방지 | `common/overconfidence-prevention.md` |
| 용어 사전 | `common/terminology.md` |
| 환영 메시지 | `common/welcome-message.md` |
| 그래프 health 리뷰 | `common/graph-health-review.md` |
| Phase 0 | `stages/00-workspace-detection.md` |
| Phase 1 | `stages/01-discovery-intent.md` |
| Phase 2 | `stages/02-data-structure-survey.md` |
| Phase 3 | `stages/03-domain-storytelling.md` |
| Phase 4 | `stages/04-event-storming.md` |
| Phase 5 | `stages/05-ontology-synthesis.md` |

---

## 14. License

MIT-0. 본 워크플로우는 awslabs/aidlc-workflows의 패턴(3-phase, opt-in extension, audit, state, question file)을 참조했다.
