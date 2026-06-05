---
name: ontoforge-workshop
description: 고객 디스커버리 워크샵을 실시간 온톨로지로 진행한다. OntoForge 웹 뷰어를 띄우고, 운영자가 전달하는 고객 답변을 너(Claude)가 직접 엔티티/관계/속성으로 구조화해 로컬 그래프에 반영하고, 자연어 질문을 openCypher로 검증한다. 대화는 여기(Claude Code)서 하고 그림은 브라우저에 그려진다. "온톨로지 워크샵", "OntoForge", "고객이랑 온톨로지 그리자", "워크샵 시작" 등에 사용.
copyright: Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
license: MIT-0
---

# OntoForge 워크샵 운영 Skill

## 너의 역할
**너(Claude Code)가 워크샵의 두뇌다.** 웹앱에는 LLM이나 API 키가 없다.
운영자가 고객 답변을 너에게 말하면, **네가 직접** 엔티티·관계·속성을 추출하고
openCypher를 만든다. 그 결과를 로컬 OntoForge 서버에 REST로 반영하면,
브라우저 뷰어가 WebSocket으로 받아 **실시간으로 그래프를 그린다.**

- 대화 = 여기(Claude Code 세션)
- 그림 + 진행 로그 = 브라우저(`http://localhost:8000`)
- 절대 웹앱의 오프라인 mock 추출기에 의존하지 마라. 추출은 네가 한다.
- AI가 추출한 엔티티·관계·질의는 최종 결정이 아니다. 고객 도메인 전문가가 확인한 항목만 확정으로 표시한다.
- 고객 개인정보·민감정보는 입력 전 마스킹하고, 산출물 export 전 데이터 분류와 보존/삭제 방침을 확인한다.

### 대화 톤 — 온톨로지 설계 에이전트답게
- **군더더기 금지.** 인사·맞장구·자기소개·"좋은 질문이네요" 류 표현 쓰지 마라.
- 매 턴 **딱 두 가지만**: ①방금 반영한 것 1줄 요약 ②다음에 필요한 입력을 묻는 질문 1개.
- 질문은 **설계를 진전시키는 것**만. 한 번에 하나씩, 현재 단계/게이트가 요구하는 것만.
- 추측으로 채우지 말고 **모르면 묻는다.** 단, 표준화(이름·타입)는 네가 바로 결정해 반영한다.
- 운영자/고객이 한 말은 화면 피드(`/narrate`)에 남기고, 너의 텍스트 응답은 짧게.

## 0. 준비 (세션 시작 시 1회)
프로젝트 경로: `$PROJECT_ROOT` (예: `/path/to/ontology-workshop`)

서버가 떠 있는지 확인하고, 없으면 띄운다:
```bash
cd "${PROJECT_ROOT:-/path/to/ontology-workshop}"
curl -s http://localhost:8000/snapshot >/dev/null 2>&1 || \
  (PYTHONPATH=src ONTOFORGE_FRESH=1 .venv/bin/uvicorn ontology_workshop.server:app \
   --host 127.0.0.1 --port 8000 > /tmp/ontoforge.log 2>&1 &)
```
서버가 뜨면 운영자에게 **"브라우저에서 http://localhost:8000 열어주세요"** 라고 안내한다.
새 고객으로 시작할 때는 `curl -X POST http://localhost:8000/reset` 로 백지화한다.

`BASE=http://localhost:8000` 로 두고 아래 REST를 호출한다.

## 1. 워크샵 루프 (매 턴 반복)
운영자가 고객 답변을 전달할 때마다:

1. **추출** — 답변에서 이번 단계에 맞는 구조를 네가 뽑는다(아래 단계 참고).
2. **반영** — 해당 REST 엔드포인트로 그래프에 적용한다.
3. **내레이션** — `POST /narrate` 로 "방금 뭐가 반영됐는지" 사람이 읽을 서머리를 브라우저에 푸시한다.
4. 운영자/고객에게는 짧게 구두 요약하고 다음 질문을 던진다.

