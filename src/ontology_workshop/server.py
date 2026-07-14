# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""OntoForge 워크샵 서버.
- REST: 엔티티/관계/인스턴스 추가, 쿼리 검증, 익스포트
- WebSocket: 그래프가 바뀔 때마다 시각화에 실시간 push
대화 구조화(에이전트)는 클라이언트/스킬에서 수행하고, 그 결과를 이 API로 반영한다."""
from __future__ import annotations
import asyncio
import datetime as _dt
import hmac
import io
import json
import logging
import os
import zipfile
from contextlib import asynccontextmanager
from ipaddress import ip_address
from typing import Literal
from urllib.parse import urlparse

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.encoders import jsonable_encoder
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

from .graph import OntologyGraph, EntityType, RelationType
from .docgen import render_markdown, render_query_evidence
from . import neptune_export as nx
from . import skills as sk
from . import report_export as rx
from . import snapshot_export as sx
from . import rdf_export as rdfx
from . import rdf_validation as rdfv
from .workflow import WorkflowState, STAGES, STAGE_LABELS
from .security import audit_log, safe_export_path

DB_PATH = os.environ.get("ONTOFORGE_DB", "./workshop.kuzu")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "static")
REPORT_DIR = "./exports/report"
SESSION_PATH = os.environ.get(
    "ONTOFORGE_SESSION_PATH", "./exports/session/workshop_snapshot.json")
AUTH_TOKEN = os.environ.get("ONTOFORGE_TOKEN")
REQUIRE_TOKEN = os.environ.get("ONTOFORGE_REQUIRE_TOKEN", "").lower() in {"1", "true", "yes"}

g: OntologyGraph
clients: set[WebSocket] = set()
verified_queries: list[dict] = []
narrations: list[dict] = []   # Claude Code가 푸시하는 사람용 진행 로그(서머리·Q&A·대화)
workflow = WorkflowState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global g
    _configure_audit_logging()
    fresh = os.environ.get("ONTOFORGE_FRESH") == "1"
    g = OntologyGraph(DB_PATH, fresh=fresh)
    os.makedirs(REPORT_DIR, exist_ok=True)
    if not fresh or os.environ.get("ONTOFORGE_RESTORE_SESSION") == "1":
        _restore_session_on_start()
    yield


app = FastAPI(title="OntoForge", lifespan=lifespan)


@app.middleware("http")
async def optional_token_auth(request: Request, call_next):
    if not _token_required_for_http(request) or request.url.path.startswith("/static/"):
        return await call_next(request)
    if not _valid_http_token(request):
        audit_log("http_rejected", path=request.url.path)
        return _json({"ok": False, "error": "unauthorized"}, status_code=401)
    return await call_next(request)


def _json(content: dict, status_code: int = 200) -> JSONResponse:
    """Kùzu DATE/TIMESTAMP 등 비표준 타입을 안전하게 직렬화."""
    return JSONResponse(jsonable_encoder(content), status_code=status_code)


def _workflow_context() -> dict:
    tb = g.tbox()
    snap = g.snapshot()
    return {
        "graph": {
            "entities": len(tb.get("entities", {})),
            "relations": len(tb.get("relations", {})),
            "nodes": len(snap.get("nodes", [])),
            "edges": len(snap.get("edges", [])),
        },
        "entity_names": list(tb.get("entities", {}).keys()),
        "relation_names": list(tb.get("relations", {}).keys()),
        "verified_count": len(verified_queries),
        "rdf_validation_source_fingerprint": rdfv.source_fingerprint(
            tb, snap, workflow.data,
            (workflow.data.get("last_validation") or {}).get("base_iri")),
    }


def _workflow_payload() -> dict:
    return workflow.to_dict(_workflow_context())


def _graph_payload() -> dict:
    return {"type": "graph", "tbox": g.tbox(), "snapshot": g.snapshot(),
            "workflow": _workflow_payload()}


def _init_payload() -> dict:
    return {"type": "init", "tbox": g.tbox(), "snapshot": g.snapshot(),
            "narrations": narrations, "workflow": _workflow_payload()}


def _graph_is_empty() -> bool:
    return not g.tbox().get("entities") and not g.snapshot().get("nodes")


def _load_session_payload() -> dict | None:
    try:
        path = safe_export_path(SESSION_PATH)
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:  # noqa: BLE001
        audit_log("session_autosave_load_failed", error=str(e))
        return None


def _restore_snapshot_payload(payload: dict, restore_graph: bool = True) -> dict:
    if restore_graph:
        g.reset()
        ents = (payload.get("tbox") or {}).get("entities", {}) or {}
        for name, e in ents.items():
            g.add_entity_type(EntityType(
                name, e.get("properties", {}), e.get("primary_key", "name")))
        rels = (payload.get("tbox") or {}).get("relations", {}) or {}
        for name, r in rels.items():
            g.add_relation_type(RelationType(
                name, r.get("src"), r.get("dst"),
                r.get("cardinality", "N:M"), r.get("properties", {})))

        skipped = 0
        for nd in (payload.get("snapshot") or {}).get("nodes", []):
            d = nd.get("data", {})
            if d.get("etype"):
                g.add_instance(d["etype"], d.get("props", {}))
        for ed in (payload.get("snapshot") or {}).get("edges", []):
            d = ed.get("data", {})
            rtype = d.get("label") or d.get("rtype")
            src = (d.get("source") or "").split(":", 1)[-1]
            dst = (d.get("target") or "").split(":", 1)[-1]
            if rtype and src and dst:
                g.add_edge(rtype, src, dst, d.get("props", {}))
            else:
                skipped += 1
    else:
        skipped = 0

    narrations.clear()
    verified_queries.clear()
    narrations.extend(payload.get("narrations") or [])
    verified_queries.extend(payload.get("verified_queries") or [])
    workflow.load(payload.get("workflow") or {})
    snap = g.snapshot()
    return {"entities": len(g.tbox().get("entities", {})),
            "relations": len(g.tbox().get("relations", {})),
            "nodes": len(snap["nodes"]),
            "edges": len(snap["edges"]),
            "narrations": len(narrations),
            "verified": len(verified_queries),
            "skipped_edges": skipped}


def _restore_session_on_start() -> None:
    payload = _load_session_payload()
    if not payload:
        return
    restore_graph = _graph_is_empty()
    res = _restore_snapshot_payload(payload, restore_graph=restore_graph)
    audit_log("session_autosave_restored", restore_graph=restore_graph, **res)


def _autosave_session() -> None:
    try:
        path = sx.export_snapshot_json(
            g, SESSION_PATH, narrations, verified_queries,
            last_report.get("title") or "OntoForge autosave",
            _workflow_payload())
        audit_log("session_autosaved", path=path)
    except Exception as e:  # noqa: BLE001
        audit_log("session_autosave_failed", error=str(e))


async def _send_all(payload: dict):
    data = json.dumps(payload, ensure_ascii=False, default=str)
    dead = []
    for ws in clients:
        try:
            await ws.send_text(data)
        except Exception:  # noqa: BLE001
            dead.append(ws)
    for ws in dead:
        clients.discard(ws)


async def broadcast():
    """그래프 변경분만 브로드캐스트(증분)."""
    await _send_all(_graph_payload())


async def broadcast_workflow():
    await _send_all({"type": "workflow", "workflow": _workflow_payload()})


def _narration_item(kind: str, title: str, text: str,
                    role: str = "agent", meta: dict | None = None) -> dict:
    return {
        "kind": kind, "title": title, "text": text,
        "role": role, "meta": meta or {},
        "ts": _dt.datetime.now().strftime("%H:%M:%S"),
    }


async def _append_narration(kind: str, title: str, text: str,
                            role: str = "agent", meta: dict | None = None) -> dict:
    item = _narration_item(kind, title, text, role, meta)
    narrations.append(item)
    await _send_all({"type": "narration", "item": item})
    audit_log("narration_added", kind=kind, role=role)
    return item


def _configure_audit_logging() -> None:
    logger = logging.getLogger("ontology_workshop.audit")
    if logger.handlers:
        return
    logger.setLevel(logging.INFO)
    audit_path = os.environ.get("ONTOFORGE_AUDIT_LOG", "./exports/audit.log")
    try:
        audit_path = safe_export_path(audit_path)
        os.makedirs(os.path.dirname(audit_path), exist_ok=True)
        handler = logging.FileHandler(audit_path, encoding="utf-8")
        os.chmod(audit_path, 0o600)
    except Exception:  # noqa: BLE001
        handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)


def _valid_ws_origin(websocket: WebSocket) -> bool:
    origin = websocket.headers.get("origin")
    host = websocket.headers.get("host")
    if not origin or not host:
        return True
    parsed = urlparse(origin)
    return parsed.netloc == host or parsed.hostname in {"localhost", "127.0.0.1", "::1"}


def _is_loopback_host(host: str | None) -> bool:
    if not host:
        return False
    if host.lower() == "localhost":
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


def _token_required_for_http(request: Request) -> bool:
    if not AUTH_TOKEN:
        return False
    if REQUIRE_TOKEN:
        return True
    return not _is_loopback_host(request.client.host if request.client else None)


def _token_required_for_ws(websocket: WebSocket) -> bool:
    if not AUTH_TOKEN:
        return False
    if REQUIRE_TOKEN:
        return True
    return not _is_loopback_host(websocket.client.host if websocket.client else None)


def _valid_ws_token(websocket: WebSocket) -> bool:
    if not _token_required_for_ws(websocket):
        return True
    supplied = websocket.query_params.get("token") or ""
    return hmac.compare_digest(supplied, AUTH_TOKEN)


def _valid_http_token(request: Request) -> bool:
    supplied = request.query_params.get("token") or request.headers.get("x-ontoforge-token", "")
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        supplied = auth.split(" ", 1)[1].strip()
    return hmac.compare_digest(supplied, AUTH_TOKEN)


# ---- 스키마 ---------------------------------------------------------
class EntityIn(BaseModel):
    name: str
    properties: dict[str, str] = {}
    primary_key: str = "name"


class RelationIn(BaseModel):
    name: str
    src: str
    dst: str
    cardinality: str = "N:M"
    properties: dict[str, str] = {}


class InstanceIn(BaseModel):
    etype: str
    props: dict


class EdgeIn(BaseModel):
    rtype: str
    src_key: str
    dst_key: str
    props: dict = {}


class QueryIn(BaseModel):
    cypher: str
    parameters: dict = {}
    question: str | None = None


class SkillIn(BaseModel):
    skill: str
    text: str
    apply: bool = True  # 결과를 그래프에 자동 반영할지


class NarrateIn(BaseModel):
    """Claude Code → 브라우저 진행 로그 푸시.
    kind: chat(대화) | reflect(반영 서머리) | qa(쿼리 Q&A) | note(메모) | system."""
    kind: Literal["chat", "reflect", "qa", "note", "system"] = "note"
    title: str = ""
    text: str = ""
    role: Literal["operator", "customer", "agent", "system"] = "agent"
    meta: dict = {}


@app.post("/narrate")
async def narrate(n: NarrateIn):
    item = {
        "kind": n.kind, "title": n.title, "text": n.text,
        "role": n.role, "meta": n.meta,
        "ts": _dt.datetime.now().strftime("%H:%M:%S"),
    }
    narrations.append(item)
    await _send_all({"type": "narration", "item": item})
    _autosave_session()
    audit_log("narration_added", kind=n.kind, role=n.role)
    return {"ok": True, "count": len(narrations)}


class FocusIn(BaseModel):
    """그래프에 쿼리 답을 투영(초점). ids = 시각화 노드 id 목록("{etype}:{pk}").
    mode: isolate(나머지 숨김) | clear(해제)."""
    ids: list[str] = []
    label: str = ""
    mode: str = "isolate"


@app.post("/focus")
async def focus(f: FocusIn):
    await _send_all({"type": "focus", "ids": f.ids, "label": f.label, "mode": f.mode})
    return {"ok": True, "n": len(f.ids)}


# ---- AI-ODLC workflow state -------------------------------------------
class WorkflowStartIn(BaseModel):
    language: str | None = None
    scope: str | None = None
    reset: bool = False


class WorkflowAnswerIn(BaseModel):
    text: str
    stage: str | None = None
    role: str = "customer"
    status: str = "candidate"
    source: str = "workflow_answer"
    extracted: dict | None = None


class WorkflowAdvanceIn(BaseModel):
    stage: str | None = None
    force: bool = False


class WorkflowReviewIn(BaseModel):
    findings: list[dict] = []
    assumptions: list[dict] = []
    risks: list[dict] = []
    action_items: list[dict] = []


class WorkflowValidateIn(BaseModel):
    outdir: str = "./exports/validation"
    base_iri: str | None = None


class WorkflowItemIn(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    text: str | None = None
    status: str | None = None
    source: str | None = None
    stage: str | None = None


def _workflow_item(body: WorkflowItemIn) -> dict:
    return body.model_dump(exclude_none=True)


def _review_summary(added: dict[str, list[dict]]) -> str:
    parts = []
    labels = {
        "review_findings": "findings",
        "assumptions": "assumptions",
        "risks": "risks",
        "action_items": "actions",
    }
    for key, label in labels.items():
        count = len(added.get(key) or [])
        if count:
            parts.append(f"{count} {label}")
    return "Adversarial review recorded: " + (", ".join(parts) if parts else "no new findings")


async def _save_and_broadcast_workflow(event: str, **fields):
    _autosave_session()
    await broadcast_workflow()
    audit_log(event, **fields)


@app.get("/workflow/state")
async def workflow_state():
    return {"ok": True, "workflow": _workflow_payload(), "stages": STAGES}


@app.post("/workflow/start")
async def workflow_start(body: WorkflowStartIn):
    state = workflow.start(body.language, body.scope, body.reset)
    await _save_and_broadcast_workflow(
        "workflow_started", language=body.language, reset=body.reset)
    return {"ok": True, "workflow": state, "stages": STAGES}


@app.post("/workflow/answer")
async def workflow_answer(body: WorkflowAnswerIn):
    result = workflow.process_answer(
        body.text, body.stage, body.role, body.status, body.source,
        body.extracted, _workflow_context())
    item = result["claim"]
    await _append_narration(
        "chat", STAGE_LABELS.get(item.get("stage"), item.get("stage", "AI-ODLC")),
        body.text, body.role,
        {"workflow_claim_id": item.get("id"), "stage": item.get("stage")})
    summary = result.get("summary", {})
    await _append_narration(
        "reflect", "AI-ODLC extraction",
        summary.get("summary") or "claim captured",
        "agent", {"workflow": summary})
    await _save_and_broadcast_workflow(
        "workflow_answer_recorded", stage=item.get("stage"), status=item.get("status"))
    return {"ok": True, **result, "workflow": _workflow_payload()}


@app.post("/workflow/clarify")
async def workflow_clarify(body: WorkflowAnswerIn):
    result = workflow.process_answer(
        body.text, body.stage, body.role, body.status,
        "workflow_clarification", body.extracted, _workflow_context())
    item = result["claim"]
    await _append_narration(
        "chat", "Clarification", body.text, body.role,
        {"workflow_claim_id": item.get("id"), "stage": item.get("stage")})
    await _save_and_broadcast_workflow(
        "workflow_clarification_recorded",
        stage=item.get("stage"), status=item.get("status"))
    return {"ok": True, **result, "workflow": _workflow_payload()}


@app.post("/workflow/advance")
async def workflow_advance(body: WorkflowAdvanceIn):
    try:
        result = workflow.advance(body.stage, body.force, _workflow_context())
    except ValueError as e:
        return _json({"ok": False, "error": str(e)}, status_code=400)
    if result.get("ok"):
        await _save_and_broadcast_workflow(
            "workflow_advanced", stage=result.get("stage"), force=body.force)
    return _json(result)


@app.post("/workflow/review")
async def workflow_review(body: WorkflowReviewIn):
    if body.findings or body.assumptions or body.risks or body.action_items:
        added = workflow.add_review(
            body.findings, body.assumptions, body.risks, body.action_items)
    else:
        added = workflow.generate_review(_workflow_context())
    await _append_narration(
        "reflect", "Adversarial review",
        _review_summary(added), "agent", {"review": added})
    await _save_and_broadcast_workflow(
        "workflow_review_recorded",
        findings=len(added["review_findings"]),
        assumptions=len(added["assumptions"]),
        risks=len(added["risks"]),
        action_items=len(added["action_items"]))
    return {"ok": True, "added": added, "workflow": _workflow_payload()}


@app.post("/workflow/validate")
async def workflow_validate(body: WorkflowValidateIn | None = None):
    """Run one explicit static RDF/SPARQL/SHACL handoff validation."""
    body = body or WorkflowValidateIn()
    try:
        base_iri = (body.base_iri or last_report.get("rdf_base_iri")
                    or rdfx.DEFAULT_BASE_IRI)
        bundle = rdfx.export_all(g, body.outdir, _workflow_payload(), base_iri)
        result = rdfv.validate_bundle(bundle, g.tbox())
        result["base_iri"] = base_iri
        result["source_fingerprint"] = rdfv.source_fingerprint(
            g.tbox(), g.snapshot(), workflow.data, base_iri)
        result["freshness"] = "current"
        reports = rdfv.write_reports(result, body.outdir)
        result["reports"] = reports
        workflow.record_static_validation(result)
    except (OSError, UnicodeError, ValueError) as e:
        return _json({"ok": False, "error": str(e)}, status_code=400)

    await _append_narration(
        "reflect", "RDF handoff static validation", result["summary"], "agent",
        {"validation": {
            "scope": result["scope"],
            "status": result["status"],
            "counts": result["counts"],
            "reports": reports,
        }})
    await _save_and_broadcast_workflow(
        "workflow_static_validation_recorded",
        scope=result["scope"], status=result["status"],
        passed=result["counts"]["passed"],
        warnings=result["counts"]["warnings"],
        failed=result["counts"]["failed"])
    return {
        "ok": result["status"] != "fail",
        "validation": result,
        "workflow": _workflow_payload(),
    }


@app.get("/workflow/gates")
async def workflow_gates():
    return {"ok": True, "gates": workflow.gates(_workflow_context())}


@app.get("/workflow/next-question")
async def workflow_next_question():
    question = workflow.next_question(_workflow_context())
    workflow.data["active_question"] = question
    workflow.touch()
    return {"ok": True, "question": question, "workflow": _workflow_payload()}


@app.get("/coverage")
async def workflow_coverage():
    wf = _workflow_payload()
    return {
        "ok": True,
        "progress": wf.get("progress", {}),
        "gates": wf.get("gates", {}),
        "counts": {
            "claims": len(wf.get("claims") or []),
            "user_stories": len(wf.get("user_stories") or []),
            "domain_events": len(wf.get("domain_events") or []),
            "competency_questions": len(wf.get("competency_questions") or []),
            "model_candidates": len(wf.get("model_candidates") or []),
            "data_sources": len(wf.get("data_sources") or []),
            "field_mappings": len(wf.get("field_mappings") or []),
            "risks": len(wf.get("risks") or []),
            "assumptions": len(wf.get("assumptions") or []),
            "action_items": len(wf.get("action_items") or []),
            "validation_queries": len(wf.get("validation_queries") or []),
            "rdf_decisions": len(wf.get("rdf_decisions") or []),
        },
    }


async def _add_workflow_item(collection: str, prefix: str, body: WorkflowItemIn):
    try:
        item = workflow.add_item(collection, prefix, _workflow_item(body))
        if collection in {
            "competency_questions", "model_candidates", "data_sources",
            "field_mappings", "rdf_decisions",
        }:
            workflow._refresh_query_candidates(_workflow_context())
            workflow.data["active_question"] = workflow.next_question(_workflow_context())
    except ValueError as e:
        return _json({"ok": False, "error": str(e)}, status_code=400)
    await _save_and_broadcast_workflow(
        "workflow_item_added", collection=collection, item_id=item.get("id"))
    return {"ok": True, "item": item, "workflow": _workflow_payload()}


@app.post("/claim")
async def add_claim(body: WorkflowItemIn):
    return await _add_workflow_item("claims", "claim", body)


@app.post("/story")
async def add_story(body: WorkflowItemIn):
    return await _add_workflow_item("user_stories", "story", body)


@app.post("/event")
async def add_event(body: WorkflowItemIn):
    return await _add_workflow_item("domain_events", "event", body)


@app.post("/question")
async def add_question(body: WorkflowItemIn):
    return await _add_workflow_item("competency_questions", "question", body)


@app.post("/model-candidate")
async def add_model_candidate(body: WorkflowItemIn):
    return await _add_workflow_item("model_candidates", "model", body)


@app.post("/data-source")
async def add_data_source(body: WorkflowItemIn):
    return await _add_workflow_item("data_sources", "source", body)


@app.post("/mapping")
async def add_mapping(body: WorkflowItemIn):
    return await _add_workflow_item("field_mappings", "mapping", body)


@app.post("/validation-query")
async def add_validation_query(body: WorkflowItemIn):
    return await _add_workflow_item("validation_queries", "query", body)


@app.post("/rdf-decision")
async def add_rdf_decision(body: WorkflowItemIn):
    return await _add_workflow_item("rdf_decisions", "rdf", body)


@app.post("/skill")
async def run_skill(s: SkillIn):
    """대화 텍스트 → 스킬 실행 → (옵션)그래프 반영 → 브로드캐스트."""
    ctx = {
        "entities": list(g.entity_types.keys()),
        "relations": list(g.relation_types.keys()),
    }
    out = sk.run_skill(s.skill, s.text, ctx)
    if not out.get("ok"):
        return _json(out, status_code=400)

    result = out["result"]
    # verify_query는 반영이 아니라 즉시 실행/검증
    if s.skill == "verify_query":
        cypher = result.get("cypher", "")
        qres = g.query(cypher)
        question = result.get("question", s.text)
        qres["evidence_md"] = render_query_evidence(question, cypher, qres)
        out["query_result"] = qres
        out["cypher"] = cypher
        # 성공한 질의는 서머리용으로 기록
        if qres.get("ok"):
            verified_queries.append(
                {"question": question, "cypher": cypher, "count": qres["count"]})
        workflow.record_query_verification(question, cypher, qres)
        _autosave_session()
        return _json(out)

    if s.apply:
        out["applied"] = sk.apply_to_graph(g, s.skill, result)
        await broadcast()
        _autosave_session()
    return _json(out)


@app.post("/entity")
async def add_entity(e: EntityIn):
    r = g.add_entity_type(EntityType(e.name, e.properties, e.primary_key))
    await broadcast()
    _autosave_session()
    return r


@app.post("/relation")
async def add_relation(r: RelationIn):
    out = g.add_relation_type(
        RelationType(r.name, r.src, r.dst, r.cardinality, r.properties))
    await broadcast()
    _autosave_session()
    return out


@app.post("/instance")
async def add_instance(i: InstanceIn):
    r = g.add_instance(i.etype, i.props)
    await broadcast()
    _autosave_session()
    return r


@app.post("/edge")
async def add_edge(e: EdgeIn):
    r = g.add_edge(e.rtype, e.src_key, e.dst_key, e.props)
    await broadcast()
    _autosave_session()
    return r


@app.post("/query")
async def run_query(q: QueryIn):
    r = g.query(q.cypher, q.parameters)
    if q.question:
        r["evidence_md"] = render_query_evidence(q.question, q.cypher, r)
        # question을 단 성공 질의는 보고서 §5(설득 증거)에 등록(중복 방지)
        if r.get("ok") and not any(
                v["question"] == q.question and v["cypher"] == q.cypher
                for v in verified_queries):
            verified_queries.append(
                {"question": q.question, "cypher": q.cypher,
                 "count": r.get("count", 0)})
        workflow.record_query_verification(q.question, q.cypher, r)
        _autosave_session()
    return _json(r)


@app.get("/markdown")
async def markdown(title: str = "온톨로지"):
    return {"markdown": render_markdown(g, title)}


@app.post("/export/neptune")
async def export_neptune():
    os.makedirs("./exports", exist_ok=True)
    sm = last_report.get("schema_map")
    oc = nx.export_opencypher(g, "./exports/neptune.cypher", sm)
    csvs = nx.export_bulk_csv(g, "./exports/bulk", sm)
    return {"opencypher": oc, "bulk": csvs}


@app.get("/snapshot")
async def snapshot():
    return {"tbox": g.tbox(), "snapshot": g.snapshot(),
            "workflow": _workflow_payload()}


# ---- M2: 변경 모드 / 백지 시작 -------------------------------------
class DropIn(BaseModel):
    kind: str          # "entity" | "relation"
    name: str


class DelInstanceIn(BaseModel):
    etype: str
    key: str


class DelEdgeIn(BaseModel):
    rtype: str
    src_key: str
    dst_key: str


@app.post("/reset")
async def reset():
    """백지 시작: 그래프 전체 + 진행 로그 초기화."""
    r = g.reset()
    verified_queries.clear()
    narrations.clear()
    workflow.reset()
    await _send_all(_init_payload())   # 클라이언트 피드까지 비우도록 init 재전송
    _autosave_session()
    audit_log("server_reset")
    return r


@app.post("/drop")
async def drop(d: DropIn):
    r = g.drop_entity_type(d.name) if d.kind == "entity" \
        else g.drop_relation_type(d.name)
    await broadcast()
    _autosave_session()
    return r


@app.post("/instance/delete")
async def del_instance(d: DelInstanceIn):
    r = g.delete_instance(d.etype, d.key)
    await broadcast()
    _autosave_session()
    return r


@app.post("/edge/delete")
async def del_edge(d: DelEdgeIn):
    r = g.delete_edge(d.rtype, d.src_key, d.dst_key)
    await broadcast()
    _autosave_session()
    return r


# ---- M2: 워크샵 산출물 3종 ----------------------------------------
class ReportIn(BaseModel):
    """보고서 내보내기. descriptions로 비개발자용 한글 라벨·'왜' 설명을 주입.
    형식: {"domain": "...", "entities": {"Concept": {"label":"개념","why":"..."}},
           "relations": {"PRECEDES": {"label":"선행","why":"..."}}}"""
    title: str = "온톨로지 워크샵 결과"
    descriptions: dict | None = None
    open_issues: list[str] | None = None
    # 한글 식별자 → 영문 구현 스키마 매핑(개발자용 §9 인계서·Neptune 익스포트에만 적용)
    schema_map: dict | None = None
    # Gate 2 data status: {"<element>": {"kind","status","where","note"}}.
    # Accepted status aliases include available, partial, missing, derived, unknown.
    # They are normalized during report generation for localized display/action items.
    data_status: dict | None = None
    action_items: dict | None = None  # {"customer":[...],"us":[...]}
    # 보고서/스냅샷 UI 언어(ko|en|ja). 엔터티·데이터 라벨은 고객 도메인이라 번역하지 않음.
    lang: str | None = None
    # RDF/JSON-LD/SHACL export base IRI.
    rdf_base_iri: str | None = None


# 마지막으로 사용한 비개발자 설명/제목을 기억 → ZIP 재생성 시 풍부한 보고서 유지
last_report: dict = {"title": "온톨로지 워크샵 결과",
                     "descriptions": None, "open_issues": None,
                     "schema_map": None, "gate_data": None, "lang": None,
                     "rdf_base_iri": None}


def _gate_data(body: "ReportIn") -> dict | None:
    if body.data_status or body.action_items:
        return {"data_status": body.data_status,
                "action_items": body.action_items}
    return None


@app.post("/export/report")
async def export_report(body: ReportIn | None = None):
    body = body or ReportIn()
    # 명시적으로 보낸 필드만 last_report에 덮어쓴다. 뷰어의 📄 버튼은 {lang}만 보내므로,
    # 운영자가 앞서 주입한 descriptions·data_status 등이 None으로 지워지지 않게 보존한다.
    sent = body.model_fields_set
    title = body.title if "title" in sent else (last_report.get("title")
                                                or "온톨로지 워크샵 결과")
    descriptions = (body.descriptions if "descriptions" in sent
                    else last_report.get("descriptions"))
    open_issues = (body.open_issues if "open_issues" in sent
                   else last_report.get("open_issues"))
    schema_map = (body.schema_map if "schema_map" in sent
                  else last_report.get("schema_map"))
    gate_data = (_gate_data(body) if {"data_status", "action_items"} & sent
                 else last_report.get("gate_data"))
    lang = body.lang if "lang" in sent else last_report.get("lang")
    rdf_base_iri = (body.rdf_base_iri if "rdf_base_iri" in sent
                    else last_report.get("rdf_base_iri"))

    last_report.update(title=title, descriptions=descriptions,
                       open_issues=open_issues, schema_map=schema_map,
                       gate_data=gate_data, lang=lang,
                       rdf_base_iri=rdf_base_iri)
    _autosave_session()
    res = rx.export_all(g, REPORT_DIR, title, verified_queries,
                        open_issues, descriptions, schema_map,
                        gate_data, lang, _workflow_payload(), rdf_base_iri)
    # 단독 실행 스냅샷 뷰어 + 복원용 JSON 함께 생성
    res["snapshot_viewer"] = sx.export_static_viewer(
        g, os.path.join(REPORT_DIR, "workshop_snapshot.html"),
        narrations, verified_queries, title, _workflow_payload())
    res["snapshot_json"] = sx.export_snapshot_json(
        g, os.path.join(REPORT_DIR, "workshop_snapshot.json"),
        narrations, verified_queries, title, _workflow_payload())
    audit_log("report_exported", title=title, lang=lang)
    return res


class RdfExportIn(BaseModel):
    outdir: str = "./exports/rdf"
    base_iri: str | None = None


@app.post("/export/rdf")
async def export_rdf(body: RdfExportIn | None = None):
    body = body or RdfExportIn()
    try:
        res = rdfx.export_all(
            g, body.outdir, _workflow_payload(),
            body.base_iri or last_report.get("rdf_base_iri")
            or rdfx.DEFAULT_BASE_IRI)
    except ValueError as e:
        return _json({"ok": False, "error": str(e)}, status_code=400)
    audit_log("rdf_exported", outdir=body.outdir, base_iri=body.base_iri)
    return {"ok": True, "rdf": res}


class ImportIn(BaseModel):
    """스냅샷 산출물(workshop_snapshot.json 또는 .html 임베드 payload)로
    워크샵 전체(T-Box·A-Box·대화·검증질의)를 복원. 여분 키(title/generated)는 무시."""
    tbox: dict = {}
    snapshot: dict = {}
    narrations: list = []
    verified_queries: list = []
    workflow: dict = {}


@app.post("/import")
async def import_snapshot(s: ImportIn):
    """스냅샷을 현재 서버에 올린다(백지화 후 재구성 → 라이브 뷰어로 즉시 표시)."""
    res = _restore_snapshot_payload(s.model_dump(), restore_graph=True)
    await _send_all(_init_payload())
    _autosave_session()
    audit_log("snapshot_imported", **res)
    return {"ok": True, **res}


@app.get("/export/snapshot.html", response_class=HTMLResponse)
async def export_snapshot():
    """대화·인스턴스·스키마·상태를 그대로 담은 단독 실행 HTML(브라우저에서 바로 열림)."""
    return sx.build_static_viewer(g, narrations, verified_queries,
                                  last_report.get("title") or "온톨로지 워크샵 스냅샷",
                                  _workflow_payload())


@app.get("/download/workshop.zip")
async def download_zip():
    """보고서(md/html/docx) + 단독 스냅샷 + Neptune 익스포트를 ZIP 한 방에."""
    # 최신 상태로 산출물 재생성(마지막 설명/제목 재사용)
    rx.export_all(g, REPORT_DIR, last_report.get("title") or "온톨로지 워크샵 결과",
                  verified_queries, last_report.get("open_issues"),
                  last_report.get("descriptions"), last_report.get("schema_map"),
                  last_report.get("gate_data"), last_report.get("lang"),
                  _workflow_payload(), last_report.get("rdf_base_iri"))
    title = last_report.get("title") or "온톨로지 워크샵 스냅샷"
    sx.export_static_viewer(
        g, os.path.join(REPORT_DIR, "workshop_snapshot.html"),
        narrations, verified_queries, title, _workflow_payload())
    # 스킬 재발동 복원용 JSON도 묶음에 포함
    sx.export_snapshot_json(
        g, os.path.join(REPORT_DIR, "workshop_snapshot.json"),
        narrations, verified_queries, title, _workflow_payload())

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _dirs, files in os.walk(REPORT_DIR):
            for fn in files:
                # 내부 임시·설명 json은 제외하되 복원용 스냅샷 json은 포함
                if fn.startswith("~$") or (
                        fn.endswith(".json") and fn != "workshop_snapshot.json"):
                    continue
                full = os.path.join(root, fn)
                arc = os.path.relpath(full, REPORT_DIR)
                z.write(full, arc)
    buf.seek(0)
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M")
    return Response(
        content=buf.getvalue(), media_type="application/zip",
        headers={"Content-Disposition":
                 f'attachment; filename="ontoforge_workshop_{stamp}.zip"'})


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    if not _valid_ws_origin(websocket) or not _valid_ws_token(websocket):
        audit_log("websocket_rejected", host=websocket.headers.get("host"),
                  origin=websocket.headers.get("origin"))
        await websocket.close(code=1008)
        return
    await websocket.accept()
    clients.add(websocket)
    audit_log("websocket_connected",
              token_required=_token_required_for_ws(websocket))
    await websocket.send_text(json.dumps(
        _init_payload(), ensure_ascii=False, default=str))
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        clients.discard(websocket)


@app.get("/", response_class=HTMLResponse)
async def index():
    with open(os.path.join(STATIC_DIR, "index.html"), encoding="utf-8") as f:
        return f.read()


@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)


if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# 생성된 산출물(보고서 HTML·스냅샷 등)을 브라우저에서 바로 열람
os.makedirs(REPORT_DIR, exist_ok=True)
app.mount("/files", StaticFiles(directory=REPORT_DIR, html=True), name="files")
