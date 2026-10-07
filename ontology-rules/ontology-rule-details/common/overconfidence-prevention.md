# Overconfidence Prevention

AI가 추출한 업무 용어, 관계, 페르소나는 사용자가 확인하기 전까지 `candidate`로 표시한다.

---

## 1. 사용자 확인

호스트 에이전트가 자료원, 이전 산출물에서 추출한 모든 항목은 사용자가 명시적으로 승인하기 전까지 "candidate"로 표시된다. 사용자가 stage gate에서 Continue를 응답한 후에야 "확정(confirmed)"으로 승격된다.

---

## 2. Candidate 표시 규칙

### 2.1 마크다운 산출물

자동 추출 결과는 항목 앞에 `[candidate]` prefix:

```markdown
## Candidate Entities (사용자 검증 필요)

- [candidate] **Settlement**: 자료원: schemas/ddl.sql, openapi.yaml. 추출 신뢰도: 높음.
  - 필드: id, merchant_id, amount, settled_at, status
  - **사용자 결정 필요:** 이름이 도메인 언어에 맞나요? `정산`이 더 적절할 수 있습니다.

- [candidate] **Payout**: 자료원: schemas/ddl.sql. 추출 신뢰도: 보통.
  - **사용자 결정 필요:** Settlement와의 관계가 1:1인지 1:N인지 확인 필요.
```

게이트 통과 후 prefix는 제거되거나 `[confirmed]`로 변경.

### 2.2 JSON 산출물

```json
{
  "data": {
    "id": "Ent-Settlement-candidate",
    "label": "Settlement (candidate)",
    "type": "entity",
    "candidate": true,
    "confidence": "high",
    "extraction_source": "schemas/ddl.sql:42"
  }
}
```

`candidate: true` 필드와 `confidence: low|medium|high` 필드 의무.

### 2.3 시각화

candidate 노드는 점선 테두리. 사용자가 시각적으로 "확정 vs 후보"를 구분 가능.

---

## 3. 절대 금지 표현

자동 추출 결과를 다음과 같이 표현하면 안 됨:

- "확정", "Confirmed" (게이트 통과 전)
- "정확히", "분명히", "당연히"
- "사용자 의도는 X입니다" (사용자가 말하지 않은 의도 추측)
- "이 도메인에서는 보통 ...입니다" (당위 표현)
- "자명하게" 등 의문 차단 표현

대안:
- "후보로 추출했습니다"
- "이 표현이 맞나요?"
- "사용자 결정 필요"
- "추정: ... (검증 필요)"

---

## 4. 도메인 용어 규칙

도메인 용어는 특별히 보수적으로:

### 4.1 자동 명명 금지
호스트 에이전트가 영어 컬럼명(`merchant_id`)을 한국어 도메인 용어(`가맹점`)로 자동 번역하면 안 된다. 사용자에게 명시적 매핑 요청:

```markdown
## Question: Term Mapping (Phase 5)

자료원에서 발견한 다음 식별자에 대한 도메인 용어를 알려주세요.

### 5.1 `merchant_id` (테이블: settlements, payouts)
A. 가맹점주 ID
B. 가맹점 ID (가맹점주와 다른 개념)
C. PG 가맹사 ID
D. Other (please describe after [Answer]: tag below)

[Answer]:
```

### 4.2 동의어, 동음이의어
같은 의미 다른 이름(`정산` vs `Settlement`) 발견 시 사용자에게 우선 사용할 표기 결정 요청. 결정 후 glossary.md에 기록, 다른 표기는 alias로.

같은 이름 다른 의미(예: `정산`이 두 컨텍스트에서 다른 데이터 모델) 발견 시 바운디드 컨텍스트 경계 신호: Phase 4 hotspots.md에 기록.

---

## 5. 신뢰도 표시

자동 추출 결과에 confidence 표기:

| 등급 | 기준 |
|---|---|
| `high` | 자료원에서 명시적, 구조적 (DDL `PRIMARY KEY`, OpenAPI `required`) |
| `medium` | 추론 기반 (변수명, 주석으로 추정) |
| `low` | 약한 신호 (단편적 등장, 한 곳에만) |

confidence는 사용자에게 "어디까지 검증해야 하는지" 알려주는 신호. high도 검증 면제 아님: 단지 우선순위 낮음.

---

## 6. 검증 우선순위

phase 종료 직전 사용자 검증 우선순위 가이드:

1. **반드시 검증**: 페르소나 이름, 애그리거트 이름, 엔티티 식별자(자연키), 도메인 용어 매핑.
2. **권장 검증**: confidence가 medium, low인 모든 항목, 동의어, 동음이의어 후보, 컨텍스트 경계.
3. **검토만**: confidence high인 자료원 직접 추출(DDL primary key 등). 사용자가 시간 부족 시 스킵 가능하지만 audit에 스킵 기록.

호스트 에이전트는 게이트 메시지에 검증 우선순위 안내 포함:

```
이번 phase에서 사용자 검증이 필요한 항목:
- 반드시: {N개} (페르소나명, 도메인 용어 매핑)
- 권장: {N개} (confidence medium 이하 후보들)
```

---

## 7. 사용자 명시 동의 시점

다음 표현은 명시적 동의로 간주(audit에 인용):
- "맞아", "OK", "좋아", "그대로", "확정"
- "Continue" / "1" (게이트 응답)
- 산출물 파일을 수정 없이 다음 phase 진입

다음은 불충분(추가 확인 필요):
- 침묵, 짧은 끄덕임("음", "어")
- "그런 것 같아"
- 게이트 외 자유 발언

---

## 8. Anti-pattern

금지: 자료원에서 추출한 엔티티를 곧바로 ontology에 "확정" 표기.
금지: 영문 컬럼명을 임의로 한국어로 번역.
금지: 사용자가 게이트에 응답하기 전에 다음 phase 산출물 작성.
금지: confidence 표기 없이 자동 추출 결과 게시.
금지: "이 도메인에서는 보통 ..." 같은 당위적 진술로 사용자 결정 영향.

---

## 9. 결정 이유 기록

key_decisions에 다음 형식으로 기록(`session-continuity.md` §2):

```yaml
key_decisions:
  - phase: 05
    decision: "Settlement 엔티티 → '정산'으로 명명"
    reason: "사용자가 Q1 응답에서 한국어 도메인 용어 우선 명시"
    sources_evidence: [schemas/ddl.sql, story-001]
```

이 기록은 6개월 뒤 재검토할 때 결정의 맥락을 복원하는 데 쓰인다.
