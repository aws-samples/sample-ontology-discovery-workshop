#!/usr/bin/env python3
"""
그래프 평가 스킬 — 정적 모델 품질 평가기.

입력: workshop-model.json (metadata + tbox + snapshot + queries)
동작: 실제 데이터·DB 실행 없이 스키마(T-Box) + 인스턴스(A-Box)만 분석.
출력: 단일 HTML 리포트 (오프라인·외부 의존성 없음).

두 엔진:
  엔진 A (구조/품질)  : _quality.analyze 복제 로직 재사용.
  엔진 B (시나리오 추측): T-Box 관계 경로 + 노드/타입 이름으로 "해결 가능 시나리오"
                          후보를 추론. 전부 CANDIDATE 표기, 근거 경로 첨부.

런타임 성능 지표(E_t, ΔT 등)는 이 스킬 범위 밖이다.
→ docs/future-runtime-graph-performance-skill.md 참고.

사용법:
    python evaluate.py <input.json> [--out report.html]
"""
from __future__ import annotations

import argparse
import datetime
import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _quality  # noqa: E402


MAX_HOPS = 3
MAX_SCENARIOS = 15


# ---------------------------------------------------------------------------
# 입력
# ---------------------------------------------------------------------------
def load_document(path: Path) -> dict:
    with path.open(encoding="utf-8") as stream:
        document = json.load(stream)
    if not isinstance(document, dict):
        raise ValueError("입력 JSON의 최상위는 객체여야 합니다.")
    return document


# ---------------------------------------------------------------------------
# 엔진 B — 시나리오 추측
# ---------------------------------------------------------------------------
def _entity_label(schema: dict, type_name: str) -> str:
    definition = schema["entities"].get(type_name, {})
    return definition.get("label") or type_name


def _relation_label(schema: dict, relation_name: str) -> str:
    definition = schema["relations"].get(relation_name, {})
    return definition.get("label") or relation_name


def _enumerate_paths(schema: dict):
    """T-Box 관계를 유향 그래프로 보고, 엔티티 타입을 반복하지 않는
    단순 경로(1~MAX_HOPS 홉)를 열거한다. 각 경로 = 관계 이름 리스트."""
    adjacency = defaultdict(list)
    for name, definition in schema["relations"].items():
        adjacency[definition["src"]].append((name, definition["dst"]))

    paths = []
    seen = set()

    def walk(current_type, visited_types, relation_chain):
        if relation_chain:
            key = tuple(relation_chain)
            if key not in seen:
                seen.add(key)
                paths.append(list(relation_chain))
        if len(relation_chain) >= MAX_HOPS:
            return
        for relation_name, destination in adjacency.get(current_type, []):
            if destination in visited_types:
                continue  # 사이클 방지(읽기 쉬운 경로 유지)
            walk(destination, visited_types | {destination}, relation_chain + [relation_name])

    for entity_type in schema["entities"]:
        walk(entity_type, {entity_type}, [])
    return paths


def _query_coverage(relation_chain, queries):
    """경로의 관계 이름들이 역량질문(queries) cypher에 등장하는지 대조."""
    best_matched = 0
    best_title = None
    for query in queries:
        cypher = query.get("cypher", "")
        matched = sum(1 for relation_name in relation_chain if relation_name in cypher)
        if matched > best_matched:
            best_matched = matched
            best_title = query.get("title") or query.get("cypher", "")[:40]
    if best_matched == len(relation_chain):
        return "일치", best_title
    if best_matched > 0:
        return "부분 일치", best_title
    return "없음", None


def infer_scenarios(state: dict):
    schema = state["schema"]
    if not schema["relations"]:
        return []
    paths = _enumerate_paths(schema)
    scenarios = []
    for relation_chain in paths:
        entity_path = [schema["relations"][relation_chain[0]]["src"]]
        for relation_name in relation_chain:
            entity_path.append(schema["relations"][relation_name]["dst"])

        start_label = _entity_label(schema, entity_path[0])
        end_label = _entity_label(schema, entity_path[-1])
        if len(relation_chain) == 1:
            title = f"{start_label}별 {end_label} 조회"
        else:
            title = f"{start_label}에서 {end_label}까지 추적 및 집계"

        technical_path = _format_path(schema, entity_path, relation_chain)
        coverage, matched_title = _query_coverage(relation_chain, state["queries"])

        scenarios.append({
            "title": title,
            "path": technical_path,
            "hops": len(relation_chain),
            "coverage": coverage,
            "coverage_query": matched_title,
            "status": "CANDIDATE",
        })

    scenarios.sort(key=lambda item: (item["hops"], item["title"]))
    return scenarios[:MAX_SCENARIOS]


