# 로컬 웹 사용법

로컬 AI가 작성한 그래프 모델을 브라우저에서 확인합니다. Cypher 조회, 모델 변경 이력, 타입 목록, 품질 경고, 노드 상세를 제공합니다.

## 설치와 실행

Python 3.10 이상을 사용합니다. 다음 명령은 현재 프로젝트 폴더에서 실행합니다.

```bash
python3 -m venv viz-server/.venv
viz-server/.venv/bin/python -m pip install -r viz-server/requirements.txt
bash scripts/serve.sh
```

다른 프로젝트에 설치하려면 다음 명령을 실행합니다.

```bash
bash scripts/install.sh --target=all --workspace=/path/to/project --no-hook
```

`--target`은 `claude-code`, `kiro`, `all` 중 하나입니다. `all`은 `AGENTS.md`도 설치합니다. 기존 파일이 있으면 워크숍 규칙의 참조를 추가합니다.

서버는 `127.0.0.1`에서 실행합니다. 기본 시작 포트는 5173이고 사용 중이면 다음 포트를 찾습니다. 실행 시 PID, URL, 데이터 경로를 출력합니다.

```bash
bash scripts/serve.sh --data-dir ontology-docs/viz-runtime --no-browser
```

`--port-start`, `--port-end`, `--static-dir`을 지정할 수 있습니다. `ONTOLOGY_PYTHON`은 사용할 Python 경로입니다. 종료하려면 실행한 터미널에서 Ctrl-C를 누릅니다. Kuzu를 설치하지 않으면 시각화와 품질 검사는 사용할 수 있고 Cypher 조회만 비활성화됩니다.

## 예제 열기

다음 명령은 가상 결제 정산 데이터를 `output/demo/`에 게시합니다.

```bash
python3 viz-server/agent.py --data-dir output/demo/viz-runtime publish \
  --file examples/payment-settlement/workshop-model.json \
  --actor local-ai --summary '결제 정산 예제'
bash scripts/serve.sh --data-dir output/demo/viz-runtime
```

이미 게시한 폴더라면 다음 절차로 버전을 확인한 뒤 갱신합니다.

## 로컬 AI의 모델 작성

```bash
python3 viz-server/agent.py --data-dir ontology-docs/viz-runtime inspect
python3 viz-server/agent.py --data-dir ontology-docs/viz-runtime publish \
  --file ontology-docs/05-ontology/model-draft.json \
  --actor local-ai --summary '사용자가 확인한 관계 수정' \
  --expected-revision '<inspect의 document_revision>'
python3 viz-server/agent.py --data-dir ontology-docs/viz-runtime quality
```

첫 게시만 `--expected-revision`을 생략합니다. 사용자 확인 근거는 `--approval-note`로 기록할 수 있습니다. 응답 원문은 별도로 `audit.md`에 추가합니다.

게시할 때 모델 구조와 예상 버전을 검사합니다. 변경 전후는 `revisions/`에 남기고 `current.json`을 원자적으로 교체합니다. 작성자, 사유, 검토 결정도 이력에 포함됩니다. 브라우저는 5초마다 갱신하며 모델이 바뀌면 이전 쿼리 결과를 지웁니다.

## 모델 형식

T-box에는 타입 정의를, `snapshot`에는 A-box 인스턴스를 저장합니다.

```json
{
  "metadata": {"title": "가맹점 모델", "phase": "05-ontology", "depth": "standard"},
  "tbox": {
    "entities": {
      "Merchant": {
        "label": "가맹점",
        "primary_key": "merchant_id",
        "properties": {"merchant_id": "STRING", "name": "STRING"},
        "status": "candidate",
        "trace_links": ["story-001"]
      }
    },
    "relations": {}
  },
  "snapshot": {"nodes": [], "edges": []},
  "queries": [{"title": "가맹점 조회", "cypher": "MATCH (merchant:Merchant) RETURN merchant LIMIT 25"}]
}
```

- 엔티티 타입은 `properties`, `primary_key`를 정의합니다.
- 관계 타입은 `src`, `dst`, `cardinality`, `properties`를 정의합니다.
- 인스턴스는 `{data:{id,label,etype,props,trace_links}}` 형식입니다.
- 인스턴스 관계는 `{data:{id,source,target,rtype,props,trace_links}}` 형식입니다.
- 속성 타입은 `STRING`, `INT64`, `DOUBLE`, `BOOLEAN`, `DATE`, `TIMESTAMP`와 각 배열입니다. 속성 정의에 `required`, `enum`을 추가할 수 있습니다.
- `personas`, `bounded_context`, `source_files`, `description`으로 업무 설명과 근거를 기록합니다. `source_files`는 워크숍 폴더 안의 Markdown 상대 경로입니다.
- 타입과 속성 키는 ASCII 식별자를 사용합니다. 표시 이름과 값은 한국어로 작성할 수 있습니다. `viz_id`와 `display_label`은 웹에서 사용하는 예약 속성입니다.
- 기존 `{metadata,elements:{nodes,edges}}` 형식은 통합 그래프로 표시합니다. T-box와 A-box를 추정해서 나누지 않습니다.

전체 예제는 `examples/payment-settlement/workshop-model.json`에 있습니다.

## Cypher 조회

왼쪽 패널에서 쿼리를 작성하거나 AI가 남긴 쿼리를 선택합니다. JSON 파라미터를 넣을 수 있습니다. 노드나 경로가 반환되면 그래프에서 해당 결과를 강조할 수 있습니다.

