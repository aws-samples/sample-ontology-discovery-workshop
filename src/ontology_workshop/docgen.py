# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""온톨로지 → Markdown(Obsidian 호환) 문서 생성."""
from __future__ import annotations
from .graph import OntologyGraph


def render_markdown(g: OntologyGraph, title: str = "온톨로지") -> str:
    tb = g.tbox()
    lines: list[str] = [f"# {title}", "", "## 엔티티 (T-Box)", ""]

    for name, et in tb["entities"].items():
        lines.append(f"### {name}")
        lines.append(f"- 기본키: `{et['primary_key']}`")
        if et["properties"]:
            lines.append("- 속성:")
            for k, v in et["properties"].items():
                lines.append(f"  - `{k}`: {v}")
        lines.append("")

    lines += ["## 관계 (T-Box)", ""]
    for name, rt in tb["relations"].items():
        card = rt.get("cardinality", "N:M")
        lines.append(f"- **{rt['src']}** —`{name}`({card})→ **{rt['dst']}**")
        if rt["properties"]:
            for k, v in rt["properties"].items():
                lines.append(f"  - `{k}`: {v}")
    lines.append("")

    snap = g.snapshot()
    lines += ["## 인스턴스 데이터 (A-Box)", "",
              f"- 노드 {len(snap['nodes'])}개, 엣지 {len(snap['edges'])}개", ""]
    return "\n".join(lines)


def render_query_evidence(question: str, cypher: str, result: dict) -> str:
    """검증된 질의 1건을 설득용 증거 블록으로."""
    out = [f"### Q: {question}", "", "```cypher", cypher.strip(), "```", ""]
    if result.get("ok"):
        out.append(f"**결과 ({result['count']}건):** `{result['columns']}`")
        for row in result["rows"][:10]:
            out.append(f"- {row}")
    else:
        out.append(f"> 오류: {result.get('error')}")
    out.append("")
    return "\n".join(out)