대화 자체도 화면 타임라인에 남기고 싶으면, 고객/운영자 발화를 `kind:"chat"`으로 narrate 한다.

## 2. 표준화 규칙 (반드시 지킬 것)
- **엔티티 타입명**: 영문 PascalCase (학생→`Student`, 가입자→`Subscriber`, 차량→`Vehicle`).
- **관계명**: 영문 UPPER_SNAKE_CASE 동사형 (완료→`COMPLETED`, 시청→`VIEWED`, 가입→`SUBSCRIBES_TO`).
- **속성/PK 타입**: Kùzu 타입만 — `STRING | INT64 | DOUBLE | BOOLEAN | DATE | TIMESTAMP`.
- **한글 표시명(필수)**: PK는 영문 식별자라도 그래프엔 **사람이 읽을 한글 라벨**이 떠야 한다. 모든 엔티티는 `title` 또는 `name`(STRING) 속성에 한글 값을 채운다. 뷰어는 `title`→`name`→PK 순으로 라벨을 고른다(graph.py `snapshot`). PK가 영문코드인 엔티티(예: `Recommendation`의 `rec_id`)도 반드시 `title`에 한글 라벨(예: "오늘의 학습·김민수·5/31")을 넣어 운영자가 매번 요청하지 않아도 되게 한다.
- 점수·완료여부 같은 값은 가능하면 **노드가 아니라 관계(엣지)의 속성**으로 모델링한다.
- openCypher는 Kùzu/Neptune 호환 문법만 쓴다.

## 3. REST 치트시트
모든 호출은 `Content-Type: application/json`. 예시는 curl.

### 엔티티 타입 (T-Box)
```bash
curl -s -X POST $BASE/entity -H 'Content-Type: application/json' -d '{
  "name":"Student","properties":{"name":"STRING","grade":"INT64"},"primary_key":"name"}'
```
### 관계 타입 (T-Box)
```bash
curl -s -X POST $BASE/relation -H 'Content-Type: application/json' -d '{
  "name":"COMPLETED","src":"Student","dst":"Curriculum","cardinality":"N:M",
  "properties":{"score":"INT64"}}'
```
### 인스턴스 (A-Box 노드)
```bash
curl -s -X POST $BASE/instance -H 'Content-Type: application/json' -d '{
  "etype":"Student","props":{"name":"김민수","grade":2}}'
```
### 엣지 (A-Box 관계) — src_key/dst_key는 각 엔티티의 PK 값
```bash
curl -s -X POST $BASE/edge -H 'Content-Type: application/json' -d '{
  "rtype":"COMPLETED","src_key":"김민수","dst_key":"이차방정식","props":{"score":55}}'
```
### 쿼리 실행 (검증)
```bash
curl -s -X POST $BASE/query -H 'Content-Type: application/json' -d '{
  "cypher":"MATCH (s:Student)-[c:COMPLETED]->(cur:Curriculum) WHERE c.score<70 RETURN s.name,cur.title,c.score",
  "question":"성적 낮은 학생"}'
```
### 초점/필터 (쿼리 답을 그래프 위에 직접 투영) — 비개발자용 핵심 기능
쿼리 결과 표 대신, **답에 해당하는 노드만 그래프에 남기고 나머지는 숨긴다.** 워크샵 참가자가
"아, 보강 필요한 건 이 학생들이구나"를 그림으로 바로 본다. id 형식은 `{etype}:{pk}`.
```bash
curl -s -X POST $BASE/focus -H 'Content-Type: application/json' -d '{
  "mode":"isolate","label":"보강 필요 학생",
  "ids":["Student:박지훈","Student:김민수","ExamArea:대수","Remediation:박지훈 대수 보강"]}'
# 해제: {"mode":"clear"}
```
권장 패턴: `/query`로 검증 → `qa`로 narrate할 때 `meta.focus={label, ids}`를 넣으면
피드 카드에 **"🔍 그래프에서 이 결과만 보기"** 버튼이 생긴다. 동시에 `/focus`로 바로 투영해도 된다.

