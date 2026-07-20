"""Headless Textual TUI, client, rendering, and interaction contract checks."""
from __future__ import annotations

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from textual.widgets import Button, ListView, Static, TabbedContent, TextArea

from ontology_workshop.tui import OntoForgeTui
from ontology_workshop.tui_client import (
    ApiError, WorkflowApiClient, panel_items, parse_changes,
    render_gate_detail, validation_summary,
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def sample_workflow() -> dict:
    gates = {
        "inception": {
            "status": "pass", "missing": [], "checks": [{
                "id": "inception.story_fields", "status": "pass",
                "requirement": "complete story evidence",
                "evidence": {"complete_story_ids": ["story-001"]},
            }],
        },
        "discovery": {
            "status": "fail", "missing": ["a discovery narrative"],
            "checks": [{
                "id": "discovery.narrative", "status": "fail",
                "requirement": "a discovery narrative", "evidence": {},
            }],
        },
    }
    return {
        "current_stage": "discovery", "stage_label": "Discovery",
        "active_question": "Describe one real scenario from start to finish.",
        "progress": {"passed": 1, "total": 8, "percent": 13},
        "gates": gates,
        "user_stories": [{
            "id": "story-001", "actor": "Operator", "goal": "Trace impact",
            "status": "confirmed", "priority": "high",
        }],
        "claims": [{
            "id": "claim-001", "text": "A candidate narrative",
            "status": "candidate", "stage": "discovery",
        }],
        "domain_events": [], "competency_questions": [],
        "validation_queries": [], "model_candidates": [], "data_sources": [],
        "field_mappings": [], "review_findings": [{
            "id": "finding-001", "text": "Resolve an ambiguous term",
            "category": "ambiguity", "severity": "medium", "status": "open",
        }],
        "assumptions": [], "contradictions": [], "risks": [],
        "action_items": [{
            "id": "action-001", "text": "Confirm source ownership",
            "owner": "data-team", "status": "open",
        }],
        "last_validation": {
            "status": "warning", "freshness": "current",
            "handoff_approval": "not_approved",
            "summary": "Static validation warning",
            "counts": {"passed": 8, "warnings": 1, "failed": 0},
        },
        "handoff_manifest": {
            "status": "incomplete", "missing_artifacts": ["workshop_zip"],
        },
    }


class StubClient:
    def __init__(self):
        self.base_url = "stub://local"
        self.workflow = sample_workflow()
        self.calls: list[tuple] = []

    def get_state(self):
        self.calls.append(("get",))
        return {"ok": True, "workflow": self.workflow}

    def answer(self, text, stage):
        self.calls.append(("answer", text, stage))
        return {"ok": True, "workflow": self.workflow,
                "summary": {"summary": "answer captured"}}

    def advance(self, *, force=False, reason=""):
        self.calls.append(("advance", force, reason))
        return {"ok": False, "blocked": True, "workflow": self.workflow,
                "gate": self.workflow["gates"]["discovery"]}

    def review(self):
        self.calls.append(("review",))
        return {"ok": True, "workflow": self.workflow}

    def validate(self):
        self.calls.append(("validate",))
        return {"ok": True, "workflow": self.workflow,
                "validation": self.workflow["last_validation"]}

    def decide(self, collection, item_id, action, note, changes=None, owner=""):
        self.calls.append((
            "decide", collection, item_id, action, note, changes or {}, owner))
        return {"ok": True, "workflow": self.workflow}


def test_client_contract():
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            requests.append(("GET", self.path, self.headers.get("X-OntoForge-Token"), None))
            self._reply({"ok": True, "workflow": sample_workflow()})

        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length) or b"{}")
            requests.append((
                "POST", self.path, self.headers.get("X-OntoForge-Token"), payload))
            if self.path == "/workflow/advance" and payload.get("force"):
                self._reply({"ok": False, "error": "force rejected"}, 400)
            else:
                self._reply({"ok": True, "workflow": sample_workflow()})

        def log_message(self, _format, *_args):
            return

        def _reply(self, payload, status=200):
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = WorkflowApiClient(
            f"http://127.0.0.1:{server.server_port}", "secret", timeout=2)
        state = client.get_state()
        require(state["workflow"]["current_stage"] == "discovery",
                "TUI client did not parse workflow state")
        client.answer("A narrative", "discovery")
        client.decide(
            "review_findings", "finding-001", "resolve", "Owner resolved it")
        try:
            client.advance(force=True, reason="Audited exception")
        except ApiError as error:
            require(error.status == 400 and "force rejected" in str(error),
                    "TUI client lost API error details")
        else:
            raise AssertionError("HTTP error did not raise ApiError")
        require(all(request[2] == "secret" for request in requests),
                "TUI client omitted the access token")
        answer = next(request for request in requests if request[1] == "/workflow/answer")
        require(answer[3]["stage"] == "discovery"
                and answer[3]["source"] == "terminal_tui",
                "TUI answer did not preserve current-stage provenance")
        decision = next(request for request in requests if "/decision" in request[1])
        require(decision[3]["note"] == "Owner resolved it",
                "TUI decision did not preserve its audit note")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_render_helpers():
    workflow = sample_workflow()
    review = panel_items(workflow, "review")
    actions = panel_items(workflow, "actions")
    require(review[0][0] == "review_findings",
            "review panel omitted findings")
    require([collection for collection, _item in actions[:2]] == [
        "last_validation", "handoff_manifest"],
        "actions panel omitted validation or handoff evidence")
    detail = render_gate_detail(workflow, "discovery")
    require("discovery.narrative" in detail and "FAIL" in detail,
            "gate detail omitted failed predicate evidence")
    require("SPARQL was not executed" in validation_summary(workflow)
            and "not_approved" in validation_summary(workflow),
            "TUI validation summary overclaims execution or approval")
    require(parse_changes('{"text":"revised"}') == {"text": "revised"},
            "decision change JSON was not parsed")
    for invalid in ("[]", "not-json"):
        try:
            parse_changes(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid decision changes were accepted")


def test_tui_contract():
    from pathlib import Path

    source = Path("src/ontology_workshop/tui.py").read_text(encoding="utf-8")
    client = Path("src/ontology_workshop/tui_client.py").read_text(
        encoding="utf-8")
    for panel in (
            "stories", "events", "questions", "model", "data", "review", "actions"):
        require(f'"{panel}"' in client,
                f"terminal cockpit is missing the {panel} panel contract")
    require("ForceAdvanceScreen" in source and "DecisionScreen" in source,
            "terminal cockpit is missing audited force or decision dialogs")
    require("request_in_flight" in source and "disabled = disabled" in source,
            "terminal cockpit does not lock duplicate requests")
    require("ping_interval=None" in client
            and "async for raw in websocket" in client,
            "terminal cockpit does not use one passive WebSocket stream")
    require("while True" not in client and "sleep(" not in client,
            "terminal client introduced polling or retry loops")
    require("SPARQL was not executed" in client
            and "SHACL engine conformance was not evaluated" in client,
            "terminal validation display overclaims executable validation")


async def test_headless_app():
    client = StubClient()
    app = OntoForgeTui(client)  # type: ignore[arg-type]
    async with app.run_test(size=(120, 42)) as pilot:
        await pilot.pause()
        await asyncio.sleep(0.05)
        await pilot.pause()
        require(str(app.query_one("#stage-title", Static).renderable) == "DISCOVERY",
                "TUI did not render the current stage")
        require("Describe one real scenario" in str(
            app.query_one("#active-question", Static).renderable),
            "TUI did not render the active AI question")
        require(len(app.query_one("#gate-list", ListView).children) == 2,
                "TUI did not render gate rows")
        for panel in (
                "stories", "events", "questions", "model", "data", "review", "actions"):
            app.query_one(f"#list-{panel}", ListView)
            app.query_one(f"#detail-{panel}", Static)
        require("SPARQL" in str(
            app.query_one("#detail-actions", Static).renderable),
            "TUI actions panel omitted static-validation scope")

        app.query_one("#answer-input", TextArea).load_text("A concrete scenario")
        app.query_one("#submit-answer", Button).press()
        await asyncio.sleep(0.05)
        await pilot.pause()
        require(any(call[:3] == (
            "answer", "A concrete scenario", "discovery") for call in client.calls),
            "TUI did not submit the answer for the current stage")

        app.query_one("#advance", Button).press()
        await asyncio.sleep(0.05)
        await pilot.pause()
        require("Blocked:" in str(app.query_one("#status-line", Static).renderable),
                "TUI did not expose gate-blocking reasons")

        app.query_one("#validate", Button).press()
        await asyncio.sleep(0.05)
        await pilot.pause()
        require(("validate",) in client.calls,
                "TUI did not trigger the bounded static validation")


async def test_headless_compact_app():
    app = OntoForgeTui(StubClient())  # type: ignore[arg-type]
    async with app.run_test(size=(80, 42)) as pilot:
        await pilot.pause()
        await asyncio.sleep(0.05)
        await pilot.pause()
        require(app.screen.has_class("compact"),
                "80-column TUI did not activate compact layout")

        stories = app.query_one("#list-stories", ListView)
        detail = app.query_one("#detail-stories", Static)
        require(stories.region.x == detail.region.x
                and stories.region.y < detail.region.y,
                "compact evidence list and detail were not stacked")

        work = app.query_one("#work-column")
        for button in app.query("#action-row Button"):
            require(button.region.width > 0
                    and button.region.x >= work.region.x
                    and button.region.right <= work.region.right,
                    f"80-column action {button.id} is clipped")


def main():
    test_client_contract()
    test_render_helpers()
    test_tui_contract()
    asyncio.run(test_headless_app())
    asyncio.run(test_headless_compact_app())
    print("Terminal TUI client and headless interaction checks passed")


if __name__ == "__main__":
    main()
