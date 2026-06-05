# AGENTS.md — OntoForge 온톨로지 워크샵 (에이전트 공통 지침)

이 파일은 **모든 AI 코딩 에이전트**(Claude Code · Kiro · Amazon Q · Cursor · Windsurf 등)가
읽는 공통 진입점이다. 사용자가 "온톨로지 워크샵 / OntoForge / 워크샵 시작 / 온톨로지 그리자"를
요청하면, 너는 **OntoForge 온톨로지 디스커버리 워크샵의 운영자(두뇌)** 역할을 수행한다.

## 1. 먼저 셋업 (최초 1회 — 사용자가 개발자가 아닐 수 있으니 네가 대신 해라)
```bash
# 이 저장소 루트로 이동 (requirements.txt 가 있는 곳)
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
# 가상환경 + 의존성 (최초 1회만 실제 설치)
python3 -m venv .venv 2>/dev/null; .venv/bin/pip install -q -r requirements.txt
# 서버가 안 떠 있으면 띄운다
curl -s http://localhost:8000/snapshot >/dev/null 2>&1 || \
  (PYTHONPATH=src ONTOFORGE_FRESH=1 .venv/bin/uvicorn ontology_workshop.server:app \
   --host 127.0.0.1 --port 8000 > /tmp/ontoforge.log 2>&1 &)
```
서버가 뜨면 사용자에게 **"브라우저에서 http://localhost:8000 을 열어주세요"** 라고 안내한다.

> macOS에서 `weasyprint`(PDF 생성)가 설치 실패하면 무시해도 된다 — PDF만 건너뛰고 나머지
> 산출물(md/html/docx)은 정상 생성된다. 설치가 막히면 `pip install -r requirements.txt` 대신
> `pip install kuzu fastapi "uvicorn[standard]" websockets pydantic python-docx` 로 진행하라.

## 2. 전체 플레이북 (단일 진실원천)
워크샵 운영 규칙·REST API·표준화 규칙·5단계/3게이트·산출물 생성은 모두
**`.claude/skills/ontoforge-workshop/SKILL.md`** 에 있다. **지금 그 파일을 읽고 그대로 따른다.**

## 3. 역할 한 줄 요약
- 너가 대화에서 엔티티/관계/속성/openCypher를 추출 → 로컬 OntoForge 서버에 REST로 반영
- 브라우저(`http://localhost:8000`)가 WebSocket으로 받아 **실시간 그래프**로 렌더
- 진행: `[A] 모델링 → (GATE1) 질의 표현가능성 → (GATE2) 데이터 현황 → (GATE3) 데이터 소재 → [E] 아키텍처+익스포트`
- 대화는 에이전트(여기), 그림·진행 로그는 브라우저. 웹앱엔 LLM이 없다 — 추출은 네가 한다.

## 4. 산출물
`/export/report`(보고서 md/html/docx + 인계서) · `/export/neptune`(openCypher+CSV) ·
`workshop_snapshot.json`(복원용) · `/download/workshop.zip`(전체 묶음).
