# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""M2 — 워크샵 산출물 생성기 (비개발자 친화).

구성:
  0) 온톨로지란? (T-Box / A-Box 쉬운 설명)
  1) 온톨로지 한눈에 보기 (Mermaid 스키마 다이어그램)
  2) 엔티티 — 무엇을 위한 것인가 (왜 표)
  3) 관계 — 무엇을 위한 것인가 (왜 표)
  4) 실제 데이터 예시 (Mermaid 인스턴스 샘플)
  5) 검증된 질의
  6) AWS 구축 아키텍처 제안
  7) 데이터 준비 상태
  8) 기술 미팅 인계서

`descriptions`(선택)로 각 엔티티/관계의 한글 라벨과 "왜 필요한가"를 주입한다.
Claude(브레인)가 도메인 맥락을 채워 넘기면 비개발자용 설명이 풍부해진다.
주입이 없으면 구조는 그대로 렌더되고 설명 칸엔 보충 안내가 들어간다.
Markdown / HTML 두 포맷으로 렌더. PDF·docx는 report_export.py에서 변환.
"""
from __future__ import annotations

import datetime as _dt
import html as _html
import re as _re

from .graph import OntologyGraph
from . import skills as sk
from . import i18n


def _now() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------------------
# descriptions 정규화
#   descriptions = {
#     "domain": "이 그래프가 푸는 큰 문제 1~2문장",
#     "entities": {"Concept": {"label":"개념", "why":"..."} 또는 "왜 문자열"},
#     "relations": {"PRECEDES": {"label":"선행", "why":"..."}},
#   }
# ---------------------------------------------------------------------------
def _norm(entry) -> dict:
    if entry is None:
        return {}
    if isinstance(entry, str):
        return {"why": entry}
    if isinstance(entry, dict):
        return {"label": entry.get("label"), "why": entry.get("why")}
    return {}


def _label(name: str, d: dict) -> str:
    """한글 라벨이 있으면 '한글(Name)', 없으면 Name."""
    lab = d.get("label")
    return f"{lab}({name})" if lab else name


def _mermaid_id(s: str) -> str:
    """Mermaid 노드 ID로 안전한 문자열."""
    return _re.sub(r"[^0-9A-Za-z_]", "_", str(s)) or "n"


# ---------------------------------------------------------------------------
# 0) 온톨로지란? — 비개발자용 개념 설명
# ---------------------------------------------------------------------------
def ontology_intro_section(g: OntologyGraph, descriptions: dict | None = None,
                           lang: str | None = None) -> str:
    S = i18n.strings(lang)
    descriptions = descriptions or {}
    domain = descriptions.get("domain")
    th = S["s0_th"]
    tb, ab = S["s0_tbox"], S["s0_abox"]
    lines = [
        S["s0_h"], "",
        S["s0_p1"], "",
        S["s0_p2"], "",
        f"| {th[0]} | {th[1]} | {th[2]} |",
        "| --- | --- | --- |",
        f"| {tb[0]} | {tb[1]} | {tb[2]} |",
        f"| {ab[0]} | {ab[1]} | {ab[2]} |",
        "",
        S["s0_quote"],
    ]
    if domain:
        lines += ["", S["s0_domain_h"], "", domain]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 1) T-Box Mermaid 스키마 다이어그램
# ---------------------------------------------------------------------------
def tbox_diagram_section(g: OntologyGraph, descriptions: dict | None = None,
                         lang: str | None = None) -> str:
    S = i18n.strings(lang)
    descriptions = descriptions or {}
    edesc = descriptions.get("entities", {})
    rdesc = descriptions.get("relations", {})
    tb = g.tbox()
    ents, rels = tb["entities"], tb["relations"]

    lines = [S["s1_h"], "", S["s1_desc"], "",
             "```mermaid", "graph LR"]
    # 노드
    for name in ents:
        d = _norm(edesc.get(name))
        lines.append(f'  {_mermaid_id(name)}["{_label(name, d)}"]')
    # 엣지
    for rname, rt in rels.items():
        s, dst = _mermaid_id(rt["src"]), _mermaid_id(rt["dst"])
        rd = _norm(rdesc.get(rname))
        elabel = str(rd.get("label") or rname).replace('"', "'")
        lines.append(f'  {s} -->|"{elabel}"| {dst}')
    lines.append("```")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 2) 엔티티 — 무엇을 위한 것인가
# ---------------------------------------------------------------------------
def entities_section(g: OntologyGraph, descriptions: dict | None = None,
                     lang: str | None = None) -> str:
    S = i18n.strings(lang)
    descriptions = descriptions or {}
    edesc = descriptions.get("entities", {})
    ents = g.tbox()["entities"]
    th = S["s2_th"]
    lines = [S["s2_h"], "", S["s2_desc"], "",
             f"| {th[0]} | {th[1]} | {th[2]} | {th[3]} |",
             "| --- | --- | --- | --- |"]
    for name, et in ents.items():
        d = _norm(edesc.get(name))
        props = ", ".join(et["properties"].keys()) or "—"
        why = d.get("why") or S["why_missing"]
        lines.append(f"| **{_label(name, d)}** | {props} | "
                     f"`{et['primary_key']}` | {why} |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 3) 관계 — 무엇을 위한 것인가
# ---------------------------------------------------------------------------
def relations_section(g: OntologyGraph, descriptions: dict | None = None,
                      lang: str | None = None) -> str:
    S = i18n.strings(lang)
    descriptions = descriptions or {}
    rdesc = descriptions.get("relations", {})
    rels = g.tbox()["relations"]
    th = S["s3_th"]
    lines = [S["s3_h"], "", S["s3_desc"], "",
             f"| {th[0]} | {th[1]} | {th[2]} | {th[3]} |",
             "| --- | --- | --- | --- |"]
    for rname, rt in rels.items():
        d = _norm(rdesc.get(rname))
        conn = f"{rt['src']} → {rt['dst']} ({rt.get('cardinality', 'N:M')})"
        rprops = ", ".join(rt["properties"].keys()) or "—"
        why = d.get("why") or S["why_missing"]
        lab = d.get("label")
        rn = f"**{rname}**" + (f"<br/>({lab})" if lab else "")
        lines.append(f"| {rn} | {conn} | {rprops} | {why} |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 4) A-Box 실데이터 샘플 다이어그램
# ---------------------------------------------------------------------------
def abox_diagram_section(g: OntologyGraph, descriptions: dict | None = None,
                         per_rel: int = 2, lang: str | None = None) -> str:
    S = i18n.strings(lang)
    descriptions = descriptions or {}
    edesc = descriptions.get("entities", {})
    snap = g.snapshot()
    nodes = {n["data"]["id"]: n["data"] for n in snap["nodes"]}
    edges = snap["edges"]

    # 모든 관계 종류가 한 번씩은 보이도록 관계 타입별로 per_rel개 샘플
    seen_rel: dict[str, int] = {}
    sample, used_nodes = [], set()
    for e in edges:
        rt = e["data"]["label"]
        if seen_rel.get(rt, 0) >= per_rel:
            continue
        seen_rel[rt] = seen_rel.get(rt, 0) + 1
        sample.append(e["data"])
        used_nodes.add(e["data"]["source"])
        used_nodes.add(e["data"]["target"])

    # 노드 id는 한글을 포함하므로 충돌 없는 alias(n0,n1,…)를 부여한다.
    alias = {nid: f"n{i}" for i, nid in enumerate(sorted(used_nodes))}

    lines = [S["s4_h"], "",
             S["s4_desc"].format(nodes=len(nodes), edges=len(edges)), "",
             "```mermaid", "graph LR"]
    for nid in sorted(used_nodes):
        nd = nodes.get(nid, {})
        etype = nd.get("etype", "")
        ed = _norm(edesc.get(etype))
        lab = str(nd.get("label", nid)).replace('"', "'")
        prefix = ed.get("label") or etype
        lines.append(f'  {alias[nid]}["{prefix}: {lab}"]')
    for e in sample:
        s, dst = alias.get(e["source"]), alias.get(e["target"])
        # 관계 속성(점수 등) 있으면 라벨에 노출
        props = e.get("props") or {}
        extra = ""
        if props:
            kv = list(props.items())[0]
            extra = f" {kv[0]}={kv[1]}"
        elabel = f'{e["label"]}{extra}'.replace('"', "'")
        lines.append(f'  {s} -->|"{elabel}"| {dst}')
    lines.append("```")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 5) 검증된 질의
# ---------------------------------------------------------------------------
def verified_section(verified_queries: list[dict] | None = None,
                     lang: str | None = None) -> str:
    S = i18n.strings(lang)
    lines = [S["s5_h"], "", S["s5_desc"], ""]
    if verified_queries:
        for vq in verified_queries:
            lines.append(S["s5_q"].format(q=vq["question"], n=vq.get("count", 0)))
            lines.append(f"  - `{vq['cypher']}`")
    else:
        lines.append(S["s5_none"])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 6) AWS 구축 아키텍처 제안
# ---------------------------------------------------------------------------
def aws_architecture_section(g: OntologyGraph, lang: str | None = None) -> str:
    S = i18n.strings(lang)
    tb = g.tbox()
    n_ent = len(tb["entities"])
    n_rel = len(tb["relations"])
    neptune = S["neptune_small"] if n_ent <= 8 else S["neptune_large"]
    return S["s6"].format(neptune=neptune, n_ent=n_ent, n_rel=n_rel)


# ---------------------------------------------------------------------------
# 7) 마이그레이션 플랜 & 다음 스텝
# ---------------------------------------------------------------------------
def migration_plan_section(g: OntologyGraph, lang: str | None = None) -> str:
    S = i18n.strings(lang)
    ents = list(g.entity_types.keys())
    res = sk._mock_sources("", {"entities": ents})
    n_have = len(res["available"])
    n_need = len(res["to_be_sourced"])
    return S["s7"].format(n_have=n_have, n_need=n_need)


# ---------------------------------------------------------------------------
# 8) 데이터 준비 상태
# ---------------------------------------------------------------------------
_STATUS_ORDER = ["보유", "부분보유", "미보유", "파생", "모름"]
_STATUS_ALIASES = {
    "보유": "보유",
    "available": "보유",
    "avail": "보유",
    "have": "보유",
    "yes": "보유",
    "保有": "보유",
    "부분보유": "부분보유",
    "partial": "부분보유",
    "partially_available": "부분보유",
    "partially available": "부분보유",
    "一部保有": "부분보유",
    "미보유": "미보유",
    "missing": "미보유",
    "not_available": "미보유",
    "not available": "미보유",
    "none": "미보유",
    "未保有": "미보유",
    "파생": "파생",
    "derived": "파생",
    "computed": "파생",
    "calculated": "파생",
    "派生": "파생",
    "모름": "모름",
    "unknown": "모름",
    "unsure": "모름",
    "unclear": "모름",
    "不明": "모름",
}


def _canonical_status(status: object) -> str:
    raw = str(status or "unknown").strip()
    key = raw.lower()
    return (_STATUS_ALIASES.get(raw) or _STATUS_ALIASES.get(key) or
            _STATUS_ALIASES.get(key.replace("-", "_")) or "모름")


def _normalized_data_status(data_status: dict) -> dict:
    out = {}
    for name, d in data_status.items():
        row = dict(d or {})
        row["status"] = _canonical_status(row.get("status"))
        out[name] = row
    return out


def _action_items_block(data_status: dict, action_items: dict | None,
                        lang: str | None = None) -> list[str]:
    """GATE 2 분류에서 고객/우리 액션을 자동 도출 + 명시 항목 병합.
    모름·미보유·부분보유는 워크샵 후 고객이 이메일로 회신할 항목이 된다."""
    S = i18n.strings(lang)
    cust, ours = [], []
    for name, d in data_status.items():
        st = _canonical_status((d or {}).get("status"))
        if st == "모름":
            cust.append(S["ai_unknown"].format(name=name))
        elif st == "미보유":
            cust.append(S["ai_missing"].format(name=name))
        elif st == "부분보유":
            cust.append(S["ai_partial"].format(name=name))
    ours += list(S["ai_us_default"])
    if action_items:
        cust += list(action_items.get("customer", []))
        ours += list(action_items.get("us", []))

    out = ["", S["ai_h"], ""]
    has_unknown = any(_canonical_status((d or {}).get("status"))
                      in ("모름", "미보유", "부분보유")
                      for d in data_status.values())
    if has_unknown:
        out.append(S["ai_quote"])
        out.append("")
    out.append(S["ai_customer_h"])
    out += [f"- {c}" for c in cust] if cust else [S["ai_none"]]
    out += ["", S["ai_us_h"]]
    out += [f"- {o}" for o in ours]
    return out


def data_readiness_section(g: OntologyGraph, gate_data: dict | None = None,
                           lang: str | None = None) -> str:
    S = i18n.strings(lang)
    stl = i18n.STATUS_LABEL[i18n.lang_of(lang)]
    knd = i18n.KIND_LABEL[i18n.lang_of(lang)]
    gate_data = gate_data or {}
    data_status = _normalized_data_status(gate_data.get("data_status") or {})
    action_items = gate_data.get("action_items")

    # GATE 2 실제 분류가 들어온 경우: 보유/부분보유/미보유/파생/모름 표 + 액션 아이템
    if data_status:
        counts = {s: 0 for s in _STATUS_ORDER}
        for d in data_status.values():
            st = _canonical_status((d or {}).get("status"))
            counts[st] = counts.get(st, 0) + 1
        total = len(data_status) or 1
        summary = " · ".join(f"{stl[s]} {counts[s]}"
                             for s in _STATUS_ORDER if counts.get(s))
        th = S["s8_th"]
        lines = [
            S["s8_h"], "",
            S["s8_summary"].format(total=total, summary=summary),
            S["s8_unknown_note"],
            "",
            f"| {th[0]} | {th[1]} | {th[2]} | {th[3]} |",
            "|---|---|---|---|",
        ]
        order = {s: i for i, s in enumerate(_STATUS_ORDER)}
        for name, d in sorted(data_status.items(),
                              key=lambda kv: order.get(_canonical_status(
                                  (kv[1] or {}).get("status")), 9)):
            d = d or {}
            kind = knd["relation"] if d.get("kind") == "relation" else knd["entity"]
            st = _canonical_status(d.get("status"))
            where = d.get("where") or d.get("note") or \
                (S["s8_await"] if st == "모름" else S["s8_dash"])
            lines.append(f"| {name} | {kind} | {stl.get(st, st)} | {where} |")
        lines += _action_items_block(data_status, action_items, lang)
        return "\n".join(lines)

    # 분류 데이터가 없으면 기존 추정(mock) 유지
    ents = list(g.entity_types.keys())
    res = sk._mock_sources("", {"entities": ents})
    avail = res["available"]
    tbs = res["to_be_sourced"]
    total = len(ents) or 1
    ready_pct = round(len(avail) / total * 100)
    lines = [
        S["s8_h"], "",
        S["s8m_ready"].format(pct=ready_pct, avail=len(avail), total=total),
        S["s8m_note"], "",
        S["s8m_have_h"], "",
    ]
    if avail:
        for a in avail:
            lines.append(S["s8m_have_row"].format(
                entity=a["entity"], source=a["source"], schema=a["schema"]))
    else:
        lines.append(S["s8m_none"])
    lines += ["", S["s8m_need_h"], ""]
    if tbs:
        for t in tbs:
            lines.append(S["s8m_need_row"].format(entity=t["entity"], note=t["note"]))
    else:
        lines.append(S["s8m_need_none"])
    lines += ["", S["s8m_next_h"]] + list(S["s8m_next"])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 9) 기술 미팅 인계서 (M3)
# ---------------------------------------------------------------------------
def handover_section(g: OntologyGraph, open_issues: list[str] | None = None,
                     schema_map: dict | None = None, lang: str | None = None) -> str:
    S = i18n.strings(lang)
    kl = S["s90_kind"]
    tb = g.tbox()
    ents, rels = tb["entities"], tb["relations"]

    def m(name: str) -> str:
        return schema_map.get(name, name) if schema_map else name

    lines = [S["s9_h"], "", S["s9_desc"], ""]
    if schema_map:
        # 한글 개념 ↔ 영문 스키마 대응표 (개발자·기획자 공용)
        th = S["s90_th"]
        lines += [
            S["s90_h"], "",
            f"| {th[0]} | {th[1]} | {th[2]} |",
            "| --- | --- | --- |",
        ]
        for name in ents:
            lines.append(f"| {name} | `{m(name)}` | {kl['entity']} |")
        for name in rels:
            lines.append(f"| {name} | `{m(name)}` | {kl['relation']} |")
        seen = set()
        for et in ents.values():
            for k in et["properties"]:
                if k in schema_map and k not in seen:
                    seen.add(k)
                    lines.append(f"| {k} | `{schema_map[k]}` | {kl['prop']} |")
        for rt in rels.values():
            for k in rt["properties"]:
                if k in schema_map and k not in seen:
                    seen.add(k)
                    lines.append(f"| {k} | `{schema_map[k]}` | {kl['prop']} |")
        lines.append("")

    lines += [S["s91_h"], "", S["s91_ent_h"], ""]
    for name, et in ents.items():
        props = ", ".join(f"{m(k)}:{v}" for k, v in et["properties"].items()) or "—"
        lines.append(f"- `{m(name)}` (PK: {m(et['primary_key'])}) — {props}")
    lines += ["", S["s91_rel_h"], ""]
    for name, rt in rels.items():
        rprops = ", ".join(m(k) for k in rt["properties"].keys())
        suffix = f" · {rprops}" if rprops else ""
        lines.append(f"- `{m(name)}`: ({m(rt['src'])})→({m(rt['dst'])}) "
                     f"[{rt.get('cardinality', 'N:M')}]{suffix}")

    lines += [""] + list(S["s92"]) + [""] + list(S["s93"]) + [""] + list(S["s94"])
    lines += ["", S["s95_h"], ""]
    issues = list(open_issues or []) or list(S["s95_default"])
    for it in issues:
        lines.append(f"- {it}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 통합 렌더
# ---------------------------------------------------------------------------
def render_report_md(g: OntologyGraph, title: str = "온톨로지 워크샵 결과",
                     verified_queries: list[dict] | None = None,
                     include_handover: bool = True,
                     open_issues: list[str] | None = None,
                     descriptions: dict | None = None,
                     schema_map: dict | None = None,
                     gate_data: dict | None = None,
                     lang: str | None = None) -> str:
    S = i18n.strings(lang)
    parts = [
        f"# {title}",
        S["generated"].format(now=_now()),
        ontology_intro_section(g, descriptions, lang),
        tbox_diagram_section(g, descriptions, lang),
        entities_section(g, descriptions, lang),
        relations_section(g, descriptions, lang),
        abox_diagram_section(g, descriptions, lang=lang),
        verified_section(verified_queries, lang),
        aws_architecture_section(g, lang),
        migration_plan_section(g, lang),
        data_readiness_section(g, gate_data, lang),
    ]
    if include_handover:
        parts.append(handover_section(g, open_issues, schema_map, lang))
    return "\n\n".join(parts)


def render_report_html(g: OntologyGraph, title: str = "온톨로지 워크샵 결과",
                       verified_queries: list[dict] | None = None,
                       include_handover: bool = True,
                       open_issues: list[str] | None = None,
                       descriptions: dict | None = None,
                       schema_map: dict | None = None,
                       gate_data: dict | None = None,
                       lang: str | None = None) -> str:
    md = render_report_md(g, title, verified_queries, include_handover,
                          open_issues, descriptions, schema_map, gate_data, lang)
    body = _md_to_html(md)
    return (_HTML_TMPL
            .replace("{{LANG}}", i18n.strings(lang)["html_lang"])
            .replace("{{TITLE}}", _html.escape(title))
            .replace("{{BODY}}", body))


# ---------------------------------------------------------------------------
# 경량 Markdown → HTML (헤더/리스트/코드/볼드/표/Mermaid)
# ---------------------------------------------------------------------------
def _is_table_sep(line: str) -> bool:
    s = line.strip()
    return bool(s) and set(s) <= set("|-: ") and "-" in s


def _render_table(rows: list[str]) -> list[str]:
    """| a | b | 형태 행 묶음 → <table>. 첫 행은 헤더, 둘째 구분선."""
    def cells(line: str) -> list[str]:
        parts = line.strip().strip("|").split("|")
        return [_inline(p.strip()) for p in parts]

    out = ["<table>"]
    header = cells(rows[0])
    out.append("<thead><tr>" + "".join(f"<th>{c}</th>" for c in header) + "</tr></thead>")
    out.append("<tbody>")
    for r in rows[2:]:  # rows[1] = 구분선
        out.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells(r)) + "</tr>")
    out.append("</tbody></table>")
    return out


def _md_to_html(md: str) -> str:
    out, in_ul, in_code = [], False, False
    mermaid = False
    lines = md.split("\n")
    i = 0
    n = len(lines)
    while i < n:
        raw = lines[i]
        line = raw.rstrip()
        stripped = line.strip()

        # 코드/머메이드 펜스
        if stripped.startswith("```"):
            if in_code:
                out.append("</pre>")
                in_code, mermaid = False, False
            else:
                if in_ul:
                    out.append("</ul>"); in_ul = False
                if stripped.startswith("```mermaid"):
                    out.append('<pre class="mermaid">'); mermaid = True
                else:
                    out.append("<pre>")
                in_code = True
            i += 1
            continue
        if in_code:
            out.append(line if mermaid else _html.escape(line))
            i += 1
            continue

        # 표 블록
        if stripped.startswith("|") and i + 1 < n and _is_table_sep(lines[i + 1]):
            if in_ul:
                out.append("</ul>"); in_ul = False
            block = []
            while i < n and lines[i].strip().startswith("|"):
                block.append(lines[i])
                i += 1
            out += _render_table(block)
            continue

        line = _inline(line)
        if line.startswith("# "):
            if in_ul:
                out.append("</ul>"); in_ul = False
            out.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            if in_ul:
                out.append("</ul>"); in_ul = False
            out.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "):
            if in_ul:
                out.append("</ul>"); in_ul = False
            out.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("- ") or line.startswith("  - "):
            if not in_ul:
                out.append("<ul>"); in_ul = True
            out.append(f"<li>{line.lstrip(' -')}</li>")
        elif line.startswith("&gt; ") or line.startswith("> "):
            if in_ul:
                out.append("</ul>"); in_ul = False
            txt = line[5:] if line.startswith("&gt; ") else line[2:]
            out.append(f"<blockquote>{txt}</blockquote>")
        elif not line:
            if in_ul:
                out.append("</ul>"); in_ul = False
        else:
            if in_ul:
                out.append("</ul>"); in_ul = False
            out.append(f"<p>{line}</p>")
        i += 1
    if in_ul:
        out.append("</ul>")
    if in_code:
        out.append("</pre>")
    return "\n".join(out)


def _inline(s: str) -> str:
    s = _html.escape(s)
    s = _re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = _re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", s)
    s = _re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    s = s.replace("&lt;br/&gt;", "<br/>").replace("&lt;br&gt;", "<br/>")
    return s


_HTML_TMPL = """<!DOCTYPE html><html lang="{{LANG}}"><head><meta charset="UTF-8">
<title>{{TITLE}}</title>
<style>
body{font-family:-apple-system,'Segoe UI','Malgun Gothic',sans-serif;max-width:860px;
margin:40px auto;padding:0 20px;color:#1a2230;line-height:1.65}
h1{border-bottom:3px solid #34d3a6;padding-bottom:8px}
h2{margin-top:34px;color:#0e7a5f;border-left:4px solid #34d3a6;padding-left:10px}
h3{margin-top:22px;color:#2b3a4f}
code{background:#eef3f1;padding:2px 6px;border-radius:4px;font-size:.9em}
pre{background:#0d1117;color:#e8eef6;padding:14px;border-radius:8px;overflow:auto;font-size:.85em}
blockquote{border-left:4px solid #34d3a6;margin:14px 0;padding:8px 14px;color:#3a4a5e;background:#f0fbf7}
ul{padding-left:22px}li{margin:3px 0}
table{border-collapse:collapse;width:100%;margin:14px 0;font-size:.93em}
th,td{border:1px solid #d7e0dc;padding:8px 10px;text-align:left;vertical-align:top}
th{background:#e8faf3;color:#0e7a5f}
tr:nth-child(even) td{background:#f7faf9}
.mermaid{background:#fbfdfc;border:1px solid #e2ebe7;border-radius:10px;color:#1a2230;
padding:16px;margin:16px 0;text-align:left;white-space:pre-wrap}
</style></head><body>{{BODY}}</body></html>"""
