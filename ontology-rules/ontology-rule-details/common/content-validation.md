# Content Validation

산출물(마크다운, JSON, YAML)을 작성하기 전에 호스트 에이전트는 다음 검증을 수행한다. 검증 실패 시 작성하지 말고 수정 후 재검증.

---

## 1. Markdown

### 1.1 헤더 계층
- `#` (h1)은 파일당 한 번만, 가장 위.
- `##` 아래에 `####`이 직접 등장하면 안 됨(h2 → h3 → h4 순서).
- 한국어 헤더 OK.

### 1.2 코드블록 언어 태그
모든 코드블록에 언어 태그 명시:
- ` ```yaml `, ` ```json `, ` ```python `, ` ```bash `, ` ```mermaid `
- 무명 코드블록은 텍스트로만 사용(`text` 또는 langtag 없이는 출력만).

### 1.3 링크
상대 경로 우선:
```markdown
[trace-link.md](../common/trace-link.md)
```
사용자 산출물에서 `<workspace>/ontology-docs/...` 절대경로 표기는 OK.

### 1.4 문장과 표기

- 가운데점과 em dash를 쓰지 않는다. 나열은 쉼표, 설명은 문장이나 콜론으로 구분한다.
- 제목의 장식 문자, 홍보 문구, 같은 내용을 반복하는 요약을 넣지 않는다.
- README는 워크숍의 역할, 진행 방식, 결과물을 설명한다. DB 이관 비교나 기술 미팅 안내는 넣지 않는다.
- 명령, 파일 경로, 필드명, 사용자 답변 원문은 임의로 바꾸지 않는다. 기존 `audit.md`는 그대로 보존한다.

---

## 2. Mermaid

작성 전 다음을 확인:

### 2.1 문법
- `flowchart TD` / `flowchart LR` / `sequenceDiagram` / `erDiagram` / `classDiagram` 중 하나로 시작.
- 노드 ID는 영숫자, 언더스코어만 (한국어 ID 금지).
- 노드 라벨에 한국어 시 따옴표로 감싸기:
  ```mermaid
  flowchart LR
    A["가맹점주"] --> B["정산 요청"]
  ```
- 줄 끝 세미콜론은 선택. 일관성 유지.

### 2.2 흔한 실수 사전 체크
- `<` `>` `(` `)` 같은 특수문자가 라벨에 있으면 따옴표 필수.
- 화살표 `-->`, `---`, `==>` 표기 일관.
- subgraph 닫기 `end` 누락 금지.

### 2.3 검증 방법 (호스트 에이전트가 수행)
출력 직전에:
1. ` ```mermaid `로 시작하는지.
2. 첫 줄에 다이어그램 종류.
3. 마지막 줄 ` ``` ` 닫힘.
4. 노드 ID 영숫자만.
5. 한국어 라벨 따옴표.

문제 발견 시 수정 후 다시 작성.

---

## 3. JSON (viz JSON 포함)

### 3.1 형식
- 4 space 들여쓰기 또는 2 space 일관.
- trailing comma 금지.
- 키는 영문 lowercase + underscore.
- 모든 문자열 쌍따옴표.

### 3.2 Cytoscape 호환 스키마
viz JSON은 다음 최상위 키를 가져야 한다:
```json
{
  "metadata": { ... },
  "elements": {
    "nodes": [ ... ],
    "edges": [ ... ]
  }
}
```

### 3.3 필수 노드 필드
```json
{
  "data": {
    "id": "...",          // 필수, 고유
    "label": "...",       // 필수, 한국어 OK
    "type": "...",        // 필수, terminology.md의 11개 type 중 하나
    "trace_links": [],    // 필수, 빈 배열이라도 명시
    "phase_introduced": "..."  // 필수, "00"~"05"
  },
  "classes": "..."        // 권장, type과 동일 또는 그룹
}
```

### 3.4 필수 엣지 필드
```json
{
  "data": {
    "id": "...",          // 필수, 고유
    "source": "...",      // 필수, 노드 ID
    "target": "...",      // 필수, 노드 ID
    "label": "...",       // 권장
    "type": "..."         // 필수: trace-link | actor-event | causal | is-a | has-a | part-of | related-to
  }
}
```

### 3.5 검증 (호스트 에이전트)
- `json.loads()` 통과.
- 모든 source/target ID가 nodes에 존재.
- 중복 노드 ID 없음.
- 중복 엣지 ID 없음.

---

## 4. YAML

### 4.1 형식
- 2 space 들여쓰기.
- 키는 영문 lowercase + underscore.
- 한국어 문자열은 그냥 적음(따옴표 불필요, 값에 콜론, 하이픈이 있으면 쌍따옴표).
- 다중 줄 문자열은 `|` 또는 `>`.

### 4.2 ontology-state.md
`session-continuity.md` §2의 풀 스키마 준수. 누락 키 금지(빈 값이라도 명시).

### 4.3 검증
- `yaml.safe_load()` 통과.
- 풀 스키마의 필수 키 모두 존재.

---

## 5. 한국어 인코딩

모든 파일 UTF-8. BOM 없음.

호스트 에이전트는 macOS 한국어 자모 분리(NFD) vs 결합(NFC) 문제를 주의.
- 입력은 NFC로 정규화하여 저장.
- 산출물 비교 시 NFD/NFC 차이를 고려.

---

## 6. 파일 쓰기 전 체크리스트

호스트 에이전트는 모든 파일 작성 직전 다음을 마음속으로 점검:

- [ ] 파일 경로가 정확한가? (`{workspace}/ontology-docs/...`)
- [ ] 형식(Markdown/JSON/YAML)이 올바른가?
- [ ] Mermaid, JSON 코드블록은 검증 통과했는가?
- [ ] 모든 trace_links가 채워졌는가? (빈 배열이라도 명시)
- [ ] 페르소나 ID는 `P-<slug>` 형식인가?
- [ ] 자동 추출 결과는 "candidate" 표시되었는가?
- [ ] 한국어가 NFC인가?

---

## 7. 검증 실패 시 동작

작성 직전 검증 실패면:
1. **잘못된 출력 방지**: 파일 쓰지 말 것.
2. 사용자에게 보고: "Mermaid 다이어그램에 문법 오류가 있어 수정 후 다시 시도합니다."
3. 수정 → 재검증 → 통과 시 작성.
4. 두 번 실패하면 사용자에게 도움 요청 (수동 입력 안내).

audit.md에 검증 실패, 재시도 기록.
