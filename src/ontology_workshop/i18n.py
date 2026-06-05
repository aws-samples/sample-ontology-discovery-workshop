# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""보고서(report.py) 다국어 문자열 — KO / EN / JA.

UI(뷰어)는 static/index.html에 별도 i18n 딕셔너리가 있고, 여기는 산출물 보고서 전용.
엔티티/관계 이름과 고객이 채운 한글 라벨·설명(descriptions)·데이터 분류 값은
'고객 데이터'이므로 번역하지 않는다. 여기서 번역하는 건 보고서의 *골격 문구*
(섹션 제목·고정 안내문·표 헤더·상태 표시명 등)뿐이다.

긴 산문 섹션(§6 AWS, §7 마이그레이션)은 통째로 현지화한 마크다운 블록으로 둔다.
"""
from __future__ import annotations

DEFAULT_LANG = "ko"
SUPPORTED = ("ko", "en", "ja")


def lang_of(lang: str | None) -> str:
    return lang if lang in SUPPORTED else DEFAULT_LANG


# 데이터 분류 상태(한글 표준값) → 표시명. 키는 항상 한글 표준값.
STATUS_LABEL = {
    "ko": {"보유": "보유", "부분보유": "부분보유", "미보유": "미보유", "파생": "파생", "모름": "모름"},
    "en": {"보유": "Available", "부분보유": "Partial", "미보유": "Missing",
           "파생": "Derived", "모름": "Unknown"},
    "ja": {"보유": "保有", "부분보유": "一部保有", "미보유": "未保有", "파생": "派生", "모름": "不明"},
}

KIND_LABEL = {
    "ko": {"entity": "엔티티", "relation": "관계"},
    "en": {"entity": "Entity", "relation": "Relation"},
    "ja": {"entity": "エンティティ", "relation": "リレーション"},
}


REPORT = {
    # =====================================================================
    "ko": {
        "html_lang": "ko",
        "default_title": "온톨로지 워크샵 결과",
        "generated": "_생성: {now} · OntoForge_",

        # ---- §0 온톨로지란? ----
        "s0_h": "## 0. 이 문서를 읽는 법 — 온톨로지란?",
        "s0_p1": ("**온톨로지**는 우리 업무의 '개념들'과 '개념 사이의 관계'를 "
                  "컴퓨터와 사람이 함께 이해할 수 있게 정리한 지식 지도입니다. "
                  "엑셀이 행과 열로 데이터를 담는다면, 온톨로지는 **점(개념)과 "
                  "화살표(관계)**로 '무엇이 무엇과 어떻게 연결되는지'를 담습니다."),
        "s0_p2": "이 그래프는 두 층으로 나뉩니다.",
        "s0_th": ["층", "무엇", "비유"],
        "s0_tbox": ["**T-Box** (스키마)", "어떤 *종류*의 개념과 관계가 존재하는가 (설계도)",
                    "부동산 *분양 도면* — 방·복도·연결 규칙"],
        "s0_abox": ["**A-Box** (인스턴스)", "실제 *데이터* 한 건 한 건 (실거주)",
                    "그 도면에 *실제로 입주한 가구*"],
        "s0_quote": ("> 즉 **T-Box는 규칙**, **A-Box는 그 규칙을 따르는 실제 데이터**입니다. "
                     "아래 1~3장은 T-Box(설계)를, 4장은 A-Box(실데이터 예시)를 보여줍니다."),
        "s0_domain_h": "### 이 온톨로지가 푸는 문제",

        # ---- §1 ----
        "s1_h": "## 1. 온톨로지 한눈에 보기 (설계도 · T-Box)",
        "s1_desc": ("개념(상자)과 관계(화살표)의 전체 지도입니다. "
                    "화살표 위 글자는 '관계의 이름'입니다."),

        # ---- §2 ----
        "s2_h": "## 2. 엔티티 — 무엇을, 왜",
        "s2_desc": "각 개념(엔티티)이 *어떤 문제를 풀기 위해* 존재하는지 설명합니다.",
        "s2_th": ["엔티티", "핵심 속성", "키", "왜 필요한가"],
        "why_missing": "_(설명 보충 필요)_",

        # ---- §3 ----
        "s3_h": "## 3. 관계 — 무엇을, 왜",
        "s3_desc": ("관계는 개념과 개념을 잇는 '의미 있는 연결'입니다. "
                    "관계 위에 값(예: 점수·근거)을 달면 '얼마나/왜 연결되는지'까지 담깁니다."),
        "s3_th": ["관계", "연결", "관계 속성", "왜 필요한가"],

        # ---- §4 ----
        "s4_h": "## 4. 실제 데이터 예시 (인스턴스 · A-Box)",
        "s4_desc": ("위 설계도(T-Box)에 실제 데이터를 넣으면 이렇게 됩니다. "
                    "전체 노드 {nodes}개·엣지 {edges}개 중 관계별 대표 샘플만 추렸습니다."),

        # ---- §5 ----
        "s5_h": "## 5. 검증된 질의 (설득 증거)",
        "s5_desc": ("워크샵에서 실제로 실행해 결과를 확인한 질문입니다. "
                    "'이 그래프로 무엇을 답할 수 있는가'의 증거입니다."),
        "s5_q": "- **Q. {q}** — 결과 {n}건",
        "s5_none": "- (워크샵 중 검증한 질의가 여기에 기록됩니다)",

        # ---- §6 (통짜 블록) ----
        "neptune_small": ("Amazon Neptune (db.r6g.large 1개 + 읽기 복제 1개) — "
                          "PoC·중소 규모에 충분"),
        "neptune_large": ("Amazon Neptune (db.r6g.xlarge 이상, Multi-AZ) "
                          "또는 분석 위주라면 Neptune Analytics 병행 검토"),
        "s6": """## 6. AWS 구축 아키텍처 제안

워크샵에서 검증한 property graph 온톨로지를 그대로 운영 환경으로 승격하는 구성.
로컬에서 작성한 openCypher가 Neptune에서 동작하도록 설계됨.

### 핵심 구성요소

- **그래프 DB:** {neptune}
  - 로컬 Kùzu에서 익스포트한 openCypher / Bulk Loader CSV로 초기 적재
  - 쿼리 인터페이스: openCypher (워크샵 쿼리 호환)
- **데이터 적재:** S3(원천 CSV/Parquet, Block Public Access + SSE-KMS + HTTPS 전송 강제) → Neptune Bulk Loader, 증분은 AWS Glue 또는 Lambda 기반 ETL
- **API 계층:** API Gateway + Lambda(또는 ECS/Fargate)로 그래프 질의 노출
- **에이전트/추론(선택):** Amazon Bedrock AgentCore — 자연어 질문 → openCypher 변환 → Neptune 질의 → 응답
- **시각화/BI:** 운영 대시보드는 본 워크샵 뷰어를 확장하거나 Amazon QuickSight·Graph Explorer 연계

