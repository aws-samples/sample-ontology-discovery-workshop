# OntoForge

[English](./README.md) | [한국어](./README.ko.md) | [日本語](./README.ja.md)

OntoForge는 업무 대화와 기존 자료를 바탕으로 그래프 모델을 만드는 로컬 워크숍 도구입니다. 참가자는 자신의 AI 도구와 대화하고, 브라우저에서 모델을 검토합니다.

## 진행 방식

AI는 업무 시나리오를 묻고 답변에서 엔티티와 관계를 정리합니다. 기존 스키마와 예시 데이터를 참고하고, 참가자가 확인한 내용에 따라 모델을 수정합니다.

브라우저에서는 그래프와 워크숍 기록을 확인합니다. 노드 속성을 보고 관계를 따라가며, 업무 질문에 답할 수 있는 모델인지 Cypher 조회로 확인합니다.

## 확인할 내용

- T-box: 엔티티 타입, 관계 타입, 속성, 식별자 정의
- A-box: 각 타입의 인스턴스와 실제 연결
- Cypher: 업무 질문을 표현한 쿼리와 실행 결과
- 워크숍 기록: 결정 사항, 자료 출처, 남은 질문, 모델 변경 내용

Cypher는 속성 그래프를 조회하고 생성하는 언어입니다. 그래프 모델은 타입, 속성, 관계의 정의이며 워크숍은 이 정의와 인스턴스 데이터를 나눠 관리합니다.

## 결과물

워크숍이 끝나면 그래프 모델, 모델을 정한 근거, 검토에 사용한 쿼리가 남습니다. 웹에서 모델 JSON, PNG, SVG를 저장할 수 있습니다. Cypher는 스키마, 인스턴스 데이터, 전체 모델로 나눠 내보냅니다.

## 시작하기

로컬 웹을 설치하고 환경을 확인합니다.

```bash
python3 -m venv viz-server/.venv
viz-server/.venv/bin/python -m pip install -r viz-server/requirements.txt
bash scripts/test-viz.sh
bash scripts/serve.sh
```

출력된 주소를 브라우저에서 엽니다. 기본 주소는 `http://127.0.0.1:5173`입니다. 로컬 AI에서 `/onto-discover` 또는 `온톨로지 발견 시작`으로 진행합니다. 모델과 답변은 `ontology-docs/`에 저장하고 웹은 게시된 모델을 보여줍니다.

예제 실행과 워크숍 당일 명령은 [로컬 워크숍 실행](./docs/LOCAL_WORKSHOP.md)에 정리했습니다.

기존 API 워크숍과 `$run-workshop` 플러그인도 유지합니다. 해당 서버의 상태는 파일 기반 워크숍과 별도이며 실행 방법은 같은 안내 문서에서 확인할 수 있습니다.

## 모델 평가

워크숍이 끝나면 최종 모델을 평가합니다. 평가는 `workshop-model.json`의 스키마(T-box)를 읽으며, DB에 접속하거나 모델을 수정하지 않습니다. 결과는 모델과 같은 폴더의 `graph-evaluation-report.html`에 저장되고, 보고서는 한국어로 작성합니다.

로컬 AI에서 `/ontoforge-evaluation` 또는 `최종 그래프 평가`를 요청합니다. Claude Code에서는 모델 경로를 함께 줄 수 있습니다. 예: `/ontoforge-evaluation path/to/workshop-model.json`. 워크숍 밖에서 그래프 스키마 평가나 비교를 요청해도 같은 스킬이 동작합니다. 내보내기와 산출물 확인이 끝난 뒤 마지막에 실행하고, 모델이 바뀌면 다시 실행합니다.

보고서에 담기는 내용입니다.

- 구조 점검: 관계 제약, 겹치거나 한 이름이 여러 의미로 쓰이는 관계, 같은 사실의 중복 표현, 이름과 열거형의 불일치
- 정량 지표: 속성 풍부도, 타입 계층이 있을 때의 관계 풍부도와 상속 풍부도, 도메인 정보가 없는 관계의 비율 같은 측정값
- 의미 검토: 라벨의 의미, 상태와 식별자를 노드로 둘지 속성으로 둘지, 비어 있는 중간 분류
- 질문 연계: 틀린 골든 질문을 원인별로 나누는 방법, 질문 후보를 스키마가 표현할 수 있는지 정적 확인
- 개선 권고, 그래프 DB 고려사항, 데이터나 고객 확인이 필요한 남은 항목

참고 자료는 원문을 직접 연 논문만 싣고, 확인하지 못한 항목은 미확인으로 표시합니다. 등급과 심각도는 평가자의 판단입니다.

구성은 다음과 같습니다.

- 절차, 보고서 구성, 스타일은 `.claude/skills/graph-evaluation/SKILL.md`에 있습니다. 명령 파일 `.claude/commands/ontoforge-evaluation.md`와 Kiro 스티어링 `.kiro/steering/ontoforge-evaluation.md`는 이 파일을 가리키는 입구입니다.
- `schema_metrics.py`는 스키마 지표를 계산합니다. 라벨 이름은 모델마다 다르므로 모델의 범용 라벨과 허브를 정해 `--generic`, `--hubs`로 넘깁니다.
- `evaluate.py`는 선택 사항인 정적 점검입니다. 별도 파일 `graph-evaluation-static-check.html`을 만들며 보고서를 대신하지 않습니다.

```bash
python3 .claude/skills/graph-evaluation/schema_metrics.py path/to/workshop-model.json \
  --generic <범용 라벨> --hubs <허브 라벨>
```

## 관련 문서

- [로컬 워크숍 실행](./docs/LOCAL_WORKSHOP.md)
- [온톨로지 발견 워크숍](./docs/ONTOLOGY_DISCOVERY.md)
- [모델 형식과 Cypher 내보내기](./viz-server/README.md)
- [워크숍 진행 단계](./docs/AI_ODLC_WORKFLOW.md)
- [애플리케이션 구조](./docs/DESIGN.md)
- [워크숍 스킬](./skills/WORKSHOP_SKILLS.md)
- [그래프 평가 스킬](./.claude/skills/graph-evaluation/SKILL.md)
- [보안](./SECURITY.md)
- [기여 방법](./CONTRIBUTING.md)