로컬 AI에서도 같은 조회를 실행할 수 있습니다.

```bash
viz-server/.venv/bin/python viz-server/agent.py --data-dir ontology-docs/viz-runtime query \
  --actor local-ai --cypher 'MATCH (node) RETURN node LIMIT 25'
```

조회는 게시된 A-box의 Kuzu 복제본에서 읽기 전용으로 실행합니다. 실행한 쿼리와 결과 상태는 `query-history.jsonl`에 기록합니다. 한 번에 최대 200행을 반환하고 쿼리 실행 시간은 3초로 제한합니다.

## Cypher 내보내기

웹의 내보내기 메뉴에서 파일을 선택합니다.

| 메뉴 | 파일 | 내용 |
|---|---|---|
| T-box 스키마 Cypher | `ontology-schema.cypher` | 타입, 속성 타입, 기본 키, 관계 양 끝의 타입 |
| A-box 데이터 Cypher | `ontology-data.cypher` | 현재 인스턴스와 관계의 생성문 |
| 전체 모델 Cypher | `ontology-model.cypher` | 스키마 정의와 데이터 생성문 |

로컬 AI는 다음 명령으로 저장할 수 있습니다.

```bash
python3 viz-server/agent.py --data-dir ontology-docs/viz-runtime export-cypher \
  --scope schema --output exports/ontology-schema.cypher
python3 viz-server/agent.py --data-dir ontology-docs/viz-runtime export-cypher \
  --scope model --output exports/ontology-model.cypher
```

`--scope`은 `schema`, `data`, `model` 중 하나입니다. `--output`을 생략하면 Cypher를 stdout으로 출력합니다. 같은 이름의 파일은 덮어쓰지 않습니다.

스키마는 로컬 Kuzu의 `CREATE NODE TABLE`, `CREATE REL TABLE` 문장으로 작성합니다. 속성의 `required`, `enum`, 설명과 근거는 `COMMENT ON TABLE`에 보존합니다. 선언한 기본 키를 사용하며, 기본 키가 없는 타입은 `viz_id`를 사용합니다. 데이터 생성문은 문자열, 숫자, 날짜, 배열과 관계 속성을 포함합니다.

전체 모델 파일은 빈 로컬 DB에 적용합니다. 스키마와 데이터를 따로 저장했다면 스키마 파일부터 적용합니다. 내보내기는 파일만 생성하고 DB에는 실행하지 않습니다. 브라우저의 조회창에서도 생성문은 실행할 수 없습니다.

그래프 필터와 관계없이 현재 게시된 모델 전체를 저장합니다. 데이터 타입, 식별자, 관계가 잘못되었거나 미정의 속성이 있으면 내보내기 전에 수정해야 합니다. 스키마만 저장할 때는 인스턴스 값이 없어도 됩니다.

## 품질 검사

고립 노드, 근거 누락, 연결 집중, 여러 컨텍스트의 책임 혼재, 중복 후보, 재귀 관계를 검사합니다. ID 중복, 관계 끝점, 속성 타입, 필수값, 식별자, 카디널리티도 확인합니다. `minimal`, `standard`, `comprehensive`에 따라 검사 범위가 달라집니다.

경고를 클릭하면 대상과 근거를 확인할 수 있습니다. 구조 오류는 빨간색, 경고는 주황색으로 표시합니다. 판단과 수정은 사용자 확인 후 로컬 AI에서 진행합니다.

예외로 남길 항목은 다음과 같이 기록한 뒤 다시 게시합니다.

```json
{
  "quality_decisions": {
    "<경고 ID>": {
      "status": "suppressed",
      "revision": "<현재 graph revision>",
      "actor": "<검토자>",
      "reason": "<사용자가 확인한 사유>"
    }
  }
}
```

검토 상태는 `accepted` 또는 `suppressed`입니다. 그래프가 바뀌면 기존 예외를 다시 검토합니다. 구조 검사만으로 업무 의미를 확정하지 않습니다.

## API

| 경로 | 기능 |
|---|---|
| `GET /api/state` | 현재 모델, 버전, 품질 결과, 세션 토큰 |
| `GET /api/history` | 최근 게시 이력 |
| `GET /api/quality` | 품질 보고서 |
| `GET /api/queries` | 실행 쿼리 이력 |
| `GET /api/export/cypher?scope=model` | Cypher 파일명과 내용 |
| `POST /api/query` | `{cypher, parameters, revision}` 읽기 전용 조회 |
| `POST /feedback` | `{nodeId, note, revision}` 검토 요청 |
| `POST /render-status` | 현재 버전의 렌더링 결과 |
| `GET /health` | 서버와 브라우저 렌더링 상태 |
| `GET /source/<relative.md>` | 워크숍 Markdown 원문 |

POST에는 JSON과 `X-Ontology-Token`이 필요합니다. 서버는 localhost Host와 동일 Origin을 확인합니다. 현재 버전과 다른 조회나 내보내기 요청은 409로 반환합니다.

모델 문서의 크기 제한은 8 MiB입니다. `/health`의 `ok`는 현재 버전이 브라우저에 렌더링됐다는 뜻입니다. 피드백은 `feedback-pending.md`에 추가되며 AI가 다음 단계 확인 시 처리합니다.

## 이미지와 JSON

PNG와 SVG는 현재 보이는 그래프를 저장합니다. JSON은 게시된 모델 전체를 저장합니다. 드래그한 노드 위치는 페이지가 열려 있는 동안 유지됩니다.
