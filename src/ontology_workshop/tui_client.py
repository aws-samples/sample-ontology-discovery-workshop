# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Dependency-light HTTP client and render helpers for the OntoForge TUI."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, AsyncIterator

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed


PANEL_COLLECTIONS: dict[str, tuple[str, ...]] = {
    "stories": ("user_stories", "claims"),
    "events": ("domain_events",),
    "questions": ("competency_questions", "validation_queries"),
    "model": ("model_candidates",),
    "data": ("data_sources", "field_mappings"),
    "review": ("review_findings", "assumptions", "contradictions", "risks"),
    "actions": ("action_items",),
}

DECISION_COLLECTIONS = {
    "claims", "assumptions", "contradictions",
    "review_findings", "risks", "action_items",
}


class ApiError(RuntimeError):
    """A reachable OntoForge server returned an unsuccessful response."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


@dataclass(slots=True)
class WorkflowApiClient:
    """Small synchronous client; Textual runs calls in worker threads."""

    base_url: str = "http://127.0.0.1:8000"
    token: str | None = None
    timeout: float = 15.0

    def __post_init__(self) -> None:
        parsed = urllib.parse.urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("server URL must be an absolute http(s) URL")
        self.base_url = self.base_url.rstrip("/")

    def get_state(self) -> dict[str, Any]:
        return self.request("GET", "/workflow/state")

    @property
    def websocket_url(self) -> str:
        parsed = urllib.parse.urlparse(self.base_url + "/ws")
        scheme = "wss" if parsed.scheme == "https" else "ws"
        query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        if self.token:
            query.append(("token", self.token))
        return urllib.parse.urlunparse(parsed._replace(
            scheme=scheme, query=urllib.parse.urlencode(query)))

    async def workflow_updates(self) -> AsyncIterator[dict[str, Any]]:
        """Yield live workflow state from one connection, without retry/polling."""
        try:
            async with connect(
                    self.websocket_url, open_timeout=self.timeout,
                    ping_interval=None) as websocket:
                async for raw in websocket:
                    try:
                        message = json.loads(raw)
                    except (json.JSONDecodeError, TypeError):
                        continue
                    if not isinstance(message, dict):
                        continue
                    workflow = message.get("workflow")
                    if (message.get("type") in {"init", "graph", "workflow"}
                            and isinstance(workflow, dict)):
                        yield workflow
        except ConnectionClosed as error:
            raise ApiError(f"live stream closed: {error}") from error

    def answer(self, text: str, stage: str) -> dict[str, Any]:
        if not text.strip():
            raise ValueError("answer text is required")
        return self.request("POST", "/workflow/answer", {
            "text": text.strip(), "stage": stage, "role": "customer",
            "source": "terminal_tui",
        })

    def advance(self, *, force: bool = False, reason: str = "") -> dict[str, Any]:
        payload: dict[str, Any] = {"force": force, "actor": "terminal-operator"}
        if force:
            payload["reason"] = reason.strip()
        return self.request("POST", "/workflow/advance", payload)

    def review(self) -> dict[str, Any]:
        return self.request("POST", "/workflow/review", {})

    def validate(self) -> dict[str, Any]:
        return self.request("POST", "/workflow/validate", {})

    def decide(self, collection: str, item_id: str, action: str, note: str,
               changes: dict[str, Any] | None = None,
               owner: str = "") -> dict[str, Any]:
        if collection not in DECISION_COLLECTIONS:
            raise ValueError(f"collection {collection} does not support decisions")
        if not item_id:
            raise ValueError("item id is required")
        if not note.strip():
            raise ValueError("decision note is required")
        payload: dict[str, Any] = {
            "action": action,
            "changes": changes or {},
            "note": note.strip(),
            "actor": "terminal-operator",
        }
        if owner.strip():
            payload["linked_action"] = {
                "text": f"Address accepted {collection} {item_id}",
                "owner": owner.strip(),
            }
        path = (
            f"/workflow/items/{urllib.parse.quote(collection, safe='')}"
            f"/{urllib.parse.quote(item_id, safe='')}/decision"
        )
        return self.request("POST", path, payload)

    def request(self, method: str, path: str,
                payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if not path.startswith("/"):
            raise ValueError("API path must start with /")
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["X-OntoForge-Token"] = self.token
        request = urllib.request.Request(
            self.base_url + path, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                status = response.status
        except urllib.error.HTTPError as error:
            raw = error.read().decode("utf-8", errors="replace")
            message = _error_message(raw) or error.reason or f"HTTP {error.code}"
            raise ApiError(str(message), error.code) from error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            reason = getattr(error, "reason", error)
            raise ApiError(f"cannot reach OntoForge at {self.base_url}: {reason}") from error
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError as error:
            raise ApiError(f"OntoForge returned invalid JSON (HTTP {status})", status) from error
        if not isinstance(data, dict):
            raise ApiError("OntoForge returned a non-object JSON response", status)
        if status >= 400:
            raise ApiError(str(data.get("error") or f"HTTP {status}"), status)
        return data


def workflow_from_response(response: dict[str, Any]) -> dict[str, Any] | None:
    workflow = response.get("workflow")
    return workflow if isinstance(workflow, dict) else None


def panel_items(workflow: dict[str, Any], panel: str) -> list[tuple[str, dict[str, Any]]]:
    items: list[tuple[str, dict[str, Any]]] = []
    for collection in PANEL_COLLECTIONS.get(panel, ()):
        for item in workflow.get(collection) or []:
            if isinstance(item, dict):
                items.append((collection, item))
    if panel == "actions":
        if isinstance(workflow.get("last_validation"), dict) and workflow.get(
                "last_validation"):
            items.insert(0, ("last_validation", workflow["last_validation"]))
        if isinstance(workflow.get("handoff_manifest"), dict) and workflow.get(
                "handoff_manifest"):
            items.insert(1 if items else 0, (
                "handoff_manifest", workflow["handoff_manifest"]))
    return items


def evidence_title(collection: str, item: dict[str, Any]) -> str:
    if collection == "user_stories":
        return f"{item.get('actor') or '-'} -> {item.get('goal') or '-'}"
    if collection == "domain_events":
        return str(item.get("name") or item.get("text") or "-")
    if collection == "competency_questions":
        return str(item.get("question") or item.get("text") or "-")
    if collection == "validation_queries":
        return f"{item.get('language') or ''}: {item.get('question') or item.get('question_id') or '-'}"
    if collection == "model_candidates":
        return f"{item.get('kind') or 'model'} · {item.get('name') or '-'}"
    if collection == "data_sources":
        return f"{item.get('type') or 'source'} · {item.get('name') or '-'}"
    if collection == "field_mappings":
        return (
            f"{item.get('source') or '-'}.{item.get('source_field') or '-'}"
            f" -> {item.get('target') or '-'}"
        )
    if collection == "last_validation":
        return "RDF handoff static validation"
    if collection == "handoff_manifest":
        return "Report / snapshot / Neptune / RDF handoff manifest"
    return str(item.get("text") or item.get("name") or item.get("id") or "-")


def item_status(item: dict[str, Any]) -> str:
    return str(
        item.get("effective_status") or item.get("status")
        or item.get("readiness") or item.get("query_readiness") or "candidate")


def render_gate_summary(workflow: dict[str, Any]) -> str:
    lines = []
    current = workflow.get("current_stage")
    for name, gate in (workflow.get("gates") or {}).items():
        marker = ">" if name == current else " "
        status = str((gate or {}).get("status") or "fail").upper()
        lines.append(f"{marker} {status:7} {name}")
    return "\n".join(lines) or "No gate state received."


def render_gate_detail(workflow: dict[str, Any], gate_name: str) -> str:
    gate = (workflow.get("gates") or {}).get(gate_name) or {}
    lines = [f"{gate_name} · {str(gate.get('status') or 'unknown').upper()}", ""]
    for check in gate.get("checks") or []:
        mark = "PASS" if check.get("status") == "pass" else "FAIL"
        lines.append(f"[{mark}] {check.get('id') or 'check'}")
        lines.append(f"  {check.get('requirement') or ''}")
        evidence = check.get("evidence") or {}
        if evidence:
            lines.append("  evidence: " + _compact_json(evidence, 400))
    return "\n".join(lines)


def render_item_detail(collection: str, item: dict[str, Any]) -> str:
    if collection == "last_validation":
        payload = json.dumps({
            "scope": item.get("scope", "static_handoff_validation"),
            "status": item.get("status"),
            "freshness": item.get("freshness"),
            "handoff_approval": item.get("handoff_approval", "not_approved"),
            "summary": item.get("summary"),
            "counts": item.get("counts") or {},
            "checks": item.get("checks") or [],
            "report_urls": item.get("report_urls") or {},
            "limitations": item.get("limitations") or [],
            "execution_scope": {
                "sparql_executed": False,
                "shacl_engine_conformance": False,
            },
        }, ensure_ascii=False, indent=2, default=str)
        return (
            payload
            + "\n\nStructural check only: SPARQL was not executed and "
            "SHACL engine conformance was not evaluated."
        )
    if collection == "handoff_manifest":
        return json.dumps({
            "status": item.get("status"),
            "generated_at": item.get("generated_at"),
            "missing_artifacts": item.get("missing_artifacts") or [],
            "artifacts": item.get("artifacts") or {},
            "artifact_urls": item.get("artifact_urls") or {},
        }, ensure_ascii=False, indent=2, default=str)
    ordered = {
        "id": item.get("id"),
        "collection": collection,
        "status": item_status(item),
        "title": evidence_title(collection, item),
    }
    for key in (
        "priority", "severity", "category", "owner", "freshness", "stage",
        "expected_answer_shape", "question_ids", "story_ids", "source",
        "source_field", "target", "query", "merge_conflicts", "history",
    ):
        if item.get(key) not in (None, "", [], {}):
            ordered[key] = item[key]
    return json.dumps(ordered, ensure_ascii=False, indent=2, default=str)


def validation_summary(workflow: dict[str, Any]) -> str:
    validation = workflow.get("last_validation") or {}
    if not validation:
        return "Static RDF handoff validation has not been run."
    counts = validation.get("counts") or {}
    return (
        f"static={validation.get('status', 'unknown')} · "
        f"freshness={validation.get('freshness', 'unknown')} · "
        f"handoff={validation.get('handoff_approval', 'not_approved')} · "
        f"{counts.get('passed', 0)} pass / {counts.get('warnings', 0)} warning / "
        f"{counts.get('failed', 0)} fail\n"
        "Structural check only: SPARQL was not executed and SHACL engine "
        "conformance was not evaluated."
    )


def parse_changes(raw: str) -> dict[str, Any]:
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(f"changes must be valid JSON: {error.msg}") from error
    if not isinstance(parsed, dict):
        raise ValueError("changes must be a JSON object")
    return parsed


def _error_message(raw: str) -> str:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return raw.strip()
    if isinstance(payload, dict):
        return str(payload.get("error") or payload.get("detail") or "")
    return ""


def _compact_json(value: Any, limit: int) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return text if len(text) <= limit else text[:limit - 1] + "…"