### 보안 구현 기준과 책임 분담
- **AWS 책임(클라우드 자체 보안):** Amazon Neptune, Amazon S3, AWS Lambda 등 관리형 서비스 인프라의 물리·네트워크·패치 보안.
- **고객 책임(클라우드 내 보안):** 데이터 분류, IAM 최소권한, VPC 보안 그룹, S3 버킷 정책, KMS 키 정책, 애플리케이션 인증/감사 로깅.
- **우선순위 1 — 네트워크:** Neptune은 프라이빗 서브넷에 배치, 애플리케이션 보안 그룹에서만 8182 접근 허용, VPC Flow Logs 활성화. **목표:** 공개 인터넷 노출 0.
- **우선순위 2 — IAM:** 질의 역할은 `neptune-db:ReadDataViaQuery`/`WriteDataViaQuery`만 대상 클러스터 ARN으로 제한, Bulk Loader 역할은 S3 prefix 단위 `s3:GetObject`/`ListBucket`만 허용. **목표:** 와일드카드 리소스 0.
- **우선순위 3 — 암호화:** Neptune 저장 암호화(AWS KMS), S3 SSE-KMS, S3 `aws:SecureTransport=false` Deny, TLS 1.2+ 강제. **목표:** 저장·전송 암호화 100%.
- **우선순위 4 — AI 보안:** Amazon Bedrock AgentCore 사용 시 입력 길이/스키마 검증, Amazon Bedrock Guardrails, 출력 openCypher 읽기 전용 검증, 사람 검수 게이트 적용. **목표:** 검증되지 않은 쿼리 실행 0.

### 데이터 흐름
```mermaid
graph LR
  S3["원천 데이터 (S3)"] --> ETL["Glue / Lambda ETL"]
  ETL --> NEP["Amazon Neptune (openCypher)"]
  API["API GW + Lambda"] --> NEP
  USER["사용자 / 에이전트"] --> API
  BR["Amazon Bedrock AgentCore (NL→Cypher)"] --> NEP
  USER --> BR
```

### 한국 고객 컴플라이언스
- 개인정보·생체정보 포함 시 **PIPA / ISMS-P** 준수 트랙 필요
- 리전: ap-northeast-2(서울) 우선, 데이터 거주성 요건 확인
- 민감정보는 적재 전 비식별화/암호화(KMS) 적용 검토

> 현재 온톨로지 규모(엔티티 {n_ent}, 관계 {n_rel}) 기준 초기 제안이며, 실데이터 볼륨·동시성·SLA에 따라 인스턴스 사이징은 기술 미팅에서 확정.""",

        # ---- §7 (통짜 블록) ----
        "s7": """## 7. 마이그레이션 & 지속 동기화 플랜

워크샵에서 검증한 온톨로지를 실제 운영으로 옮기고, 이후 **소스 데이터와 계속 동기화하면서 그래프가 깨지지 않게 유지**하는 단계별 계획입니다. 각 단계는 *목표 · 할 일 · 완료 판단 · 리스크*로 구성됩니다.

```mermaid
graph LR
  P0["0단계<br/>PoC 검증"] --> P1["1단계<br/>데이터 적재"]
  P1 --> P2["2단계<br/>자동 채움·추론"]
  P2 --> P3["3단계<br/>운영 전환"]
  P3 --> P4["4단계<br/>지속 동기화"]
```

### 0단계 — PoC 검증 (1~2주)
- **목표:** 로컬 그래프를 Amazon Neptune에서 동일하게 재현하고 핵심 질의 성능 확인.
- **할 일:** `exports/neptune.cypher`/Bulk CSV를 S3→Neptune 적재, 워크샵 검증 질의 재실행.
- **완료 판단:** 워크샵에서 통과한 질의가 Neptune에서도 동일 결과 + 허용 지연 내.
- **리스크:** openCypher 함수·인덱스 차이 → 사전 호환성 점검.

### 1단계 — 실데이터 적재 (2~4주)
- **목표:** 보유 데이터(추정 {n_have}종)를 운영 키와 매핑해 적재, 미보유 데이터({n_need}종) 수집 범위 확정.
- **할 일:** 운영 DB 테이블 ↔ 엔티티 PK 매핑, S3 적재 파이프라인(Glue/Lambda) 구성, 증분 적재 설계.
- **완료 판단:** 실데이터 볼륨으로 그래프가 채워지고 키 정합성 검증 통과.
- **리스크:** 키 불일치·중복 → 적재 전 정합성 규칙 정의.

### 2단계 — 빈 메타 자동 채움·추론 (3~6주)
- **목표:** 비어 있는 메타(개념·역량·난이도 등)를 LLM/임베딩으로 자동 채움, 연관·선후관계 추론.
- **할 일:** Amazon Bedrock로 메타 생성, 자동 생성 엣지엔 `source`/`confidence` 부여, 검수 워크플로우(사람 확인) 연결.
- **완료 판단:** 자동 채움 정확도 샘플 검수 기준 충족, 검수상태가 그래프에 반영.
- **리스크:** 환각·오분류 → confidence 임계값 + 사람 검수 게이트.

### 3단계 — 운영 전환 (4~8주)
- **목표:** 서비스(챗봇·추천 등)가 그래프를 실시간 질의하도록 API/에이전트 노출.
- **할 일:** API Gateway+Lambda(또는 ECS), Amazon Bedrock AgentCore(NL→Cypher), 모니터링·백업·PIPA/ISMS-P 컴플라이언스 트랙.
- **완료 판단:** SLA 내 응답, 운영 대시보드·알람 가동, 보안 점검 통과.
- **리스크:** 동시성·비용 → 인스턴스 사이징과 캐싱 전략 확정.

### 4단계 — 지속 동기화 (정상 운영, 상시)
한 번 적재로 끝나지 않습니다. 기존 DB·로그가 계속 바뀌므로 **그래프를 깨지 않으면서 계속 따라가게** 하는 것이 핵심입니다.

- **목표:** 소스(운영 DB·이벤트 로그)의 변경을 그래프에 안전하게 반영, 무결성 상시 유지.
- **소스별 동기화 방식:**
  - **정형 DB(테이블):** CDC(AWS DMS/Debezium) 또는 `updated_at` 워터마크 기준 증분 배치 → S3 스테이징 → 적재. 키가 있는 마스터 데이터(학생·콘텐츠 등)에 적합.
  - **이벤트/로그(완료·시청 등 사건):** Amazon Kinesis Data Streams 또는 Amazon Data Firehose로 받아 **관계(엣지) append**로 적재. 사건은 노드가 아니라 엣지 속성으로(§T-Box 규칙).
  - **자동 채움 메타(개념·역량·난이도 등):** 소스 변경분에 대해서만 Amazon Bedrock 재추론, `source`/`confidence` 갱신.
