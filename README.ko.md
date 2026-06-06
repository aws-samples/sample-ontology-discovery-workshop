# OntoForge — 온톨로지 디스커버리 워크샵 도구

**한국어** · [English](./README.md) · [日本語](./README.ja.md)

고객과 **대화하며 온톨로지를 실시간으로 만들고 검증**하는 로컬 도구다. 합의된 온톨로지는 그대로 Amazon Neptune으로 승격(promote)하여 구성을 활용, 데이터 모델을 구축하여 향후 온톨로지 구축에 활용할 수 있습니다.

## 데모

![OntoForge 데모](./images/demo.gif)

## 무엇을 하나
1. 대화에서 엔티티·관계·속성을 구조화 → **Kùzu(임베디드 property graph)** 에 실시간 반영
2. 스키마(T-Box) / 인스턴스(A-Box)를 **실시간 그래프로 시각화** (Cytoscape.js)
3. 고객 질문을 **openCypher로 검증** — "이 답이 진짜 그래프에서 나오네요"
4. 온톨로지 문서(Markdown, Obsidian 호환) 자동 생성
5. **Neptune 익스포트** (openCypher 스크립트 + Bulk Loader CSV)

자세한 설계·보안 제약·범위는 [`docs/DESIGN.md`](./docs/DESIGN.md)와
[`docs/THREAT_MODEL.md`](./docs/THREAT_MODEL.md), 대화 스킬은
[`skills/WORKSHOP_SKILLS.md`](./skills/WORKSHOP_SKILLS.md) 참조.

### 워크샵 운영 (M2)
- **백지 시작**: 좌측 상단 `⟲ 백지` 버튼 → 새 고객 대화를 처음부터 쌓기
- **변경 모드**: 사이드바의 엔티티/관계 칩을 클릭하면 삭제(관련 관계 연쇄 삭제). 대화 중 "모의고사 추가하면?" 같은 변경이 실시간 반영
- **산출물 3종**: `📄 워크샵 산출물 3종 생성` 버튼 → `exports/report/`에 생성
  1. 워크샵 서머리 (엔티티·관계·검증 질의)
  2. AWS 구축 아키텍처 제안 (Neptune 규모 자동 추정 + 데이터 흐름 + 컴플라이언스)
  3. 데이터 준비 상태 (보유/미보유 분류, 준비도 %)
  4. **기술 미팅 인계서** — 확정 스키마, 적재용 익스포트 안내, 데이터 매핑 액션, 검증 포인트, 오픈 이슈
  - 포맷: Markdown + HTML + PDF(weasyprint) + docx(python-docx)
  - 인계 번들: 같은 폴더에 `neptune.cypher` + `bulk/*.csv`도 함께 생성 → 기술팀에 폴더째 전달

### 질의 실행 대상
현재 **Cytoscape**에 실제 openCypher를 실행해 결과를 시각화한다. 리모트 Neptune
라이브 쿼리는 M3 예정(현재는 익스포트만).

## 빠른 시작

### Windows (PowerShell)
```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH="src"
uvicorn ontology_workshop.server:app --reload
# 브라우저: http://localhost:8000
```
> weasyprint는 Windows에서 GTK 런타임이 없으면 설치/실행이 까다로울 수 있다.
> 그 경우 PDF만 자동으로 건너뛰고(나머지 3포맷은 정상 생성), HTML 리포트를
> 브라우저에서 "인쇄 → PDF로 저장"하면 된다. 도구가 그렇게 안내한다.

### macOS / Linux
```bash
pip install -r requirements.txt

# 데모 데이터 시드 + 콘솔 출력
PYTHONPATH=src python src/seed_demo.py

# 워크샵 서버 (실시간 시각화 + 스킬 패널)
PYTHONPATH=src uvicorn ontology_workshop.server:app --reload
# 브라우저에서 http://localhost:8000
```

### 유지/복원
워크샵 데이터는 기본적으로 `workshop.kuzu`에 저장됩니다. 기존 워크샵을 이어서 불러오려면 `ONTOFORGE_FRESH=1` 없이 서버를 다시 시작하세요.

```bash
PYTHONPATH=src uvicorn ontology_workshop.server:app --host 127.0.0.1 --port 8000
```

정상 재시작 시 OntoForge는 다음 데이터를 다시 로드합니다.

- 그래프 스키마와 인스턴스 데이터: `workshop.kuzu`
- 워크샵 진행 피드와 검증 질의: `exports/session/workshop_snapshot.json`
- Kùzu 그래프가 비어 있는 경우: autosave 스냅샷의 최신 그래프 상태

그래프·진행 로그·검증 질의·import·reset·report가 바뀔 때마다 `exports/session/workshop_snapshot.json`에 자동 저장됩니다. 따라서 대부분의 워크샵은 위 정상 시작 명령으로 다시 복구할 수 있습니다.

`ONTOFORGE_FRESH=1`은 시작 시 로컬 Kùzu DB를 삭제해야 할 때만 사용하세요. 실수로 fresh 실행을 했다면 autosave 파일이 남아 있는 동안 `ONTOFORGE_FRESH=1` 없이 다시 시작하면 복원할 수 있습니다.

새 워크샵을 명시적으로 시작하려면 서버를 정상 기동한 뒤 UI의 reset 버튼을 누르거나 다음 명령을 호출하세요.

```bash
curl -X POST http://localhost:8000/reset
```

