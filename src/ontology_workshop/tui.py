# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Textual terminal cockpit for the OntoForge AI-ODLC workflow."""
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Any, Callable

from textual import events, on, work
from textual.app import App, ComposeResult
from textual.containers import Grid, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button, Footer, Header, Input, Label, ListItem, ListView,
    Select, Static, TabbedContent, TabPane, TextArea,
)

from .tui_client import (
    DECISION_COLLECTIONS, PANEL_COLLECTIONS, ApiError, WorkflowApiClient,
    evidence_title, item_status, panel_items, parse_changes,
    render_gate_detail, render_item_detail,
    validation_summary, workflow_from_response,
)


@dataclass(slots=True)
class DecisionRequest:
    collection: str
    item_id: str
    action: str
    note: str
    changes: dict[str, Any]
    owner: str


class ForceAdvanceScreen(ModalScreen[str | None]):
    """Collect an auditable force-next reason; it never chooses a stage."""

    DEFAULT_CSS = """
    ForceAdvanceScreen { align: center middle; background: rgba(3, 8, 12, 0.78); }
    #force-card { width: 72; max-width: 94%; height: auto; padding: 1 2;
      border: tall #ffb347; background: #101820; }
    #force-card Label { margin-bottom: 1; color: #ffd089; }
    #force-reason { height: 7; border: round #40596b; }
    #force-error { height: 2; color: #ff7f8f; }
    #force-buttons { height: 3; align-horizontal: right; }
    #force-buttons Button { margin-left: 1; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="force-card"):
            yield Label("Force next stage · audited exception")
            yield Static(
                "Only the immediate next stage is allowed. The reason and bypassed "
                "gate names are retained by the server.")
            yield TextArea(id="force-reason")
            yield Static("", id="force-error")
            with Horizontal(id="force-buttons"):
                yield Button("Cancel", id="force-cancel")
                yield Button("Force next", id="force-confirm", variant="warning")

    def on_mount(self) -> None:
        self.query_one("#force-reason", TextArea).focus()

    @on(Button.Pressed, "#force-cancel")
    def cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#force-confirm")
    def confirm(self) -> None:
        reason = self.query_one("#force-reason", TextArea).text.strip()
        if len(reason) < 8:
            self.query_one("#force-error", Static).update(
                "A meaningful reason of at least 8 characters is required.")
            return
        self.dismiss(reason)


class DecisionScreen(ModalScreen[DecisionRequest | None]):
    """Collect an explicit evidence decision with note and optional correction."""

    DEFAULT_CSS = """
    DecisionScreen { align: center middle; background: rgba(3, 8, 12, 0.78); }
    #decision-card { width: 82; max-width: 96%; height: 38; padding: 1 2;
      border: tall #43d9bd; background: #101820; }
    #decision-context { height: 3; color: #a7bac8; }
    #decision-action { margin: 1 0; }
    #decision-note { height: 5; border: round #40596b; }
    #decision-changes { height: 7; border: round #40596b; }
    #decision-owner { border: round #40596b; }
    #decision-error { height: 2; color: #ff7f8f; }
    #decision-buttons { height: 3; align-horizontal: right; }
    #decision-buttons Button { margin-left: 1; }
    """

    def __init__(self, collection: str, item: dict[str, Any]):
        super().__init__()
        self.collection = collection
        self.item = item

    def compose(self) -> ComposeResult:
        actions = _decision_actions(self.collection, self.item)
        with Vertical(id="decision-card"):
            yield Label(f"Evidence decision · {self.collection}")
            yield Static(evidence_title(self.collection, self.item), id="decision-context")
            yield Select(
                [(action, action) for action in actions],
                value=actions[0], id="decision-action", allow_blank=False)
            yield Label("Decision note (required)")
            yield TextArea(id="decision-note")
            yield Label("Revised fields JSON (required for revise/update)")
            yield TextArea(id="decision-changes")
            yield Label("Linked action owner (required when accepting high severity)")
            yield Input(id="decision-owner", placeholder="owner or team")
            yield Static("", id="decision-error")
            with Horizontal(id="decision-buttons"):
                yield Button("Cancel", id="decision-cancel")
                yield Button("Apply", id="decision-confirm", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#decision-note", TextArea).focus()

    @on(Button.Pressed, "#decision-cancel")
    def cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#decision-confirm")
    def confirm(self) -> None:
        action = str(self.query_one("#decision-action", Select).value)
        note = self.query_one("#decision-note", TextArea).text.strip()
        raw_changes = self.query_one("#decision-changes", TextArea).text
        owner = self.query_one("#decision-owner", Input).value.strip()
        if not note:
            self._error("A decision note is required.")
            return
        try:
            changes = parse_changes(raw_changes)
        except ValueError as error:
            self._error(str(error))
            return
        if action in {"revise", "update"} and not changes:
            self._error(f"{action} requires revised fields JSON.")
            return
        severity = str(self.item.get("severity") or "").lower()
        if action == "accept" and severity in {"high", "critical"} and not owner:
            self._error("Accepting high/critical evidence requires a linked action owner.")
            return
        self.dismiss(DecisionRequest(
            collection=self.collection,
            item_id=str(self.item.get("id") or ""),
            action=action,
            note=note,
            changes=changes,
            owner=owner,
        ))

    def _error(self, message: str) -> None:
        self.query_one("#decision-error", Static).update(message)


class OntoForgeTui(App[None]):
    """Operator-oriented terminal surface backed by the canonical server API."""

    TITLE = "OntoForge · AI-ODLC Terminal Cockpit"
    SUB_TITLE = "gate evidence, not production readiness"
    CSS = """
    Screen { background: #081016; color: #dce8ef; }
    Header { background: #0d1c25; color: #7de3cb; }
    Footer { background: #0d1c25; }
    #shell { height: 1fr; }
    #stage-column { width: 31; min-width: 25; border-right: solid #29404f; }
    #stage-card { height: 7; padding: 1; background: #0e1a22; border-bottom: solid #29404f; }
    #stage-title { color: #7de3cb; text-style: bold; }
    #stage-progress { color: #a7bac8; }
    #gate-list { height: 1fr; padding: 1; }
    #gate-detail { height: 14; border-top: solid #29404f; padding: 1; overflow-y: auto; }
    #work-column { width: 1fr; }
    #active-question { height: auto; min-height: 4; padding: 1 2;
      background: #10232a; border-bottom: solid #2e6f68; color: #d6fff4; }
    #evidence-tabs { height: 1fr; }
    TabPane { padding: 0; }
    .panel-grid { height: 1fr; grid-size: 2 1; grid-columns: 2fr 3fr; }
    .evidence-list { height: 1fr; border-right: solid #29404f; }
    .evidence-detail { height: 1fr; padding: 1; overflow-y: auto; }
    .empty-panel { padding: 2; color: #718796; }
    #composer { height: 13; border-top: solid #29404f; padding: 1; background: #0b151d; }
    #answer-input { height: 7; border: round #40596b; }
    #action-row { height: 3; margin-top: 1; }
    #action-row Button { margin-right: 1; min-width: 12; }
    #status-line { height: 3; padding: 1 2; background: #0d1c25; color: #a7bac8; }
    #status-line.error { color: #ff7f8f; }
    #status-line.success { color: #7de3cb; }
    #status-line.busy { color: #ffd089; }
    ListItem { padding: 0 1; }
    ListItem.--highlight { background: #17333b; }
    .item-pass { color: #7de3cb; }
    .item-fail { color: #ff7f8f; }
    .item-warn { color: #ffd089; }
    .item-muted { color: #718796; }
    Button:focus, Select:focus, TextArea:focus, Input:focus { border: tall #7de3cb; }
    Screen.compact #stage-column { width: 25; }
    Screen.compact .panel-grid { grid-size: 1 2; grid-columns: 1fr; grid-rows: 1fr 1fr; }
    Screen.compact .evidence-list { border-right: none; border-bottom: solid #29404f; }
    Screen.compact #composer { height: 16; }
    Screen.compact #action-row {
      height: 6; layout: grid; grid-size: 4 2;
      grid-columns: 1fr 1fr 1fr 1fr; grid-rows: 3 3;
    }
    Screen.compact #action-row Button { min-width: 0; width: 1fr; }
    """
    BINDINGS = [
        ("ctrl+r", "refresh", "Refresh"),
        ("ctrl+enter", "submit_answer", "Submit answer"),
        ("ctrl+n", "advance", "Next stage"),
        ("ctrl+f", "force_advance", "Force next"),
        ("ctrl+d", "decide", "Decide"),
        ("ctrl+v", "validate", "Static validate"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self, client: WorkflowApiClient):
        super().__init__()
        self.client = client
        self.workflow: dict[str, Any] = {}
        self.selected_gate = "inception"
        self.panel_rows: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        self.request_in_flight = False
        self.live_connected = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="shell"):
            with Vertical(id="stage-column"):
                with Vertical(id="stage-card"):
                    yield Static("CONNECTING", id="stage-title")
                    yield Static("0 / 8 gates", id="stage-progress")
                    yield Static("manual refresh · no polling", classes="item-muted")
                yield ListView(id="gate-list")
                yield Static("Waiting for gate evidence.", id="gate-detail")
            with Vertical(id="work-column"):
                yield Static("Connecting to OntoForge…", id="active-question")
                with TabbedContent(id="evidence-tabs"):
                    for panel in PANEL_COLLECTIONS:
                        with TabPane(panel.title(), id=f"tab-{panel}"):
                            with Grid(classes="panel-grid"):
                                yield ListView(
                                    id=f"list-{panel}", classes="evidence-list")
                                yield Static(
                                    f"No {panel} evidence selected.",
                                    id=f"detail-{panel}", classes="evidence-detail")
                with Vertical(id="composer"):
                    yield TextArea(id="answer-input")
                    with Horizontal(id="action-row"):
                        yield Button("Submit", id="submit-answer", variant="primary")
                        yield Button("Next", id="advance")
                        yield Button("Force", id="force", variant="warning")
                        yield Button("Review", id="review")
                        yield Button("Decide", id="decide")
                        yield Button("Static RDF", id="validate")
                        yield Button("Refresh", id="refresh")
                yield Static("Starting…", id="status-line")
        yield Footer()

    def on_mount(self) -> None:
        self.screen.set_class(self.size.width < 92, "compact")
        self._set_status(
            f"Connecting to {self.client.base_url} · one live stream · no polling/retry",
            "busy")
        self.action_refresh()
        if self.client.base_url.startswith(("http://", "https://")):
            self._listen_for_updates()

    def on_resize(self, event: events.Resize) -> None:
        self.screen.set_class(event.size.width < 92, "compact")

    @work(exclusive=True, group="live")
    async def _listen_for_updates(self) -> None:
        try:
            async for workflow in self.client.workflow_updates():
                self.live_connected = True
                self.workflow = workflow
                self._render_workflow()
        except (ApiError, OSError) as error:
            self.live_connected = False
            self._set_status(
                f"Live stream unavailable: {error}. Use Refresh; no automatic retry.",
                "error")
        else:
            if self.live_connected:
                self.live_connected = False
                self._set_status(
                    "Live stream closed. Use Refresh or restart the TUI; no automatic retry.",
                    "error")

    @work(thread=True, exclusive=True, group="api")
    def _run_request(self, label: str,
                     operation: Callable[[], dict[str, Any]]) -> None:
        try:
            response = operation()
        except (ApiError, ValueError) as error:
            self.call_from_thread(self._request_failed, str(error))
        except Exception as error:  # noqa: BLE001
            self.call_from_thread(
                self._request_failed, f"Unexpected TUI request failure: {error}")
        else:
            self.call_from_thread(self._request_succeeded, label, response)

    def _start_request(self, label: str,
                       operation: Callable[[], dict[str, Any]]) -> None:
        if self.request_in_flight:
            self._set_status("Another request is already in progress.", "error")
            return
        self.request_in_flight = True
        self._set_buttons_disabled(True)
        self._set_status(label, "busy")
        self._run_request(label, operation)

    def _request_failed(self, message: str) -> None:
        self.request_in_flight = False
        self._set_buttons_disabled(False)
        self._set_status(message, "error")

    def _request_succeeded(self, label: str, response: dict[str, Any]) -> None:
        self.request_in_flight = False
        self._set_buttons_disabled(False)
        workflow = workflow_from_response(response)
        if workflow is not None:
            self.workflow = workflow
            self._render_workflow()
        if response.get("blocked"):
            gate = response.get("gate") or {}
            self._set_status(
                "Blocked: " + "; ".join(gate.get("missing") or ["gate evidence missing"]),
                "error")
            return
        validation = response.get("validation") or {}
        summary = (
            validation.get("summary")
            or (response.get("summary") or {}).get("summary")
            or response.get("error")
            or label.replace("…", "") + " complete"
        )
        self._set_status(str(summary), "success")

    def _render_workflow(self) -> None:
        stage = str(self.workflow.get("current_stage") or "inception")
        progress = self.workflow.get("progress") or {}
        self.query_one("#stage-title", Static).update(
            str(self.workflow.get("stage_label") or stage).upper())
        self.query_one("#stage-progress", Static).update(
            f"{progress.get('passed', 0)} / {progress.get('total', 8)} gates · "
            f"{progress.get('percent', 0)}% · "
            f"{'LIVE' if self.live_connected else 'MANUAL'}")
        self.query_one("#active-question", Static).update(
            "NEXT QUESTION\n" + str(self.workflow.get("active_question") or "-"))
        if self.selected_gate not in (self.workflow.get("gates") or {}):
            self.selected_gate = stage
        self._render_gates()
        self._render_panels()

    def _render_gates(self) -> None:
        view = self.query_one("#gate-list", ListView)
        view.clear()
        rows = []
        for name, gate in (self.workflow.get("gates") or {}).items():
            status = str((gate or {}).get("status") or "fail")
            style = "item-pass" if status == "pass" else (
                "item-warn" if status == "partial" else "item-fail")
            rows.append(ListItem(
                Label(f"{status.upper():7} {name}", classes=style), name=name))
        if rows:
            view.extend(rows)
        self.query_one("#gate-detail", Static).update(
            render_gate_detail(self.workflow, self.selected_gate))

    def _render_panels(self) -> None:
        for panel in PANEL_COLLECTIONS:
            rows = panel_items(self.workflow, panel)
            self.panel_rows[panel] = rows
            view = self.query_one(f"#list-{panel}", ListView)
            view.clear()
            entries = []
            for index, (collection, item) in enumerate(rows):
                status = item_status(item)
                style = _status_class(status)
                title = _one_line(evidence_title(collection, item), 72)
                entries.append(ListItem(
                    Label(f"{status:12} {title}", classes=style),
                    name=str(index)))
            if entries:
                view.extend(entries)
                detail = render_item_detail(rows[0][0], rows[0][1])
                if panel == "actions":
                    detail += "\n\n" + validation_summary(self.workflow)
                self.query_one(f"#detail-{panel}", Static).update(detail)
            else:
                self.query_one(f"#detail-{panel}", Static).update(
                    f"No {panel} evidence. Use the current-stage answer box or API.")
        actions_detail = self.query_one("#detail-actions", Static)
        if not self.panel_rows.get("actions"):
            actions_detail.update(validation_summary(self.workflow))

    @on(ListView.Selected, "#gate-list")
    def gate_selected(self, event: ListView.Selected) -> None:
        if event.item.name:
            self.selected_gate = event.item.name
            self.query_one("#gate-detail", Static).update(
                render_gate_detail(self.workflow, self.selected_gate))

    @on(ListView.Highlighted, ".evidence-list")
    def evidence_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item is None or event.item.name is None:
            return
        panel = event.list_view.id.removeprefix("list-")
        rows = self.panel_rows.get(panel, [])
        try:
            collection, item = rows[int(event.item.name)]
        except (ValueError, IndexError):
            return
        self.query_one(f"#detail-{panel}", Static).update(
            render_item_detail(collection, item))

    @on(Button.Pressed, "#refresh")
    def refresh_pressed(self) -> None:
        self.action_refresh()

    def action_refresh(self) -> None:
        self._start_request("Refreshing workflow…", self.client.get_state)

    @on(Button.Pressed, "#submit-answer")
    def submit_pressed(self) -> None:
        self.action_submit_answer()

    def action_submit_answer(self) -> None:
        text = self.query_one("#answer-input", TextArea).text.strip()
        stage = str(self.workflow.get("current_stage") or "")
        if not text or not stage:
            self._set_status("Connect first and enter a current-stage answer.", "error")
            return
        self.query_one("#answer-input", TextArea).load_text("")
        self._start_request(
            "Submitting current-stage answer…",
            lambda: self.client.answer(text, stage))

    @on(Button.Pressed, "#advance")
    def advance_pressed(self) -> None:
        self.action_advance()

    def action_advance(self) -> None:
        self._start_request("Advancing one stage…", self.client.advance)

    @on(Button.Pressed, "#force")
    def force_pressed(self) -> None:
        self.action_force_advance()

    def action_force_advance(self) -> None:
        if self.request_in_flight:
            self._set_status("Another request is already in progress.", "error")
            return
        self.push_screen(ForceAdvanceScreen(), self._force_reason_received)

    def _force_reason_received(self, reason: str | None) -> None:
        if reason:
            self._start_request(
                "Forcing audited next-stage transition…",
                lambda: self.client.advance(force=True, reason=reason))

    @on(Button.Pressed, "#review")
    def review_pressed(self) -> None:
        self._start_request("Running one bounded adversarial review…", self.client.review)

    @on(Button.Pressed, "#validate")
    def validate_pressed(self) -> None:
        self.action_validate()

    def action_validate(self) -> None:
        self._start_request(
            "Running one static RDF handoff validation…", self.client.validate)

    @on(Button.Pressed, "#decide")
    def decide_pressed(self) -> None:
        self.action_decide()

    def action_decide(self) -> None:
        panel = self.query_one("#evidence-tabs", TabbedContent).active.removeprefix("tab-")
        view = self.query_one(f"#list-{panel}", ListView)
        rows = self.panel_rows.get(panel, [])
        if view.index is None or not rows:
            self._set_status("Select a reviewable evidence item first.", "error")
            return
        collection, item = rows[view.index]
        if collection not in DECISION_COLLECTIONS:
            self._set_status(f"{collection} does not support review decisions.", "error")
            return
        self.push_screen(
            DecisionScreen(collection, item), self._decision_received)

    def _decision_received(self, request: DecisionRequest | None) -> None:
        if request is None:
            return
        self._start_request(
            f"Applying {request.action} decision…",
            lambda: self.client.decide(
                request.collection, request.item_id, request.action,
                request.note, request.changes, request.owner))

    def _set_buttons_disabled(self, disabled: bool) -> None:
        for button in self.query("#action-row Button"):
            button.disabled = disabled

    def _set_status(self, message: str, state: str = "") -> None:
        widget = self.query_one("#status-line", Static)
        widget.set_classes(state)
        widget.update(message)


def _decision_actions(collection: str, item: dict[str, Any]) -> list[str]:
    terminal = str(item.get("status") or "") in {
        "resolved", "rejected", "out_of_scope"
    }
    if terminal:
        return ["update", "revise"]
    if collection == "action_items":
        return ["confirm", "start", "resolve", "reject", "revise"]
    if collection in {"claims", "review_findings"}:
        return ["confirm", "reject", "revise", "resolve"]
    return ["confirm", "accept", "reject", "revise", "resolve"]


def _status_class(status: str) -> str:
    value = status.lower()
    if value in {"pass", "confirmed", "accepted", "verified", "available", "resolved"}:
        return "item-pass"
    if value in {"fail", "failed", "conflicting", "missing", "needs_fix"}:
        return "item-fail"
    if value in {"partial", "warning", "stale", "candidate", "assumed", "open"}:
        return "item-warn"
    return "item-muted"


def _one_line(value: str, limit: int) -> str:
    clean = " ".join(value.split())
    return clean if len(clean) <= limit else clean[:limit - 1] + "…"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ontology_workshop.tui",
        description="OntoForge AI-ODLC terminal cockpit")
    parser.add_argument(
        "--url", default=os.environ.get("ONTOFORGE_URL", "http://127.0.0.1:8000"),
        help="OntoForge server URL (default: %(default)s)")
    parser.add_argument(
        "--token", default=os.environ.get("ONTOFORGE_TOKEN"),
        help="optional API token; defaults to ONTOFORGE_TOKEN")
    parser.add_argument(
        "--timeout", type=float, default=15.0,
        help="per-request timeout in seconds (default: %(default)s)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        client = WorkflowApiClient(args.url, args.token, args.timeout)
    except ValueError as error:
        build_parser().error(str(error))
    OntoForgeTui(client).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