- **그래프 무결성 원칙(깨짐 방지):**
  1. **멱등 Upsert** — 노드·엣지는 PK 기준 `MERGE` 후 `SET`. 재처리·중복 이벤트가 와도 그래프가 한 번 적용한 것과 동일(at-least-once 스트림 안전).
  2. **스키마 드리프트 가드** — 소스 컬럼/타입 변경은 자동 DDL 금지. T-Box 변경은 **사람 승인** 후 반영하고, 미지의 속성은 격리(quarantine)해 알람.
  3. **참조 무결성** — 엣지 적재 시 양끝 노드 선존재 확인. 없으면 보류 큐(dead-letter)로 보내 노드 적재 후 재시도(고아 엣지 0 유지).
  4. **사람 검수 엣지 보존** — 검수 완료(`source=human`) 엣지는 자동 재계산이 **덮어쓰지 않음**. 자동 엣지(`source=auto`)만 재생성.
  5. **적재 전 검증 게이트** — 커밋 전 검증 질의(빈 라벨·고립 노드·카디널리티 위반·PK 중복)를 실행, 위반 시 커밋 중단 + 직전 스냅샷으로 롤백.
- **운영 리듬:** 마스터 데이터 증분 배치(예: 시간/일 단위), 이벤트는 실시간/마이크로배치, 주기적 전체 대사(reconciliation)로 드리프트 보정.
- **모니터링:** 노드·엣지 카운트 추이, 빈 메타 비율, confidence 분포, 적재 실패율·dead-letter 적체를 대시보드/알람으로. 임계 초과 시 동기화 일시중단.
- **완료 판단:** 소스 변경이 정의된 지연 내 그래프에 반영되고, 검증 게이트가 매 적재마다 통과(고아 엣지·빈 라벨 0 유지).
- **리스크:** 스트림 중복·순서 역전 → 멱등 Upsert + 이벤트 타임스탬프 기준 정렬. 대량 백필 → 별도 배치 경로로 분리해 실시간 경로 보호.

### 다음 스텝 (즉시)
1. AWS SA 기술 미팅 — 본 인계서(§9)로 스키마·적재 절차·오픈이슈 리뷰.
2. 데이터 매핑 워크숍 — 보유 데이터 실제 테이블·키 확정(§8 참조).
3. PoC 환경 셋업 — Neptune + S3 + 익스포트 적재로 0단계 착수.""",

        # ---- §8 데이터 준비 상태 ----
        "s8_h": "## 8. 데이터 준비 상태 & 액션 아이템",
        "s8_summary": "워크샵에서 분류한 데이터 현황입니다(총 {total}개 요소). **{summary}**.",
        "s8_unknown_note": "'모름'은 워크샵 중 확정하지 못해 **고객 이메일 회신으로 채울 항목**입니다.",
        "s8_th": ["요소", "종류", "상태", "소재 / 메모"],
        "s8_await": "— (회신 대기)",
        "s8_dash": "—",
        "ai_h": "### 8.1 액션 아이템 (고객 · 우리)",
        "ai_quote": ("> 아래 **고객** 항목은 워크샵 중(개발자 부재 등) 확정하지 못한 부분입니다. "
                     "**이메일로 회신**해 주시면 그래프·보고서에 반영합니다."),
        "ai_customer_h": "**고객(확인 후 회신):**",
        "ai_us_h": "**우리(제안팀):**",
        "ai_none": "- (없음 — 워크샵에서 모두 확정됨)",
        "ai_unknown": "**{name}** — 데이터 보유 여부와 위치(시스템/테이블/키)를 확인해 회신",
        "ai_missing": "**{name}** — 수집/생성 가능 여부와 방법(또는 외부 확보)을 회신",
        "ai_partial": "**{name}** — 누락 범위와 보완 방법을 회신",
        "ai_us_default": [
            "보유/부분보유 데이터: 실제 스키마 ↔ 엔티티 PK 매핑 설계(기술 미팅)",
            "미보유/파생: 자동 채움(Amazon Bedrock)·추론 PoC 범위 산정",
            "PoC 환경(Neptune+S3) 셋업 및 워크샵 검증 질의 재실행",
        ],
        # §8 mock fallback
        "s8m_ready": "- 준비도(추정): **{pct}%** ({avail}/{total} 엔티티가 기존 시스템에 존재 추정)",
        "s8m_note": "- (워크샵에서 데이터 현황을 분류하면 이 섹션이 실제 표·액션 아이템으로 대체됩니다.)",
        "s8m_have_h": "### 보유 추정 (스키마 매핑 대상)",
        "s8m_have_row": "- **{entity}** ← {source} · 예상 스키마: `{schema}`",
        "s8m_none": "- (해당 없음)",
        "s8m_need_h": "### 신규 마련 필요",
        "s8m_need_row": "- **{entity}** — {note}",
        "s8m_need_none": "- (없음 — 모든 엔티티가 기존 데이터로 커버 추정)",
        "s8m_next_h": "### 다음 액션",
        "s8m_next": [
            "- 보유 데이터: 실제 테이블 스키마와 키 매핑 확인(기술 미팅)",
            "- 미보유 데이터: 수집 주체·주기·포맷 정의, 신규 파이프라인 범위 산정",
        ],

        # ---- §9 인계서 ----
        "s9_h": "## 9. 기술 미팅 인계서",
        "s9_desc": ("워크샵 합의 내용을 기술팀이 바로 이어받을 수 있도록 정리한 항목. "
                    "**이 장(章)은 개발자용으로, 식별자는 실제 구현 스키마(영문)로 표기**합니다 "
                    "— 그래프 본문(§0~§4)의 한글 개념명과 1:1 대응됩니다."),
        "s90_h": "### 9.0 한글 개념 ↔ 영문 스키마 매핑",
        "s90_th": ["한글 (워크샵)", "영문 (구현)", "구분"],
        "s90_kind": {"entity": "엔티티", "relation": "관계", "prop": "속성"},
        "s91_h": "### 9.1 확정 스키마 (T-Box)",
        "s91_ent_h": "**엔티티**",
        "s91_rel_h": "**관계**",
        "s92": ["### 9.2 익스포트 산출물 (적재용)",
                "- `exports/neptune.cypher` — openCypher CREATE 스크립트 (소규모 직접 적재용)",
                "- `exports/bulk/nodes.csv`, `exports/bulk/edges.csv` — Neptune Bulk Loader 포맷",
                "- 적재 절차: S3 업로드 → Neptune Bulk Loader 또는 openCypher 실행"],
        "s93": ["### 9.3 데이터 매핑 액션 아이템",
                "- 보유 데이터: 운영 DB 실제 테이블·키 ↔ 엔티티 PK 매핑 확정",
                "- 미보유 데이터: 수집 주체/주기/포맷 정의, 신규 파이프라인 범위 산정",
                "- 키 정합성: 엔티티 간 조인 키(예: 외래키 ↔ 관계 src/dst) 검증"],
        "s94": ["### 9.4 검증 포인트 (기술팀 확인)",
                "- 로컬 openCypher → Neptune 호환성 확인 (함수·인덱스·일부 절 차이 가능)",
                "- 쿼리 성능: 워크샵 검증 질의를 실데이터 볼륨에서 재측정",
                "- 동시성·SLA에 따른 Neptune 인스턴스 사이징 확정"],
        "s95_h": "### 9.5 오픈 이슈",
        "s95_default": [
            "OWL 추론 요건 여부 — 필요 시 트리플스토어 병행 검토(현재 범위 밖)",
            "민감/개인정보 비식별화 정책 — 적재 전 마스킹 범위 합의 필요",
            "리모트(Neptune) 라이브 쿼리 연결 시점",
        ],
    },

    # =====================================================================
    "en": {
        "html_lang": "en",
        "default_title": "Ontology Workshop Result",
        "generated": "_Generated: {now} · OntoForge_",

        "s0_h": "## 0. How to read this document — what is an ontology?",
        "s0_p1": ("An **ontology** is a knowledge map that organizes the 'concepts' of our "
                  "business and the 'relationships between concepts' so that both computers "
                  "and people can understand them together. Where a spreadsheet holds data in "
                  "rows and columns, an ontology captures 'what connects to what, and how' as "
                  "**dots (concepts) and arrows (relationships)**."),
        "s0_p2": "This graph has two layers.",
        "s0_th": ["Layer", "What", "Analogy"],
        "s0_tbox": ["**T-Box** (schema)", "Which *kinds* of concepts and relationships exist (the blueprint)",
                    "A real-estate *floor plan* — rooms, corridors, connection rules"],
        "s0_abox": ["**A-Box** (instances)", "Each individual piece of *real data* (actual residents)",
                    "The *households that actually moved in* to that floor plan"],
        "s0_quote": ("> In short, **T-Box is the rules** and **A-Box is the real data that follows "
                     "those rules**. Sections 1–3 below show the T-Box (design); section 4 shows the "
                     "A-Box (real-data examples)."),
        "s0_domain_h": "### The problem this ontology solves",

        "s1_h": "## 1. The ontology at a glance (blueprint · T-Box)",
        "s1_desc": ("The full map of concepts (boxes) and relationships (arrows). "
                    "The text on each arrow is the 'name of the relationship'."),

        "s2_h": "## 2. Entities — what and why",
        "s2_desc": "Explains *which problem* each concept (entity) exists to solve.",
        "s2_th": ["Entity", "Key properties", "Key", "Why it's needed"],
        "why_missing": "_(description to be supplemented)_",

        "s3_h": "## 3. Relationships — what and why",
        "s3_desc": ("Relationships are 'meaningful connections' between concepts. Putting values "
                    "(e.g. score, evidence) on a relationship captures 'how much / why' they connect."),
        "s3_th": ["Relationship", "Connection", "Relationship properties", "Why it's needed"],

        "s4_h": "## 4. Real-data example (instances · A-Box)",
        "s4_desc": ("Putting real data into the blueprint (T-Box) above looks like this. "
                    "Out of {nodes} nodes and {edges} edges in total, only representative "
                    "samples per relationship are shown."),

        "s5_h": "## 5. Verified queries (evidence)",
        "s5_desc": ("Questions actually run during the workshop with confirmed results. "
                    "They are evidence of 'what this graph can answer'."),
        "s5_q": "- **Q. {q}** — {n} result(s)",
        "s5_none": "- (Queries verified during the workshop will be recorded here)",

        "neptune_small": ("Amazon Neptune (one db.r6g.large + one read replica) — "
                          "sufficient for PoC / small-to-mid scale"),
        "neptune_large": ("Amazon Neptune (db.r6g.xlarge or larger, Multi-AZ), "
                          "or consider Neptune Analytics in parallel for analytics-heavy workloads"),
        "s6": """## 6. Proposed AWS architecture

