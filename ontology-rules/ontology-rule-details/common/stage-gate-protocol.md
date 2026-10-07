# Stage Gate Protocol

각 phase 종료 시 호스트 에이전트는 사용자에게 명시적 응답을 요청한다. 응답 전까지 다음 phase 진입 금지.

---

## 1. 표준 Gate 메시지

게이트 출력 직전, 호스트 에이전트는 `visualization-protocol.md` §7 절차로 시각화 자가진단을 수행한다(`GET /health`).

**진단 통과(ok) 시 표준 메시지:**

```
확인: Phase {N}: {Phase Name} 완료.

산출물:
- {workspace}/ontology-docs/{NN-phase}/{file1}.md
- {workspace}/ontology-docs/{NN-phase}/{file2}.md
- ...

시각화: {viz_url}
   - Phase: {phase} | 노드: {N} | 엣지: {M}
   - 클라이언트 렌더링: 확인: 정상 ({nodes_rendered} 노드 표시됨)
   - 등록된 레이아웃: {fcose: ✓, cose-bilkent: ✓}

❓ 그래프가 정상적으로 보이나요?
   Yes / No (어떻게 이상한지 알려주세요) / Skip viz

다음 중 선택해주세요:
1. Continue: 다음 단계({Next Phase Name})로 진행
2. Request Changes: 수정 사항을 알려주세요
3. Re-visualize: 다른 레이아웃, 필터로 다시 보기

응답 형식: 숫자(1/2/3) 또는 키워드("continue"/"changes"/"reviz")
시각화 응답: 위 ❓를 먼저 답한 뒤 게이트 응답 (또는 한 번에)
```

**진단 실패(degraded) 시: 진단 모드 우선:**

`visualization-protocol.md` §7, §8의 진단 절차를 수행한 후, 사용자가 조치 또는 `Skip viz` 선택 후에 표준 게이트 메시지.

**Phase 5(마지막)은 4번 옵션 추가:**

```
4. Drill back to Phase 4: Event Storming으로 회귀
```

---

## 2. Phase 4 Mini-Gate (Level 4a, 4b)

Phase 4의 4a, 4b 종료 시는 phase gate가 아니라 **mini gate**:

```
확인: Phase 4: Event Storming Level {a|b} 완료.

이번 레벨 산출물:
- ...

시각화: {viz_url}

다음 중 선택해주세요:
1. Continue: Level {다음 레벨}로 진행
2. Request Changes: 이번 레벨 수정
```

Level 4c 종료 시는 표준 phase gate.

---

## 3. 응답 처리

### 3.1 Continue
1. `audit.md`에 응답 기록.
2. `ontology-state.md` 갱신:
   - `last_gate_response: continue`
   - `current_phase: {다음 phase}`
   - `current_step: starting`
   - `next_immediate_action: "Phase {N+1} prerequisites 확인 후 question file 작성"`
3. 다음 phase의 prerequisites 확인 단계 진입.

### 3.2 Request Changes
사용자에게 어떤 부분을 수정할지 자유 텍스트로 요청. 응답을 audit.md에 기록 후, 해당 산출물 수정 → viz 재갱신 → 다시 gate. ontology-state.md:
- `current_step: producing-artifacts`
- `next_immediate_action: "User-requested changes: {요약}. Update {file}."`

### 3.3 Re-visualize
산출물은 그대로, viz-server에 다른 레이아웃 또는 필터로 갱신 요청. 사용자 선택지:
```
어떤 방식으로 다시 볼까요?
1. 다른 레이아웃 (fcose / cose-bilkent / breadthfirst / concentric)
2. 페르소나 필터 변경
3. Phase 누적 모드 (Phase 3 + 4 같이 보기 등)
4. Trace 체인 강조 모드
```
레이아웃, 필터는 브라우저의 실제 컨트롤을 사용하도록 안내한다. 자동 query parameter 제어는 구현된 것으로 가정하지 않는다. 누적 그래프의 내용 변경이 필요한 경우 로컬 AI가 게시 CLI로 새 버전을 작성한다.

### 3.4 Drill back to Phase 4 (Phase 5 only)
```
어느 레벨로 돌아갈까요?
1. Level 4a (Big Picture)
2. Level 4b (Process Modeling)
3. Level 4c (Software Design)
```
audit.md에 회귀 사유와 시작 레벨 기록. ontology-state.md:
- `current_phase: 04-eventstorming`
- `current_step: starting`
- `key_decisions`에 drill-back 항목 append

---

## 4. Audit 기록 형식

게이트 응답은 무조건 audit.md에 다음 형식으로 append:

```markdown
## Phase {N}: Gate Response
**Time:** {ISO 8601 UTC}
**Stage:** {NN-phase}/awaiting-gate
**User input (raw):**
> {사용자 응답 원문}

**AI response summary:** {Continue / Request Changes / Re-visualize / Drill back} 처리. {다음 액션 한 줄}.
**Context:** {viz_url}, 게이트 직전 산출물 목록
---
```

---

## 5. 응답 모호성 처리

사용자 응답이 모호하면(예: "음... 좋은 것 같은데 이벤트는 좀 더 봐야겠어"):

1. audit.md에 원문 기록.
2. 호스트 에이전트가 옵션으로 변환해 재확인:
   ```
   답변을 다음으로 해석했습니다:
   - 일부 만족 → Request Changes 선택
   - 수정 대상: 이벤트 목록
   맞나요? (yes / no)
   ```
3. yes → Request Changes 흐름. no → 사용자에게 옵션 글자/키워드 명확히 요청.

---

## 6. 게이트 무시 금지

호스트 에이전트가 **사용자 응답 없이 다음 phase로 진행하면 안 된다.** compact 직전이거나 컨텍스트가 부족해도, ontology-state.md의 `current_step: awaiting-gate`가 살아 있으면 새 세션은 Resume Protocol로 재개해 다시 gate 메시지를 띄운다.

---

## 7. 게이트 표준 응답이 아닌 자유 발언 처리

사용자가 게이트 직후 자유 텍스트로 의견을 주면(예: "결제대행 페르소나에 'PG 운영팀'이라고 적었는데 'PG 정산팀'이 더 정확해요"):

1. audit.md 기록.
2. 자동으로 Request Changes로 분기 + 변경 요청을 명시적으로 확인.
3. 변경 적용 후 다시 gate.

자유 발언이 단순 칭찬/감상이면 audit에 기록 후 "Continue로 진행할까요?" 재확인.