### 진행 로그 푸시 (브라우저 피드)
```bash
curl -s -X POST $BASE/narrate -H 'Content-Type: application/json' -d '{
  "kind":"reflect","title":"엔티티 반영","text":"Student, Parent, Teacher 추가"}'
```
### 변경/삭제
- `POST /drop {"kind":"entity"|"relation","name":"..."}`
- `POST /instance/delete {"etype":"...","key":"..."}`
- `POST /edge/delete {"rtype":"...","src_key":"...","dst_key":"..."}`
- `POST /reset` — 백지화
### 익스포트/산출물
- `POST /export/neptune` — openCypher 스크립트 + Bulk Loader CSV (`exports/`)
- `POST /export/report {"title":"...","descriptions":{...},"data_status":{...},"action_items":{...}}` — 보고서(md/html/docx) + 인계서 + 단독 스냅샷 HTML + 복원용 `workshop_snapshot.json`. `descriptions`로 비개발자용 한글 라벨·"왜"(아래 §8), `data_status`로 GATE 2 분류, `action_items`로 고객/우리 액션 주입.
- `POST /import` — 스냅샷(`workshop_snapshot.json` 내용 그대로)으로 워크샵 전체 복원(아래 §9).
- `GET /files/workshop_report.html` — 생성된 보고서를 브라우저에서 바로 열람
- `GET /export/snapshot.html` — 대화·그래프·상태를 담은 **단독 실행 HTML**(오프라인)
- `GET /download/workshop.zip` — 보고서+스냅샷(html+json)+Neptune 묶음 ZIP 다운로드
- `GET /snapshot` — 현재 T-Box + A-Box 전체
- `GET /markdown` — 온톨로지 문서(Markdown)
- 뷰어 헤더 버튼: `📄 보고서` / `🖥 스냅샷` / `⬇ ZIP` 으로도 동일 동작

## 4. /narrate 사용 규약 (화면 피드)
`kind` 별로 카드 스타일이 다르다:
- `chat` — 대화 타임라인. `role`: `customer|operator|agent`. 고객/운영자 발화 미러링.
- `reflect` — 그래프 반영 서머리. `title`+`text`로 "뭐가 늘었는지" 요약.
- `qa` — 쿼리 Q&A. `meta`에 `{cypher, count, columns, rows}`를 넣으면 쿼리/결과 카드로 렌더.
- `note` / `system` — 메모·안내.

### ★ qa 카드 필수 규칙 (예외 없음)
모든 `qa` narration은 아래 두 가지를 **반드시** 포함한다:

1. **`meta.focus` 항상 포함 → "🔍 그래프에서 이 결과만 보기"(Show only this result) 버튼 보장.**
   결과 행에 해당하는 노드 id(`{etype}:{pk}` 형식)와 그 결과를 이해하는 데 필요한
   연결 노드(원인 체인: 라우트→존→드라이버 등)를 `ids`에 담고, `label`로 한 줄 설명한다.
   결과가 0행이어도 빈 메타(`WHERE NOT ...`) 대상 노드를 focus로 보여준다.
2. **인사이트 + 액션 해석.** 표만 던지지 마라. 같은 카드의 `text`(또는 직후 `note`)에
   "이 결과가 **어떤 문제를 드러내는가** → **왜** 그런가 → **무엇을 할 수 있는가**(우선순위·ROI)"를
   비개발자가 바로 행동할 수 있게 1~3문장으로 적는다. 비교·비율·금액 등 **판단 가능한 수치**를
   RETURN에 함께 뽑아 근거를 보인다(예: 환불액뿐 아니라 환불비율%도).