A configuration that promotes the property-graph ontology verified in the workshop straight to a production environment. Designed so the openCypher written locally runs on Neptune.

### Core components

- **Graph DB:** {neptune}
  - Initial load via openCypher / Bulk Loader CSV exported from local Kùzu
  - Query interface: openCypher (compatible with the workshop queries)
- **Data ingestion:** S3 (source CSV/Parquet, Block Public Access + SSE-KMS + HTTPS-only transport) → Neptune Bulk Loader; incremental via AWS Glue or Lambda-based ETL
- **API layer:** Expose graph queries via API Gateway + Lambda (or ECS/Fargate)
- **Agent/inference (optional):** Amazon Bedrock AgentCore — natural-language question → openCypher → Neptune query → answer
- **Visualization/BI:** Extend this workshop viewer for the ops dashboard, or integrate Amazon QuickSight / Graph Explorer

### Security implementation and shared responsibilities
- **AWS responsibilities (security OF the cloud):** physical, network and managed-service patching security for Amazon Neptune, Amazon S3, AWS Lambda and related infrastructure.
- **Customer responsibilities (security IN the cloud):** data classification, least-privilege IAM, VPC security groups, S3 bucket policies, KMS key policies, application authentication and audit logging.
- **Priority 1 — Network:** deploy Neptune in private subnets, allow port 8182 only from the application security group, and enable VPC Flow Logs. **Metric:** zero public internet exposure.
- **Priority 2 — IAM:** scope query roles to `neptune-db:ReadDataViaQuery` / `WriteDataViaQuery` on the target cluster ARN; scope Bulk Loader roles to `s3:GetObject` / `ListBucket` on the exact S3 prefix. **Metric:** zero wildcard resources.
- **Priority 3 — Encryption:** enable Neptune storage encryption with AWS KMS, S3 SSE-KMS, S3 bucket-policy Deny on `aws:SecureTransport=false`, and TLS 1.2+. **Metric:** 100% encryption at rest and in transit.
- **Priority 4 — AI security:** for Amazon Bedrock AgentCore, validate input length/schema, apply Amazon Bedrock Guardrails, enforce read-only openCypher output validation, and require human review. **Metric:** zero unvalidated query executions.

### Data flow
```mermaid
graph LR
  S3["Source data (S3)"] --> ETL["Glue / Lambda ETL"]
  ETL --> NEP["Amazon Neptune (openCypher)"]
  API["API GW + Lambda"] --> NEP
  USER["User / Agent"] --> API
  BR["Amazon Bedrock AgentCore (NL→Cypher)"] --> NEP
  USER --> BR
```

### Compliance for Korean customers
- If personal/biometric data is included, a **PIPA / ISMS-P** compliance track is required
- Region: ap-northeast-2 (Seoul) preferred; verify data-residency requirements
- Consider de-identification / encryption (KMS) for sensitive data before ingestion

