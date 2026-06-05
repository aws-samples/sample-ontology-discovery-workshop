# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""워크샵 '단독 실행' 스냅샷 뷰어 생성기.

라이브 뷰어(static/index.html)와 동일한 화면(대화 피드·인스턴스·스키마·상태)을
서버/웹소켓 없이 파일 하나로 보도록 만든다. 그래프 데이터(T-Box/A-Box),
대화 로그(narrations), 검증 질의(verified_queries)를 HTML에 인라인하고,
cytoscape.js도 가능하면 인라인해 완전 오프라인으로 연다.
"""
from __future__ import annotations

import datetime as _dt
import html as _html
import json
import os

from .graph import OntologyGraph
from .security import audit_log, safe_export_path

_VENDOR = os.path.join(os.path.dirname(__file__), "..", "..",
                       "static", "vendor", "cytoscape-3.30.2.min.js")
_INDEX = os.path.join(os.path.dirname(__file__), "..", "..", "static", "index.html")

_LOCAL_TAG = '<script src="/static/vendor/cytoscape-3.30.2.min.js"></script>'
_BOOTSTRAP_LINE = "initCy();loadPanels();connect();"


def _cytoscape_inline_tag() -> str:
    """오프라인용: 로컬 vendor 파일을 인라인."""
    try:
        with open(_VENDOR, encoding="utf-8") as f:
            js = f.read()
        return "<script>" + js + "</script>"
    except OSError:
        return "<script>throw new Error('Missing local Cytoscape vendor file');</script>"


def snapshot_payload(g: OntologyGraph,
                     narrations: list[dict] | None = None,
                     verified_queries: list[dict] | None = None,
                     title: str = "온톨로지 워크샵 스냅샷") -> dict:
    """스냅샷 1건의 전체 데이터(복원·뷰어 공용)."""
    return {
        "title": title,
        "generated": _dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "tbox": g.tbox(),
        "snapshot": g.snapshot(),
        "narrations": narrations or [],
        "verified_queries": verified_queries or [],
    }


def export_snapshot_json(g: OntologyGraph, path: str,
                         narrations: list[dict] | None = None,
                         verified_queries: list[dict] | None = None,
                         title: str = "온톨로지 워크샵 스냅샷") -> str:
    """스킬 재발동 시 `POST /import`로 바로 복원할 수 있는 JSON 산출물."""
    path = safe_export_path(path)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    payload = snapshot_payload(g, narrations, verified_queries, title)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, default=str, indent=2)
    os.chmod(path, 0o600)
    audit_log("snapshot_json_exported", path=path)
    return path


def build_static_viewer(g: OntologyGraph,
                        narrations: list[dict] | None = None,
                        verified_queries: list[dict] | None = None,
                        title: str = "온톨로지 워크샵 스냅샷") -> str:
    with open(_INDEX, encoding="utf-8") as f:
        html = f.read()

    payload = snapshot_payload(g, narrations, verified_queries, title)
    data_json = json.dumps(payload, ensure_ascii=False, default=str)

    # 1) cytoscape 인라인(오프라인)
    html = html.replace(_LOCAL_TAG, _cytoscape_inline_tag())

    # 2) 데이터 임베드 + 오프라인 부트스트랩으로 connect() 대체
    boot = (
        'window.__ONTOFORGE_SNAPSHOT__ = ' + data_json + ';\n'
        'initCy();loadPanels();\n'
        '(function(){\n'
        '  var S = window.__ONTOFORGE_SNAPSHOT__;\n'
        '  var dot=document.getElementById("dot");\n'
        '  if(dot) dot.classList.add("on");\n'
        '  var conn=document.getElementById("conn");\n'
        '  if(conn) conn.textContent=t("connSnap")+" · "+(S.generated||"");\n'
        '  lastData={tbox:S.tbox,snapshot:S.snapshot};\n'
        '  clearFeed();(S.narrations||[]).forEach(addFeed);\n'
        '  if(!(S.narrations||[]).length){\n'
        '    var feed=document.getElementById("feed");\n'
        '    if(feed) feed.innerHTML="<div class=\\"empty\\">"+t("noSnapshotFeed")+"</div>";\n'
        '  }\n'
        '  render();\n'
        '  // 서버 의존 동작은 스냅샷에서 비활성(오프라인)\n'
        '  var off=function(){alert(t("snapshotUnavailable"));};\n'
        '  window.resetGraph=window.exportReport=window.exportNeptune='
        'window.openSnapshot=window.downloadZip=off;\n'
        '})();'
    )
    html = html.replace(_BOOTSTRAP_LINE, boot)

    # 3) 헤더 라벨: 스냅샷임을 명시 + 서버 버튼 영역 제거
    html = html.replace(
        "Onto<b>Forge</b> · <span data-i18n=\"subtitle\">온톨로지 디스커버리 워크샵</span>",
        "Onto<b>Forge</b> · <span data-i18n='snapshotTitle'>워크샵 스냅샷</span> "
        "<span style='font-weight:400;opacity:.7'>("
        + _html.escape(payload["generated"]) + ")</span>")
    import re  # noqa: PLC0415
    html = re.sub(
        r"<!--SRVBTNS-->.*?<!--/SRVBTNS-->",
        '<span data-i18n="readOnlySnapshot" '
        'style="font-size:12px;color:var(--muted)">읽기 전용 스냅샷</span>',
        html, flags=re.DOTALL)

    # 4) 피드 빈 상태 문구(데이터 없을 때만 노출되므로 무해)
    html = html.replace(
        "아직 대화가 없습니다.<br>Claude Code에서 워크샵을 시작하세요.",
        "이 스냅샷에 기록된 대화가 없습니다.")

    # <title> 갱신
    if "<title>" in html:
        import re  # noqa: PLC0415
        html = re.sub(r"<title>.*?</title>",
                      f"<title>{_html.escape(title)}</title>", html, count=1)
    return html


def export_static_viewer(g: OntologyGraph, path: str,
                         narrations: list[dict] | None = None,
                         verified_queries: list[dict] | None = None,
                         title: str = "온톨로지 워크샵 스냅샷") -> str:
    path = safe_export_path(path)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    html = build_static_viewer(g, narrations, verified_queries, title)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    os.chmod(path, 0o600)
    audit_log("snapshot_viewer_exported", path=path)
    return path