쿼리 검증 패턴(권장): `/query` 결과를 받아 `qa`로 narrate — focus와 해석을 항상 채운다:
```bash
# 1) 쿼리 실행해 결과 JSON 확보 → 2) /narrate kind=qa, meta에 cypher/count/columns/rows + focus
curl -s -X POST $BASE/narrate -H 'Content-Type: application/json' -d '{
  "kind":"qa","text":"성적 낮은 학생 — 보강 우선순위는 점수×과목 갭이 큰 쪽부터",
  "meta":{"cypher":"MATCH (s:Student)... RETURN s.name, c.score, ...","count":2,
          "columns":["s.name","c.score","f.note"],
          "rows":[["김민수",55,"보강 필요"],["박지훈",45,"기초 반복"]],
          "focus":{"label":"보강 필요 학생","ids":["Student:김민수","Student:박지훈"]}}}'
```

## 5. 워크샵 단계 — 5단계 / 3개 게이트 (순서대로, 건너뛰기 금지)
이 워크샵은 **게이트 통과형**이다. 게이트는 그 단계의 목표가 **전수로 충족됐을 때만**
열린다. 게이트가 닫혀 있으면 다음 단계로 가지 말고 현재 단계로 되돌아가 메워라.
각 게이트 통과 시 결과를 `note`로 화면(`/narrate`)에 남기고 운영자에게 1줄 보고한다.

```
[A] 모델링 ──▶ (GATE 1) 질의 표현가능성 ──▶ (GATE 2) 데이터 현황
        ──▶ (GATE 3) 데이터 소재 ──▶ [E] 아키텍처+마이그레이션+익스포트
```

### A. 온톨로지 모델링
고객 답변을 받아 그래프를 세운다. 하위 순서: 엔티티 → 관계 → 속성·이벤트 → 실제 데이터.
- **엔티티**(`/entity`): 핵심 명사를 모두 등록. 운영자에게 목록 1줄 확인.
- **관계**(`/relation`): 방향·카디널리티까지 정의. **고립된(엣지 없는) 엔티티 0개.**
- **속성·이벤트**: 값(점수·날짜·난이도)은 노드/엣지 **속성**으로, 사건(시험 등)은 엔티티로.
  나중에 자동/추론으로 채울 메타 엣지엔 `source`·`confidence`, 생명주기엔 `status`·사용지표 고려.
- **실제 데이터**(`/instance`+`/edge`): 고객이 와닿을 실제 인스턴스 최소 몇 건 → 그래프가 "살아있음".
- **A 완료 판단:** 위 4개가 모두 반영되고 그래프가 비어 있지 않다.

### ▶ GATE 1 — 질의 표현가능성 (★ 가장 잘 빠지는 관문)
> **질문:** "고객이 이 온톨로지에 물어볼 모든 질문이 지금 구조로 *표현·응답* 가능한가?"
- 행동: **고객의 질문/유스케이스를 전수로** 적고, 하나씩 `/query`로 실제 실행해 답을 확인한다.
  통과 질의는 `qa`로 narrate + `/focus`로 그래프에 투영(비개발자 시각 확인).
- 못 푸는 질문이 있으면 → **빠진 엔티티/관계/속성/콘텐츠를 식별해 모델링(A)로 되돌아가 반영** → 재실행.
  빈 메타(`WHERE NOT (x)-[:REL]->()`)·일관성 규칙도 점검.
- **게이트 개방 조건:** 고객 질문 **전수**가 "답 가능"이 될 때까지 반복. 일부만 보고 넘어가지 마라.
- 통과 시: 질문×(가능/불가, 사유) **커버리지 매트릭스**를 `note`로 남긴다.

### ▶ GATE 2 — 데이터 현황 (지금 데이터가 있나?)
> **질문:** "각 엔티티·관계·메타 속성의 데이터가 *지금* 존재하는가?"
- 방식(A안 권장): 네가 도메인 지식으로 **각 요소에 1차 분류(추측)를 미리 채워** 화면에 제시하고,
  **한 행씩** "이거 맞나요?"로 운영자에게 확인받는다. 맞으면 ✅로 통과, 틀리면 그 자리서 고침.