> This is an initial proposal based on the current ontology size ({n_ent} entities, {n_rel} relationships); instance sizing will be finalized in the technical meeting based on real data volume, concurrency and SLA.""",

        "s7": """## 7. Migration & continuous-sync plan

A staged plan to move the ontology verified in the workshop into real operation and then **keep it continuously in sync with source data without breaking the graph**. Each stage is structured as *Goal · Tasks · Done criteria · Risks*.

```mermaid
graph LR
  P0["Stage 0<br/>PoC validation"] --> P1["Stage 1<br/>Data load"]
  P1 --> P2["Stage 2<br/>Auto-fill·inference"]
  P2 --> P3["Stage 3<br/>Go-live"]
  P3 --> P4["Stage 4<br/>Continuous sync"]
```

### Stage 0 — PoC validation (1–2 weeks)
- **Goal:** Reproduce the local graph identically on Amazon Neptune and confirm core query performance.
- **Tasks:** Load `exports/neptune.cypher` / Bulk CSV into S3→Neptune; re-run the workshop's verified queries.
- **Done:** Queries that passed in the workshop return identical results on Neptune within acceptable latency.
- **Risks:** openCypher function / index differences → pre-check compatibility.

### Stage 1 — Real-data load (2–4 weeks)
- **Goal:** Map available data (est. {n_have} kinds) to operational keys and load it; fix the collection scope for missing data ({n_need} kinds).
- **Tasks:** Map operational DB tables ↔ entity PKs, build the S3 ingestion pipeline (Glue/Lambda), design incremental load.
- **Done:** The graph is populated with real-data volume and key-integrity checks pass.
- **Risks:** Key mismatch / duplication → define integrity rules before loading.

### Stage 2 — Auto-fill empty metadata & inference (3–6 weeks)
- **Goal:** Auto-fill empty metadata (concepts, competencies, difficulty, etc.) with LLM/embeddings; infer related / precedence relationships.
- **Tasks:** Generate metadata with Amazon Bedrock, attach `source`/`confidence` to auto-generated edges, connect a (human) review workflow.
- **Done:** Auto-fill accuracy meets the sample-review bar and review status is reflected in the graph.
- **Risks:** Hallucination / misclassification → confidence threshold + human-review gate.

### Stage 3 — Go-live (4–8 weeks)
- **Goal:** Expose APIs/agents so services (chatbots, recommendations, etc.) query the graph in real time.
- **Tasks:** API Gateway + Lambda (or ECS), Amazon Bedrock AgentCore (NL→Cypher), monitoring / backup / PIPA·ISMS-P compliance track.
- **Done:** Responses within SLA, ops dashboard / alarms running, security review passed.
- **Risks:** Concurrency / cost → finalize instance sizing and caching strategy.

### Stage 4 — Continuous sync (steady-state, always-on)
A single load is not the end. Because source DBs and logs keep changing, the key is to **keep following them without breaking the graph**.

- **Goal:** Safely reflect changes in sources (operational DB, event logs) into the graph and keep integrity at all times.
- **Sync method per source:**
  - **Structured DB (tables):** CDC (AWS DMS/Debezium) or incremental batch by `updated_at` watermark → S3 staging → load. Suited to keyed master data (students, content, etc.).
  - **Events/logs (events such as completion, viewing):** Receive via Amazon Kinesis Data Streams or Amazon Data Firehose and load as **relationship (edge) appends**. Events are edge properties, not nodes (§T-Box rule).
  - **Auto-filled metadata (concepts, competencies, difficulty, etc.):** Re-infer with Amazon Bedrock only on changed sources; update `source`/`confidence`.
- **Graph-integrity principles (break prevention):**
  1. **Idempotent upsert** — Nodes/edges use `MERGE` then `SET` by PK. Even with reprocessing / duplicate events, the graph stays identical to a single application (at-least-once stream safe).
  2. **Schema-drift guard** — No automatic DDL on source column/type changes. T-Box changes are applied only after **human approval**; unknown properties are quarantined and alerted.
  3. **Referential integrity** — On edge load, verify both endpoint nodes exist first. If not, send to a hold queue (dead-letter) and retry after node load (keep orphan edges at 0).
  4. **Preserve human-reviewed edges** — Reviewed edges (`source=human`) are **not overwritten** by auto-recalculation. Only auto edges (`source=auto`) are regenerated.
  5. **Pre-load validation gate** — Before commit, run validation queries (empty labels, isolated nodes, cardinality violations, PK duplicates); on violation, abort the commit and roll back to the previous snapshot.
- **Operating rhythm:** Incremental batch for master data (e.g. hourly/daily), real-time / micro-batch for events, periodic full reconciliation to correct drift.
- **Monitoring:** Track node/edge count trends, empty-metadata ratio, confidence distribution, load-failure rate and dead-letter backlog via dashboards/alarms. Pause sync when thresholds are exceeded.
- **Done:** Source changes are reflected in the graph within the defined latency and the validation gate passes on every load (orphan edges / empty labels stay at 0).
- **Risks:** Stream duplication / out-of-order → idempotent upsert + ordering by event timestamp. Large backfills → split into a separate batch path to protect the real-time path.