### 대화 스킬 (M1)
좌측 패널에서 고객 답변을 받아적고 스킬을 실행하면 엔티티·관계가 자동으로
그래프·시각화·문서에 반영된다. 추출 경로는 두 가지:
- `ANTHROPIC_API_KEY` 환경변수가 있으면 **Claude API(Sonnet)** 로 추출
- 없으면 **오프라인 규칙 기반 추출기**로 대체 (현장 데모 안정성)
외부 Claude API 사용은 고객 데이터 처리·법무·보안 승인이 있는 경우에만 켠다.
승인이 없거나 민감정보가 포함될 수 있으면 `ANTHROPIC_API_KEY`를 설정하지 말고
오프라인 추출기로 진행하거나, 후속 구현 단계에서 Amazon Bedrock의 승인된 모델 경로를 사용한다.

오프라인 추출기 도메인 커버리지: 교육 / 미디어·엔터테인먼트 / 게임 / 스포츠 /
제조·하이테크 / 텔코 / 자동차 / 엔터프라이즈(복합기업·계열사 모델 포함).
한국어 입력은 영문 PascalCase 엔티티명(`학생→Student`, `차량→Vehicle` 등)으로
표준화된다. 추가 도메인은 `src/ontology_workshop/skills.py`의 `_ENTITY_HINTS`와
`_mock_relations`에 1줄씩 추가.

```bash
export ANTHROPIC_API_KEY=<approved-api-key>   # 선택: API 추출 사용 시
```

## 아키텍처
정식 구성도는 [`docs/architecture.puml`](./docs/architecture.puml)에 있으며,
보안 설계는 [`docs/DESIGN.md`](./docs/DESIGN.md)와
[`docs/THREAT_MODEL.md`](./docs/THREAT_MODEL.md)에 정리되어 있다.

```
대화(Claude+스킬) → 오케스트레이터(FastAPI) → Kùzu (단일 진실원천, openCypher)
                                          ├─ WebSocket → Cytoscape 시각화
                                          ├─ Markdown 문서
                                          └─ Neptune 익스포트
```

## 보안 구성
OntoForge는 단일 운영자 로컬 워크샵 도구다. 고객 민감정보를 다룰 때는 아래 설정을 적용한다.

1. 로컬 서버는 `127.0.0.1`에 바인딩하고, 공유 네트워크에 노출하지 않는다. Loopback 접속(`localhost`, `127.0.0.1`, `::1`)은 기본적으로 토큰 없이 허용된다.
2. 기본 로컬 실행은 토큰 없이 시작한다.
   ```bash
   PYTHONPATH=src uvicorn ontology_workshop.server:app --host 127.0.0.1 --port 8000
   # 브라우저: http://localhost:8000
   ```
3. 공유 네트워크에 노출하거나 localhost에서도 인증을 강제해야 하면 REST/WebSocket 접근 토큰을 설정한다.
   ```bash
   export ONTOFORGE_TOKEN="$(openssl rand -hex 24)"
   export ONTOFORGE_REQUIRE_TOKEN=1  # localhost에서도 토큰을 강제할 때만 설정
   PYTHONPATH=src uvicorn ontology_workshop.server:app --host 127.0.0.1 --port 8000
   # 브라우저: http://localhost:8000/?token=$ONTOFORGE_TOKEN
   # curl 사용 시: -H "X-OntoForge-Token: $ONTOFORGE_TOKEN"
   ```
4. TLS가 필요한 환경에서는 uvicorn SSL 옵션을 사용한다.
   ```bash
   uvicorn ontology_workshop.server:app --host 127.0.0.1 --port 8000 \
     --ssl-keyfile key.pem --ssl-certfile cert.pem
   ```
5. `workshop.kuzu`와 `exports/`는 FileVault/BitLocker/LUKS 같은 암호화 파일시스템 위에 둔다. Export 파일은 `./exports` 아래로만 생성되며 `0600` 권한으로 저장된다.
6. `ANTHROPIC_API_KEY`는 환경변수나 승인된 secret manager에만 저장한다. 고객 개인정보·생체정보·규제 데이터는 마스킹하거나, 외부 LLM 호출을 끄고 오프라인 추출기로 진행한다.
7. Amazon Neptune 적재 전에는 [`docs/NEPTUNE_SECURITY.md`](./docs/NEPTUNE_SECURITY.md)의 IAM, S3, VPC, KMS, 감사 로그 기준을 적용한다.

데이터 분류와 보존/삭제 기준은 [`DATA_CLASSIFICATION.md`](./DATA_CLASSIFICATION.md), 보안 신고와 스캔 기록은 [`SECURITY.md`](./SECURITY.md)를 따른다.

## 주요 제약
- 내부 모델은 **property graph 단일**. T-Box/A-Box는 UI에서 개념 분리.
- **OWL 추론은 범위 밖** — 필요 시 Cypher 규칙으로 흉내, 진짜 추론은 별도 트랙.
- 로컬 openCypher → Neptune은 **대부분** 호환(100% 아님). 적재·튜닝은 기술 미팅 단계.
- 워크샵은 고객 보안망 내 로컬 실행. 외부 통신은 Claude API 호출뿐.

## 라이선스
이 프로젝트는 Apache-2.0 라이선스로 제공된다. 자세한 내용은 [`LICENSE`](./LICENSE)를 참조한다.