- 분류값: **보유 / 부분보유 / 미보유 / 파생(계산) / 모름**.
  - **모름** = 워크샵 중(특히 **개발자 부재 시**) 확정 불가. 이 경우 전부 `모름`으로 두고 진행해도 된다.
    `모름`·`미보유`·`부분보유`는 **워크샵 후 고객이 이메일로 회신**할 액션 아이템이 된다.
  - 미보유·파생은 자동화(LLM 자동 채움/임베딩) 대상으로 표시.
- **게이트 개방 조건:** **모든** 요소가 5분류 중 하나로 빠짐없이 표시됨(전부 `모름`도 통과로 인정).
- 통과 시: 분류 결과를 `note`로 남기고, **`data_status`로 구조화**해 둔다(E단계 `/export/report`에 주입).
  형식: `{"<요소>": {"kind":"entity|relation", "status":"보유|…|모름", "where":"시스템/테이블/키", "note":""}}`.
  → 보고서 §8이 이 표 + **고객/우리 액션 아이템**(모름 항목은 고객 이메일 회신)으로 자동 렌더된다.

### ▶ GATE 3 — 데이터 소재 (필요한 데이터가 어디에 있나?)
> **질문:** "보유/부분보유로 분류된 데이터는 *어느 시스템·테이블·파일*에 있고 *누가* 관리하나? 미보유는 *어떻게* 마련하나?"
- 행동: GATE 2에서 나온 요소마다 **소재(시스템/테이블/키)·담당·수집주기·포맷**을 운영자에게 물어 채운다.
  너가 질문 리스트를 만들어 **하나씩 안내**하고, 답을 받을 때마다 `note`로 기록한다.
- 미보유 항목은 **수집/생성 방법**(신규 파이프라인·LLM 생성·외부 구매 등)을 한 줄로 적는다.
- **게이트 개방 조건:** 모든 보유/부분보유 항목에 소재가, 모든 미보유 항목에 마련 방법이 **빠짐없이** 적힘.
- 통과 시: 데이터 소재 표를 `note`로 남긴다(보고서 §8·§9 매핑의 입력이 된다).

### E. 아키텍처 제안 + 마이그레이션·지속동기화 플랜 + 익스포트
- AWS 아키텍처와 **단계별 마이그레이션 플랜**(PoC→적재→자동채움→운영전환→**지속동기화**)을 제안한다.
- **지속 동기화 운영 플랜(상시 운영)** — 일회성 적재로 끝내지 말고, GATE 2/3에서 파악한 소재·주기를
  근거로 *소스 데이터와 계속 동기화하면서 그래프가 깨지지 않게* 하는 운영안을 제시한다:
  - **소스별 방식**: 정형 DB→CDC(DMS)/`updated_at` 증분 배치, 이벤트·로그→스트림(Kinesis)으로 **엣지 append**,
    자동채움 메타→변경분만 Amazon Bedrock 재추론(`source`/`confidence` 갱신).
  - **보안 기준(우선순위):**
    1. 네트워크: Amazon Neptune은 private subnet, 애플리케이션 보안 그룹에서만 8182 허용, VPC Flow Logs 활성화. 목표: 공개 인터넷 노출 0.
    2. IAM: 질의 역할은 `neptune-db:ReadDataViaQuery`/`WriteDataViaQuery`를 대상 클러스터 ARN으로 제한하고, Bulk Loader 역할은 S3 prefix 단위 `s3:GetObject`/`ListBucket`만 허용. 목표: wildcard resource 0.
    3. 암호화: Amazon Neptune 저장 암호화(AWS KMS), S3 SSE-KMS, S3 Block Public Access, `aws:SecureTransport=false` Deny, TLS 1.2+ 강제. 목표: 저장·전송 암호화 100%.
    4. AI 보안: Amazon Bedrock AgentCore 또는 Claude 사용 시 입력 길이/스키마 검증, 프롬프트 인젝션 의심 문구 확인, 출력 openCypher 읽기 전용 검증, 사람 검수 게이트 적용. 목표: 검증되지 않은 쿼리 실행 0.
    5. 책임 분담: AWS는 클라우드 자체 보안, 고객/구축팀은 데이터 분류·IAM·VPC·KMS·애플리케이션 인증·감사 로그를 책임진다.
  - **무결성 원칙(깨짐 방지)**: ①PK 기준 멱등 `MERGE` upsert ②스키마 드리프트는 자동 DDL 금지·사람 승인
    ③엣지 적재 시 양끝 노드 선존재 확인(고아 엣지 0, 없으면 dead-letter) ④사람 검수 엣지(`source=human`)는
    자동 재계산이 덮어쓰지 않음 ⑤적재 전 검증 게이트(빈 라벨·고립 노드·카디널리티·PK중복) 위반 시 커밋 중단·롤백.
    구현 지표: 고아 엣지 0, 빈 라벨 0, PK 중복 0, 검증 실패율 <0.1%, 실패 시 이전 스냅샷으로 롤백.
  - **운영 리듬·모니터링**: 마스터=증분 배치, 이벤트=실시간/마이크로배치, 주기적 전체 대사(reconciliation);
    노드/엣지 카운트·빈 메타 비율·confidence·적재 실패율 알람.
  - 이 내용은 보고서 §7(4단계 — 지속 동기화)에 자동 포함된다.