### Next steps (immediate)
1. AWS SA technical meeting — review schema, load procedure and open issues using this handover (§9).
2. Data-mapping workshop — finalize the real tables/keys of available data (see §8).
3. PoC environment setup — start Stage 0 with Neptune + S3 + export load.""",

        "s8_h": "## 8. Data readiness & action items",
        "s8_summary": "Data status classified in the workshop ({total} elements total). **{summary}**.",
        "s8_unknown_note": "'Unknown' items could not be finalized in the workshop and are **to be filled in by the customer's email reply**.",
        "s8_th": ["Element", "Kind", "Status", "Location / Note"],
        "s8_await": "— (awaiting reply)",
        "s8_dash": "—",
        "ai_h": "### 8.1 Action items (Customer · Us)",
        "ai_quote": ("> The **Customer** items below could not be finalized during the workshop "
                     "(e.g. no developer present). Please **reply by email** and we'll reflect "
                     "them in the graph and report."),
        "ai_customer_h": "**Customer (confirm and reply):**",
        "ai_us_h": "**Us (proposal team):**",
        "ai_none": "- (None — all finalized in the workshop)",
        "ai_unknown": "**{name}** — Confirm whether the data exists and its location (system/table/key), and reply",
        "ai_missing": "**{name}** — Reply whether it can be collected/generated and how (or sourced externally)",
        "ai_partial": "**{name}** — Reply with the missing scope and how to complete it",
        "ai_us_default": [
            "Available/partial data: design real-schema ↔ entity-PK mapping (technical meeting)",
            "Missing/derived: scope an auto-fill (Amazon Bedrock) / inference PoC",
            "Set up the PoC environment (Neptune+S3) and re-run the workshop's verified queries",
        ],
        "s8m_ready": "- Readiness (est.): **{pct}%** ({avail}/{total} entities estimated to exist in current systems)",
        "s8m_note": "- (Once data status is classified in the workshop, this section is replaced by the actual table and action items.)",
        "s8m_have_h": "### Estimated available (schema-mapping targets)",
        "s8m_have_row": "- **{entity}** ← {source} · expected schema: `{schema}`",
        "s8m_none": "- (None)",
        "s8m_need_h": "### Needs to be newly prepared",
        "s8m_need_row": "- **{entity}** — {note}",
        "s8m_need_none": "- (None — all entities estimated to be covered by existing data)",
        "s8m_next_h": "### Next actions",
        "s8m_next": [
            "- Available data: confirm real table schemas and key mapping (technical meeting)",
            "- Missing data: define owner / cadence / format, scope the new pipeline",
        ],

        "s9_h": "## 9. Technical-meeting handover",
        "s9_desc": ("Items organized so the technical team can pick up the workshop agreements directly. "
                    "**This chapter is for developers; identifiers are written in the actual implementation "
                    "schema (English)** — they map 1:1 to the Korean concept names in the graph body (§0–§4)."),
        "s90_h": "### 9.0 Korean concept ↔ English schema mapping",
        "s90_th": ["Korean (workshop)", "English (implementation)", "Kind"],
        "s90_kind": {"entity": "Entity", "relation": "Relation", "prop": "Property"},
        "s91_h": "### 9.1 Finalized schema (T-Box)",
        "s91_ent_h": "**Entities**",
        "s91_rel_h": "**Relationships**",
        "s92": ["### 9.2 Export artifacts (for loading)",
                "- `exports/neptune.cypher` — openCypher CREATE script (for small-scale direct load)",
                "- `exports/bulk/nodes.csv`, `exports/bulk/edges.csv` — Neptune Bulk Loader format",
                "- Load procedure: upload to S3 → Neptune Bulk Loader or run openCypher"],
        "s93": ["### 9.3 Data-mapping action items",
                "- Available data: finalize operational-DB real tables/keys ↔ entity-PK mapping",
                "- Missing data: define owner/cadence/format, scope the new pipeline",
                "- Key integrity: validate join keys between entities (e.g. foreign key ↔ relationship src/dst)"],
        "s94": ["### 9.4 Validation points (for the technical team)",
                "- Confirm local openCypher → Neptune compatibility (functions, indexes, some clauses may differ)",
                "- Query performance: re-measure the workshop's verified queries at real-data volume",
                "- Finalize Neptune instance sizing based on concurrency / SLA"],
        "s95_h": "### 9.5 Open issues",
        "s95_default": [
            "Whether OWL reasoning is required — consider a triplestore in parallel if needed (out of current scope)",
            "De-identification policy for sensitive/personal data — masking scope to be agreed before ingestion",
            "When to connect remote (Neptune) live queries",
        ],
    },

    # =====================================================================
    "ja": {
        "html_lang": "ja",
        "default_title": "オントロジー・ワークショップ結果",
        "generated": "_生成: {now} · OntoForge_",

        "s0_h": "## 0. この文書の読み方 — オントロジーとは？",
        "s0_p1": ("**オントロジー**とは、業務上の「概念」と「概念どうしの関係」を、"
                  "コンピューターと人が一緒に理解できるよう整理した知識の地図です。"
                  "表計算が行と列でデータを保持するのに対し、オントロジーは"
                  "**点（概念）と矢印（関係）**で「何が何とどう繋がるか」を表します。"),
        "s0_p2": "このグラフは2つの層に分かれます。",
        "s0_th": ["層", "内容", "たとえ"],
        "s0_tbox": ["**T-Box**（スキーマ）", "どの*種類*の概念と関係が存在するか（設計図）",
                    "不動産の*間取り図* — 部屋・廊下・接続ルール"],
        "s0_abox": ["**A-Box**（インスタンス）", "実際の*データ*一件一件（実居住）",
                    "その間取り図に*実際に入居した世帯*"],
        "s0_quote": ("> つまり **T-Box はルール**、**A-Box はそのルールに従う実データ**です。"
                     "以下の1〜3章は T-Box（設計）を、4章は A-Box（実データ例）を示します。"),
        "s0_domain_h": "### このオントロジーが解決する課題",

        "s1_h": "## 1. オントロジー全体像（設計図 · T-Box）",
        "s1_desc": ("概念（箱）と関係（矢印）の全体地図です。"
                    "矢印の上の文字は「関係の名前」です。"),

        "s2_h": "## 2. エンティティ — 何を、なぜ",
        "s2_desc": "各概念（エンティティ）が*どの課題を解くため*に存在するかを説明します。",
        "s2_th": ["エンティティ", "主な属性", "キー", "なぜ必要か"],
        "why_missing": "_(説明の補足が必要)_",

        "s3_h": "## 3. 関係 — 何を、なぜ",
        "s3_desc": ("関係は概念と概念をつなぐ「意味のあるつながり」です。"
                    "関係に値（例：スコア・根拠）を付けると「どれだけ／なぜ繋がるか」まで表せます。"),
        "s3_th": ["関係", "接続", "関係の属性", "なぜ必要か"],

        "s4_h": "## 4. 実データ例（インスタンス · A-Box）",
        "s4_desc": ("上の設計図（T-Box）に実データを入れるとこうなります。"
                    "全ノード{nodes}件・エッジ{edges}件のうち、関係ごとの代表サンプルのみ抜粋しています。"),

        "s5_h": "## 5. 検証済みクエリ（説得の証拠）",
        "s5_desc": ("ワークショップで実際に実行し結果を確認した質問です。"
                    "「このグラフで何に答えられるか」の証拠です。"),
        "s5_q": "- **Q. {q}** — 結果 {n}件",
        "s5_none": "- （ワークショップ中に検証したクエリがここに記録されます）",

        "neptune_small": ("Amazon Neptune（db.r6g.large 1台 + 読み取りレプリカ 1台） — "
                          "PoC・中小規模に十分"),
        "neptune_large": ("Amazon Neptune（db.r6g.xlarge 以上、Multi-AZ）"
                          "または分析中心なら Neptune Analytics の併用を検討"),
        "s6": """## 6. AWS構築アーキテクチャ提案

ワークショップで検証したプロパティグラフ・オントロジーをそのまま本番環境へ昇格する構成。ローカルで書いた openCypher が Neptune で動くよう設計。

### 主要コンポーネント

- **グラフDB:** {neptune}
  - ローカル Kùzu からエクスポートした openCypher / Bulk Loader CSV で初期ロード
  - クエリインターフェース: openCypher（ワークショップのクエリと互換）
