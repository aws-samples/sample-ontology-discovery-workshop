# 로컬 AI 워크숍 실행

저장소 루트에서 실행합니다. 모델 작성은 로컬 AI가 담당하고 웹은 시각화, 상세 확인, 읽기 전용 Cypher 조회를 제공합니다.

## 설치

```bash
python3 -m venv viz-server/.venv
viz-server/.venv/bin/python -m pip install -r viz-server/requirements.txt
bash scripts/test-viz.sh
```

## 예제 확인

```bash
python3 viz-server/agent.py --data-dir output/workshop-demo/viz-runtime publish \
  --file examples/payment-settlement/workshop-model.json \
  --actor local-test --summary '워크숍 실행 점검용 예시'
bash scripts/serve.sh \
  --data-dir output/workshop-demo/viz-runtime \
  --port-start 5173 --port-end 5173
```

`http://127.0.0.1:5173`에서 확인합니다. 예제에는 가상의 엔티티 타입 5개, 관계 타입 3개, 인스턴스 7개, 관계 7개가 있습니다. 고립된 `ReviewNote`는 품질 경고를 확인하기 위한 항목입니다.

예제가 이미 게시되어 있으면 `publish`를 반복하지 않고 서버만 실행합니다. 새 예제가 필요하면 다른 데이터 폴더를 지정합니다.

## 실제 워크숍

로컬 AI에서 `/onto-discover` 또는 `온톨로지 발견 시작`으로 진행합니다. 기존 상태 파일이 있으면 재개 안내를 확인합니다. 실제 결과는 `ontology-docs/`에 보존하고 예제 폴더와 섞지 않습니다.

필요하면 실제 화면을 별도 포트에서 엽니다.

```bash
bash scripts/serve.sh \
  --data-dir ontology-docs/viz-runtime \
  --port-start 5180 --port-end 5180
```

로컬 AI에 데이터 경로와 `http://127.0.0.1:5180` 주소를 알려줍니다. 모델이 게시되기 전에는 빈 그래프가 표시됩니다.

## 시작 전 확인

1. 예제 화면인지 실제 세션인지 확인합니다.
2. T-box와 A-box를 전환합니다.
3. 타입과 노드의 속성을 확인합니다.
4. Cypher 조회 결과와 필요한 내보내기 파일을 확인합니다.

```bash
curl -s http://127.0.0.1:5180/health
```

브라우저가 현재 모델을 정상 렌더링하면 `status`가 `ok`가 됩니다. 모델의 의미와 결정 근거는 참가자가 확인합니다.

서버 종료는 실행한 터미널에서 Ctrl-C를 사용합니다. 재개하려면 같은 폴더에서 같은 명령을 실행합니다. `ontology-docs/`와 감사 기록은 삭제하지 않습니다.

## 기존 API 워크숍

`src/ontology_workshop`과 `static/`의 기존 서버도 유지됩니다. `requirements.txt` 설치 후 다음 명령으로 실행합니다.

```bash
PYTHONPATH=src uvicorn ontology_workshop.server:app --host 127.0.0.1 --port 8000
```

기존 `$run-workshop` 플러그인은 이 API 서버의 별도 상태를 사용합니다. 파일 기반 워크숍의 `ontology-docs/`와 자동으로 같은 세션을 공유하지 않습니다.