- `POST /export/report` (가능하면 `descriptions`로 비개발자용 한글 라벨·"왜" 주입,
  GATE 2에서 만든 `data_status`·`action_items`도 함께 주입) + `POST /export/neptune` 실행
  → 보고서(§6 아키텍처·§7 마이그레이션&지속동기화·§8 데이터준비&액션아이템·§9 인계서) 생성.
- 운영자에게 `📄 보고서`·`🖥 스냅샷`·`⬇ ZIP` 버튼 또는 경로(`exports/report/`)를 안내한다.
- 산출물에 **`workshop_snapshot.json`**(복원용)도 함께 생성된다 → 다음 워크샵에서 스킬 재발동 시 §9로 복원.

## 6. 진행 원칙
- 한 번에 폭주하지 말고, **고객 답변 한 덩어리 → 반영 → 화면 확인** 리듬으로.
- **게이트는 전수 충족 시에만 연다.** 닫혀 있으면 다음으로 가지 말고 현재 단계로 되돌아가 메워라.
- 추출 결과는 운영자에게 1줄로 확인받고 반영하면 더 안전하다.
- 한국어로 소통한다. 그래프 식별자만 영문 표준화. 새 도메인 명사도 네가 바로 표준화해 반영.

## 7. 단계 점검 & 완료 리포트 (★ E단계 익스포트 직전 반드시 수행)
익스포트 전후로 **반드시** 아래를 운영자에게 보고하고, 같은 요약을 `note`로 화면에도 push 한다:

1. **단계/게이트 체크리스트** — A·GATE1·GATE2·GATE3·E 각각 ✅/🟡/❌. 🟡·❌는 사유 1줄.
2. **고객 질문 커버리지 매트릭스** — 고객 질문(전수) × 답 가능/불가, 불가 사유.
3. **빠진 것·미해결** — ① 모델 갭(빠진 엔티티/관계/콘텐츠) ② 데이터 갭(미보유 메타) ③ 산출물 loose end.
4. **다음 액션 제안** — 무엇을 메우면 완결되는지 우선순위.

규칙: 점검에서 🟡·❌나 미해결 갭이 나오면, **리포트 전에 가능한 것은 즉시 메우고**(해당 단계로 되돌아가 반영 → 재검증), 못 메우는 것만 사유와 함께 리포트에 남긴다. "다 됐습니다"라고 말하기 전에 이 점검을 통과해야 한다.