- **データ取込:** S3（ソース CSV/Parquet、Block Public Access + SSE-KMS + HTTPS 転送強制）→ Neptune Bulk Loader、増分は AWS Glue または Lambda ベースの ETL
- **API層:** API Gateway + Lambda（または ECS/Fargate）でグラフクエリを公開
- **エージェント/推論（任意）:** Amazon Bedrock AgentCore — 自然言語の質問 → openCypher 変換 → Neptune クエリ → 応答
- **可視化/BI:** 運用ダッシュボードは本ワークショップ・ビューアを拡張、または Amazon QuickSight・Graph Explorer と連携

### セキュリティ実装基準と責任分担
- **AWS の責任（クラウド自体のセキュリティ）:** Amazon Neptune、Amazon S3、AWS Lambda など管理サービス基盤の物理・ネットワーク・パッチ適用のセキュリティ。
- **顧客の責任（クラウド内のセキュリティ）:** データ分類、最小権限 IAM、VPC セキュリティグループ、S3 バケットポリシー、KMS キーポリシー、アプリケーション認証、監査ログ。
- **優先度 1 — ネットワーク:** Neptune をプライベートサブネットに配置し、アプリケーションのセキュリティグループからのみ 8182 を許可、VPC Flow Logs を有効化。**指標:** 公開インターネット露出 0。
- **優先度 2 — IAM:** クエリロールは対象クラスタ ARN の `neptune-db:ReadDataViaQuery` / `WriteDataViaQuery` に限定し、Bulk Loader ロールは正確な S3 prefix の `s3:GetObject` / `ListBucket` に限定。**指標:** ワイルドカードリソース 0。
- **優先度 3 — 暗号化:** AWS KMS による Neptune 保存時暗号化、S3 SSE-KMS、S3 `aws:SecureTransport=false` Deny、TLS 1.2+ を適用。**指標:** 保存・転送暗号化 100%。
- **優先度 4 — AI セキュリティ:** Amazon Bedrock AgentCore では入力長・スキーマ検証、Amazon Bedrock Guardrails、openCypher 出力の読み取り専用検証、人手レビューを適用。**指標:** 未検証クエリ実行 0。

### データフロー
```mermaid
graph LR
  S3["ソースデータ (S3)"] --> ETL["Glue / Lambda ETL"]
  ETL --> NEP["Amazon Neptune (openCypher)"]
  API["API GW + Lambda"] --> NEP
  USER["ユーザー / エージェント"] --> API
  BR["Amazon Bedrock AgentCore (NL→Cypher)"] --> NEP
  USER --> BR
```

### 韓国顧客のコンプライアンス
- 個人情報・生体情報を含む場合は **PIPA / ISMS-P** 準拠トラックが必要
- リージョン: ap-northeast-2（ソウル）優先、データ所在要件を確認
- 機微情報は取込前に非識別化／暗号化（KMS）の適用を検討

> 現在のオントロジー規模（エンティティ {n_ent}、関係 {n_rel}）を基準とした初期提案であり、実データ量・同時実行・SLA に応じてインスタンスのサイジングは技術ミーティングで確定します。""",

        "s7": """## 7. 移行 & 継続同期プラン

ワークショップで検証したオントロジーを実運用へ移し、その後も**ソースデータと継続的に同期しながらグラフを壊さずに維持する**ための段階的計画です。各段階は*目標 · 作業 · 完了判断 · リスク*で構成されます。

```mermaid
graph LR
  P0["段階0<br/>PoC検証"] --> P1["段階1<br/>データ投入"]
  P1 --> P2["段階2<br/>自動補完·推論"]
  P2 --> P3["段階3<br/>本番移行"]
  P3 --> P4["段階4<br/>継続同期"]
```

### 段階0 — PoC検証（1〜2週）
- **目標:** ローカルグラフを Amazon Neptune で同一に再現し、主要クエリの性能を確認。
- **作業:** `exports/neptune.cypher`/Bulk CSV を S3→Neptune に投入、ワークショップの検証クエリを再実行。
- **完了判断:** ワークショップで通過したクエリが Neptune でも同一結果 + 許容遅延内。
- **リスク:** openCypher の関数・インデックス差異 → 事前の互換性チェック。

### 段階1 — 実データ投入（2〜4週）
- **目標:** 保有データ（推定{n_have}種）を運用キーにマッピングして投入、未保有データ（{n_need}種）の収集範囲を確定。
- **作業:** 運用DBテーブル ↔ エンティティPKのマッピング、S3投入パイプライン（Glue/Lambda）の構成、増分投入の設計。
- **完了判断:** 実データ量でグラフが満たされ、キー整合性チェックを通過。
- **リスク:** キー不一致・重複 → 投入前に整合性ルールを定義。

### 段階2 — 空メタの自動補完・推論（3〜6週）
- **目標:** 空のメタ（概念・コンピテンシー・難易度など）を LLM/埋め込みで自動補完、関連・先後関係を推論。
- **作業:** Amazon Bedrock でメタ生成、自動生成エッジに `source`/`confidence` を付与、レビュー（人手確認）ワークフローを接続。
- **完了判断:** 自動補完の精度がサンプルレビュー基準を満たし、レビュー状態がグラフに反映。
- **リスク:** ハルシネーション・誤分類 → confidence 閾値 + 人手レビューゲート。

### 段階3 — 本番移行（4〜8週）
- **目標:** サービス（チャットボット・推薦など）がグラフをリアルタイムに照会できるよう API/エージェントを公開。
- **作業:** API Gateway+Lambda（または ECS）、Amazon Bedrock AgentCore（NL→Cypher）、監視・バックアップ・PIPA/ISMS-P コンプライアンストラック。
- **完了判断:** SLA 内応答、運用ダッシュボード・アラーム稼働、セキュリティ点検を通過。
- **リスク:** 同時実行・コスト → インスタンスのサイジングとキャッシュ戦略を確定。

### 段階4 — 継続同期（定常運用、常時）
一度の投入で終わりではありません。既存DB・ログが変わり続けるため、**グラフを壊さずに追従し続ける**ことが核心です。

- **目標:** ソース（運用DB・イベントログ）の変更をグラフに安全に反映し、整合性を常時維持。
- **ソース別の同期方式:**
  - **構造化DB（テーブル）:** CDC（AWS DMS/Debezium）または `updated_at` ウォーターマーク基準の増分バッチ → S3 ステージング → 投入。キーのあるマスターデータ（生徒・コンテンツ等）に適する。
  - **イベント/ログ（完了・視聴などの事象）:** Amazon Kinesis Data Streams または Amazon Data Firehose で受け、**関係（エッジ）append** として投入。事象はノードではなくエッジ属性に（§T-Box ルール）。
  - **自動補完メタ（概念・コンピテンシー・難易度等）:** ソース変更分のみ Amazon Bedrock で再推論、`source`/`confidence` を更新。