def _format_path(schema, entity_path, relation_chain) -> str:
    parts = [entity_path[0]]
    for index, relation_name in enumerate(relation_chain):
        parts.append(f"-[{relation_name}]->")
        parts.append(entity_path[index + 1])
    return " ".join(parts)


# ---------------------------------------------------------------------------
# HTML 렌더링 (단일 파일, 인라인 CSS 최소, 외부 의존성 없음)
# ---------------------------------------------------------------------------
_CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { font-family: -apple-system, Segoe UI, Roboto, 'Noto Sans KR', sans-serif;
       margin: 0; padding: 24px; color: #1a1a1a; background: #f0eee6; line-height: 1.5; }
h1 { font-size: 20px; margin: 0 0 4px; }
h2 { font-size: 15px; margin: 28px 0 8px; border-bottom: 1px solid #ddd; padding-bottom: 4px; }
.sub { color: #666; font-size: 12px; margin: 0 0 16px; }
.badges { margin: 8px 0 4px; }
.badge { display: inline-block; border: 1px solid #ccc; border-radius: 3px;
         padding: 2px 8px; margin-right: 6px; font-size: 12px; }
.badge b { font-variant-numeric: tabular-nums; }
.b-error { border-color: #c0392b; color: #c0392b; }
.b-warn  { border-color: #b9770e; color: #b9770e; }
.b-info  { border-color: #2471a3; color: #2471a3; }
table { border-collapse: collapse; width: 100%; margin: 4px 0 8px; font-size: 13px; }
th, td { border: 1px solid #ddd; padding: 6px 8px; text-align: left; vertical-align: top; }
th { background: #f3f3f3; font-weight: 600; }
code, .mono { font-family: SFMono-Regular, Consolas, monospace; font-size: 12px; }
.sev { font-weight: 600; font-size: 11px; letter-spacing: .3px; }
.sev-error { color: #c0392b; }
.sev-warning { color: #b9770e; }
.sev-info { color: #2471a3; }
.ok { color: #1e7e34; }
.no { color: #b9770e; }
.tag { display: inline-block; border: 1px solid #999; border-radius: 3px;
       padding: 0 6px; font-size: 11px; color: #555; }
.note { background: #f8f8f8; border-left: 3px solid #bbb; padding: 8px 12px;
        font-size: 12px; color: #444; margin: 8px 0; }
.empty { color: #777; font-style: italic; font-size: 13px; }
"""

_SEV_LABEL = {"error": "ERROR", "warning": "WARNING", "info": "INFO"}


def _esc(value) -> str:
    text = str(value).replace("·", " ").replace("—", " ")
    text = re.sub(r" {2,}", " ", text).strip()
    return html.escape(text, quote=True)


def _findings_table(findings) -> str:
    if not findings:
        return '<p class="empty">발견된 구조 문제가 없습니다.</p>'
    rows = []
    for finding in findings:
        severity = finding["severity"]
        rows.append(
            "<tr>"
            f'<td class="sev sev-{severity}">{_SEV_LABEL.get(severity, severity.upper())}</td>'
            f'<td><code>{_esc(finding["code"])}</code></td>'
            f'<td class="mono">{_esc(", ".join(finding["element_ids"]))}</td>'
            f'<td>{_esc(finding["title"])}</td>'
            f'<td>{_esc(finding["detail"])}</td>'
            f'<td>{_esc(finding["recommendation"])}</td>'
            "</tr>"
        )
    return (
        "<table><thead><tr>"
        "<th>심각도</th><th>코드</th><th>대상 ID</th><th>제목</th><th>상세</th><th>권고</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def _scenarios_table(scenarios) -> str:
    if not scenarios:
        return '<p class="empty">관계 타입이 없어 시나리오를 추론할 수 없습니다.</p>'
    rows = []
    for scenario in scenarios:
        coverage = scenario["coverage"]
        if scenario["coverage_query"]:
            coverage = f'{coverage} <span class="mono">({_esc(scenario["coverage_query"])})</span>'
        else:
            coverage = _esc(coverage)
        rows.append(
            "<tr>"
            f'<td>{_esc(scenario["title"])}</td>'
            f'<td class="mono">{_esc(scenario["path"])}</td>'
            f'<td>{scenario["hops"]}</td>'
            f"<td>{coverage}</td>"
            f'<td><span class="tag">{_esc(scenario["status"])}</span></td>'
            "</tr>"
        )
    return (
        "<table><thead><tr>"
        "<th>시나리오(추측)</th><th>근거 경로(T-Box)</th><th>홉</th>"
        "<th>역량질문 대조</th><th>상태</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def render_html(state, quality_result, scenarios) -> str:
    counts = quality_result["counts"]
    model_counts = state["counts"]
    title = state["metadata"].get("title", "그래프 평가")
    generated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    header = (
        f"<h1>그래프 평가 리포트: {_esc(title)}</h1>"
        f'<p class="sub">생성 {generated} / depth {_esc(quality_result["depth"])} / revision {_esc(state["revision"])}</p>'
        '<div class="badges">'
        f'<span class="badge b-error">ERROR <b>{counts["error"]}</b></span>'
        f'<span class="badge b-warn">WARNING <b>{counts["warning"]}</b></span>'
        f'<span class="badge b-info">INFO <b>{counts["info"]}</b></span>'
        "</div>"
        '<div class="badges">'
        f'<span class="badge">엔티티 타입 <b>{model_counts["entity_types"]}</b></span>'
        f'<span class="badge">관계 타입 <b>{model_counts["relation_types"]}</b></span>'
        f'<span class="badge">노드 <b>{model_counts["nodes"]}</b></span>'
        f'<span class="badge">엣지 <b>{model_counts["edges"]}</b></span>'
        "</div>"
    )

    section_a = (
        "<h2>1. 구조 및 품질 점검 (엔진 A)</h2>"
        f'<p class="note">{_esc(quality_result["scope"])}</p>'
        + _findings_table(quality_result["findings"])
    )

    section_b = (
        "<h2>2. 해결 가능 시나리오 후보 (엔진 B)</h2>"
        '<p class="note">아래는 T-Box 관계 경로와 노드/타입 이름을 근거로 한 '
        "<b>추측(CANDIDATE)</b>입니다. 확정이 아니며 도메인 전문가 검증이 필요합니다.</p>"
        + _scenarios_table(scenarios)
    )

    section_c = (
        "<h2>3. 사람이 확인할 것</h2>"
        "<ul>"
        "<li>엔진 A의 ERROR 항목은 모델/인스턴스 정정이 필요합니다. WARNING/INFO는 검토 후 사유 기록으로 종료할 수 있습니다.</li>"
        "<li>엔진 B 시나리오는 이름 기반 추측입니다. 실제 업무 요구와 맞는지, 누락된 경로는 없는지 전문가가 판단해야 합니다.</li>"
        "<li>실행 성능 지표(E_t, 차수 민감도 등)는 이 정적 평가 범위 밖입니다. "
        "데이터 적재 후 별도 런타임 스킬에서 측정하세요 "
        "(docs/future-runtime-graph-performance-skill.md).</li>"
        "</ul>"
    )

    return (
        "<!DOCTYPE html><html lang='ko'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>그래프 평가: {_esc(title)}</title>"
        f"<style>{_CSS}</style></head><body>"
        + header + section_a + section_b + section_c
        + "</body></html>"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="정적 그래프 모델 품질 평가 → HTML 리포트")
    parser.add_argument("input", help="workshop-model.json 경로")
    parser.add_argument("--out", help="출력 HTML 경로(기본: <input>.report.html)")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser()
    if not input_path.is_file():
        print(json.dumps({"error": f"입력 파일을 찾을 수 없습니다: {input_path}"}, ensure_ascii=False), file=sys.stderr)
        return 1

    try:
        document = load_document(input_path)
        state = _quality.normalize(document)
        # Standalone evaluation always runs all depth-dependent checks.
        # normalize() copies metadata, so the input document stays unchanged.
        state["metadata"]["depth"] = "comprehensive"
        quality_result = _quality.analyze(state)
        scenarios = infer_scenarios(state)
        report_html = render_html(state, quality_result, scenarios)
    except (ValueError, KeyError, json.JSONDecodeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1

    out_path = Path(args.out).expanduser() if args.out else input_path.with_suffix(".report.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report_html, encoding="utf-8")

    summary = {
        "report": str(out_path.resolve()),
        "depth": quality_result["depth"],
        "counts": quality_result["counts"],
        "open_count": quality_result["open_count"],
        "scenarios": len(scenarios),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