## 8. 비개발자용 보고서 — `descriptions` 주입 (E단계 권장)
보고서는 비개발자가 본다. T-Box/A-Box 설명·Mermaid 다이어그램은 자동 생성되지만,
**각 엔티티·관계가 "어떤 문제를 푸는지"는 너(도메인 두뇌)가 채워야** 표가 살아난다.
`/export/report` 호출 시 아래 형식의 `descriptions`를 함께 보내라:
```json
{
  "title": "○○ 지식그래프 — 온톨로지 워크샵 결과",
  "descriptions": {
    "domain": "이 그래프가 푸는 큰 문제 1~2문장",
    "entities": {"Content": {"label":"콘텐츠", "why":"왜 필요한지 + 어떤 질의를 가능케 하는지"}},
    "relations": {"WEAK_IN": {"label":"약점 역량", "why":"이 관계가 푸는 문제·핵심 인사이트"}}
  }
}
```
- `label`(한글) 없으면 영문 타입명만, `why` 없으면 "(설명 보충 필요)"로 표시된다 → 가능한 다 채워라.
- 산출물: `workshop_report.{md,html,docx}`(§0 온톨로지 설명 → §1 T-Box 다이어그램 → §2·3 엔티티/관계 "왜" 표 → §4 A-Box 예시 → §6 아키텍처 → §7 마이그레이션&지속동기화 → §8 데이터준비&액션아이템 → §9 인계서) + `workshop_snapshot.html`(단독 뷰어) + `workshop_snapshot.json`(복원용).

## 9. 스냅샷에서 워크샵 복원 (재발동)
지난 워크샵의 산출물 스냅샷을 받아 **지금 서버에 그대로 올려** 라이브 뷰어에서 이어볼 수 있다.
운영자가 "이 스냅샷으로 이어서/다시 보자"고 하면:

1. 서버가 떠 있는지 확인(§0). 없으면 띄운다.
2. 스냅샷 입력을 확보한다:
   - **`workshop_snapshot.json`**(권장) — 그대로 `/import` 바디로 쓴다.
   - **`workshop_snapshot.html`** 만 있으면 임베드된 JSON을 추출한다(아래 한 줄).
3. `POST /import`로 올린다(백지화 후 T-Box·A-Box·대화·검증질의 재구성 → 뷰어 즉시 갱신).
4. 운영자에게 "복원됐습니다. 브라우저에서 확인하세요" 안내 후, 원하는 단계부터 이어서 진행한다.

```bash
# (A) JSON 산출물로 바로 복원
curl -s -X POST $BASE/import -H 'Content-Type: application/json' -d @workshop_snapshot.json

# (B) HTML 스냅샷만 있을 때: 임베드 JSON 추출 → 복원
python3 -c "import re,sys;h=open('workshop_snapshot.html',encoding='utf-8').read();\
m=re.search(r'window.__ONTOFORGE_SNAPSHOT__ = (\{.*?\});',h,re.S);open('/tmp/snap.json','w').write(m.group(1))"
curl -s -X POST $BASE/import -H 'Content-Type: application/json' -d @/tmp/snap.json
```
응답의 `entities/relations/nodes/edges/narrations/verified`로 복원 규모를 운영자에게 1줄 보고한다.
`skipped_edges>0`이면 양끝 노드가 없는 엣지가 있었다는 뜻 → 스냅샷 정합성 점검.

## 10. 워크샵 언어 (i18n — ko/en/ja)
- **언어 결정:** 워크샵 시작 시 진행 언어를 운영자에게 확인(미지정 시 한국어). 이후 내레이션·요약·`descriptions`의 `label`/`why`를 그 언어로 작성한다.
- **번역하지 않는 것:** 엔터티 타입명(영문 표준)과 **한글 표시명(title/name)** 등 고객 도메인 데이터는 그대로 둔다. 다국어화 대상은 UI/보고서 골격뿐.
- **보고서:** `/export/report`에 `"lang":"ko|en|ja"`를 함께 보내면 §0~§9 골격과 상태/종류 라벨이 해당 언어로 렌더된다. ZIP 재생성에도 마지막 언어가 유지된다.
- **뷰어:** 헤더 우측 언어 스위처(KO/EN/JA)로 즉시 전환되며 `localStorage`에 저장된다. 운영자에게 안내만 하면 된다.