- **グラフ整合性の原則（破損防止）:**
  1. **冪等 Upsert** — ノード・エッジは PK 基準で `MERGE` 後 `SET`。再処理・重複イベントが来てもグラフは一度適用したものと同一（at-least-once ストリーム安全）。
  2. **スキーマドリフト・ガード** — ソースの列/型変更で自動 DDL は禁止。T-Box 変更は**人の承認**後に反映し、未知の属性は隔離（quarantine）してアラート。
  3. **参照整合性** — エッジ投入時に両端ノードの先存在を確認。無ければ保留キュー（dead-letter）へ送り、ノード投入後に再試行（孤立エッジ0を維持）。
  4. **人手レビュー済みエッジの保全** — レビュー済み（`source=human`）エッジは自動再計算で**上書きしない**。自動エッジ（`source=auto`）のみ再生成。
  5. **投入前バリデーションゲート** — コミット前に検証クエリ（空ラベル・孤立ノード・カーディナリティ違反・PK重複）を実行、違反時はコミット中断 + 直前スナップショットへロールバック。
- **運用リズム:** マスターデータは増分バッチ（例: 時間/日次）、イベントはリアルタイム/マイクロバッチ、定期的な全体照合（reconciliation）でドリフトを補正。
- **監視:** ノード・エッジ数の推移、空メタ比率、confidence 分布、投入失敗率・dead-letter 滞留をダッシュボード/アラームで。閾値超過時は同期を一時停止。
- **完了判断:** ソース変更が定義された遅延内にグラフへ反映され、検証ゲートが毎回の投入で通過（孤立エッジ・空ラベル0を維持）。
- **リスク:** ストリーム重複・順序逆転 → 冪等 Upsert + イベントタイムスタンプ基準の整列。大量バックフィル → 別バッチ経路に分離してリアルタイム経路を保護。

### 次のステップ（即時）
1. AWS SA 技術ミーティング — 本引継書（§9）でスキーマ・投入手順・オープン課題をレビュー。
2. データマッピング・ワークショップ — 保有データの実テーブル・キーを確定（§8 参照）。
3. PoC 環境セットアップ — Neptune + S3 + エクスポート投入で段階0に着手。""",

        "s8_h": "## 8. データ準備状況 & アクションアイテム",
        "s8_summary": "ワークショップで分類したデータ状況です（全{total}要素）。**{summary}**。",
        "s8_unknown_note": "「不明」はワークショップ中に確定できず、**顧客のメール回答で埋める項目**です。",
        "s8_th": ["要素", "種類", "状態", "所在 / メモ"],
        "s8_await": "— （回答待ち）",
        "s8_dash": "—",
        "ai_h": "### 8.1 アクションアイテム（顧客 · 当方）",
        "ai_quote": ("> 以下の**顧客**項目はワークショップ中（開発者不在など）に確定できなかった部分です。"
                     "**メールでご回答**いただければグラフ・レポートに反映します。"),
        "ai_customer_h": "**顧客（確認後に回答）:**",
        "ai_us_h": "**当方（提案チーム）:**",
        "ai_none": "- （なし — ワークショップですべて確定）",
        "ai_unknown": "**{name}** — データの保有有無と所在（システム/テーブル/キー）を確認して回答",
        "ai_missing": "**{name}** — 収集/生成の可否と方法（または外部調達）を回答",
        "ai_partial": "**{name}** — 欠落範囲と補完方法を回答",
        "ai_us_default": [
            "保有/一部保有データ: 実スキーマ ↔ エンティティPK のマッピング設計（技術ミーティング）",
            "未保有/派生: 自動補完（Amazon Bedrock）・推論 PoC の範囲策定",
            "PoC 環境（Neptune+S3）のセットアップとワークショップ検証クエリの再実行",
        ],
        "s8m_ready": "- 準備度（推定）: **{pct}%**（{avail}/{total} エンティティが既存システムに存在すると推定）",
        "s8m_note": "- （ワークショップでデータ状況を分類すると、この節は実際の表・アクションアイテムに置き換わります。）",
        "s8m_have_h": "### 保有推定（スキーマ・マッピング対象）",
        "s8m_have_row": "- **{entity}** ← {source} · 想定スキーマ: `{schema}`",
        "s8m_none": "- （該当なし）",
        "s8m_need_h": "### 新規整備が必要",
        "s8m_need_row": "- **{entity}** — {note}",
        "s8m_need_none": "- （なし — すべてのエンティティが既存データでカバーと推定）",
        "s8m_next_h": "### 次のアクション",
        "s8m_next": [
            "- 保有データ: 実テーブルのスキーマとキーのマッピングを確認（技術ミーティング）",
            "- 未保有データ: 収集主体・周期・フォーマットを定義、新規パイプラインの範囲を策定",
        ],

        "s9_h": "## 9. 技術ミーティング引継書",
        "s9_desc": ("ワークショップの合意内容を技術チームがそのまま引き継げるよう整理した項目。"
                    "**本章は開発者向けで、識別子は実装スキーマ（英語）で表記**します"
                    "— グラフ本文（§0〜§4）の韓国語の概念名と1:1で対応します。"),
        "s90_h": "### 9.0 韓国語概念 ↔ 英語スキーマ マッピング",
        "s90_th": ["韓国語（ワークショップ）", "英語（実装）", "区分"],
        "s90_kind": {"entity": "エンティティ", "relation": "関係", "prop": "属性"},
        "s91_h": "### 9.1 確定スキーマ（T-Box）",
        "s91_ent_h": "**エンティティ**",
        "s91_rel_h": "**関係**",
        "s92": ["### 9.2 エクスポート成果物（投入用）",
                "- `exports/neptune.cypher` — openCypher CREATE スクリプト（小規模の直接投入用）",
                "- `exports/bulk/nodes.csv`, `exports/bulk/edges.csv` — Neptune Bulk Loader 形式",
                "- 投入手順: S3 アップロード → Neptune Bulk Loader または openCypher 実行"],
        "s93": ["### 9.3 データマッピング・アクションアイテム",
                "- 保有データ: 運用DBの実テーブル・キー ↔ エンティティPK のマッピングを確定",
                "- 未保有データ: 収集主体/周期/フォーマットを定義、新規パイプラインの範囲を策定",
                "- キー整合性: エンティティ間の結合キー（例: 外部キー ↔ 関係の src/dst）を検証"],
        "s94": ["### 9.4 検証ポイント（技術チーム確認）",
                "- ローカル openCypher → Neptune 互換性の確認（関数・インデックス・一部の句に差異の可能性）",
                "- クエリ性能: ワークショップ検証クエリを実データ量で再測定",
                "- 同時実行・SLA に応じた Neptune インスタンスのサイジング確定"],
        "s95_h": "### 9.5 オープン課題",
        "s95_default": [
            "OWL 推論の要否 — 必要ならトリプルストアの併用を検討（現範囲外）",
            "機微/個人情報の非識別化ポリシー — 投入前にマスキング範囲の合意が必要",
            "リモート（Neptune）ライブクエリ接続の時期",
        ],
    },
}


def strings(lang: str | None) -> dict:
    return REPORT[lang_of(lang)]
