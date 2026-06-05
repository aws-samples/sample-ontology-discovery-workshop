# 시작하기 — 복붙 한 번이면 끝

> **개발자가 아니어도 됩니다.** 아래 텍스트를 본인이 쓰는 AI 코딩 에이전트
> (Claude Code · Kiro · Amazon Q Developer · Cursor 등)에 **그대로 붙여넣기** 하세요.
> 설치·서버 실행·워크샵 진행을 에이전트가 알아서 합니다.

## 사전 준비 (딱 한 번)
- 사용하는 AI 에이전트가 **터미널 명령 실행**과 **파일 읽기**를 할 수 있어야 합니다
  (Claude Code, Kiro, Amazon Q CLI는 기본 지원).
- 컴퓨터에 **Python 3.11+** 와 **git** 이 설치돼 있어야 합니다.

---

## 1) 어느 에이전트든 — 이 한 덩어리를 붙여넣기

```
아래 저장소를 clone 하고 셋업한 뒤, OntoForge 온톨로지 워크샵을 시작해줘.

저장소: https://github.com/jinuland/ontology-workshop

순서:
1. git clone https://github.com/jinuland/ontology-workshop.git 하고 그 폴더로 이동
2. 루트의 AGENTS.md 를 읽고, 거기 적힌 셋업 명령을 실행해 OntoForge 서버를 띄워줘
3. 서버가 뜨면 나에게 "브라우저에서 http://localhost:8000 열어주세요" 라고 알려줘
4. .claude/skills/ontoforge-workshop/SKILL.md 를 읽고, 그 지침대로
   워크샵 운영자(두뇌) 역할로 나를 인터뷰하며 온톨로지를 실시간으로 만들어줘
```

이게 가장 간단합니다. 에이전트가 clone → 설치 → 서버 실행 → 워크샵 진행까지 다 합니다.

---

## 2) 도구별 참고 (위 1번이면 충분하지만, 더 매끄럽게 쓰려면)

이미 clone 한 폴더를 도구로 열면, 각 도구가 자동으로 지침을 인식합니다:

| 도구 | 자동 인식 파일 | 비고 |
|---|---|---|
| **Claude Code** | `.claude/skills/ontoforge-workshop/SKILL.md` | "온톨로지 워크샵 시작"이라고 말하면 스킬 발동 |
| **Kiro** | `.kiro/steering/ontoforge-workshop.md` | 폴더 열면 steering으로 자동 주입 |
| **Amazon Q** | `.amazonq/rules/ontoforge-workshop.md` | 프로젝트 룰로 자동 포함 |
| **Cursor / Windsurf / 기타** | 루트 `AGENTS.md` | 범용 표준 — "AGENTS.md 읽고 워크샵 시작"이라고 요청 |

그래도 동작이 어색하면 **위 1번 복붙**을 그대로 다시 주세요. 가장 확실합니다.

---

## 3) 워크샵이 시작되면
- 브라우저(`http://localhost:8000`)에 **실시간 그래프**가 그려집니다.
- 에이전트(채팅창)에서 고객/도메인 답변을 말하면, 에이전트가 엔티티·관계로 구조화해 그래프에 반영합니다.
- 끝나면 에이전트에게 **"산출물 만들어줘"** 라고 하면 보고서(html/docx) · Neptune 익스포트 ·
  복원용 스냅샷이 `exports/` 에 생성됩니다.

문제가 생기면 에이전트에게 "서버 로그(`/tmp/ontoforge.log`) 보고 고쳐줘"라고 하세요.
