"""Direct FastAPI workflow endpoint contract checks without an HTTP test client."""
from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import tempfile

from fastapi.responses import JSONResponse

from ontology_workshop.graph import OntologyGraph
from ontology_workshop import server


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def payload(response):
    if isinstance(response, JSONResponse):
        return json.loads(response.body.decode("utf-8"))
    return response


async def main_async():
    root = tempfile.mkdtemp(prefix="ontoforge-workflow-api-")
    server.g = OntologyGraph(os.path.join(root, "api.kuzu"), fresh=True)
    server.workflow.reset()
    server.verified_queries.clear()
    server.narrations.clear()
    server.clients.clear()
    server._autosave_session = lambda: None

    audit = io.StringIO()
    logger = logging.getLogger("ontology_workshop.audit")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler(audit))

    rejected = await server.workflow_answer(server.WorkflowAnswerIn(
        text="skip", stage="validation_handoff"))
    require(rejected.status_code == 400, "answer-stage bypass was not HTTP 400")
    require(server.workflow.data["current_stage"] == "inception",
            "rejected answer changed current stage")

    extracted = payload(await server.workflow_answer(server.WorkflowAnswerIn(
        text="Capture comprehensive evidence early.", stage="inception",
        extracted={"user_stories": [{
            "actor": "Owner", "goal": "Decide", "decision": "Choose",
            "success_metric": "One hour", "scope": "One-day scenario",
            "priority": "high", "stage": "validation_handoff",
        }]})))
    require(extracted["added"]["user_stories"][0]["stage"] == "inception",
            "answer API accepted forged future-stage evidence provenance")

    started = await server.workflow_start(server.WorkflowStartIn(
        language="en", scope="One-day API contract scope"))
    require(started["workflow"]["gates"]["model_synthesis"]["evidence"]["entities"] == 0,
            "workflow/start response did not use the current graph context")

    no_reason = await server.workflow_advance(server.WorkflowAdvanceIn(force=True))
    require(no_reason.status_code == 400, "reason-less force was not HTTP 400")

    skipped = await server.workflow_advance(server.WorkflowAdvanceIn(
        stage="model_synthesis", force=True, reason="Explicit scope exception"))
    require(skipped.status_code == 400, "skipped-stage force was not HTTP 400")

    forced = payload(await server.workflow_advance(server.WorkflowAdvanceIn(
        force=True, reason="Explicit facilitator scope exception", actor="facilitator")))
    require(forced["ok"] and forced["stage"] == "discovery",
            "valid force did not advance exactly one stage")
    require(forced["transition"]["reason"] == "Explicit facilitator scope exception",
            "force reason was not returned")
    require("workflow_advanced" in audit.getvalue()
            and "Explicit facilitator scope exception" in audit.getvalue(),
            "force reason was not written to the audit stream")

    risk = server.workflow.add_item("risks", "risk", {
        "text": "Sensitive source approval is missing.",
        "severity": "high", "status": "open",
    })
    missing_action = await server.workflow_item_decision(
        "risks", risk["id"], server.WorkflowItemDecisionIn(
            action="accept", note="Accept only with a tracked follow-up"))
    require(missing_action.status_code == 400,
            "high-risk acceptance without an owned action was not rejected")

    missing_note = await server.workflow_item_decision(
        "risks", risk["id"], server.WorkflowItemDecisionIn(action="reject"))
    require(missing_note.status_code == 400,
            "unjustified review decision was not rejected")

    accepted = payload(await server.workflow_item_decision(
        "risks", risk["id"], server.WorkflowItemDecisionIn(
            action="accept", note="Track in technical handoff",
            linked_action={"text": "Obtain privacy approval", "owner": "privacy-team"})))
    require(accepted["item"]["status"] == "accepted",
            "review decision endpoint did not accept the risk")
    require(accepted["item"]["history"], "decision endpoint lost item history")
    require(accepted["item"]["linked_action_ids"],
            "decision endpoint lost its linked action")

    listed = await server.workflow_items("risks")
    require(listed["items"][0]["id"] == risk["id"],
            "workflow item listing did not return the risk")

    before = len(server.verified_queries)
    arbitrary = payload(await server.run_query(server.QueryIn(
        question="Arbitrary health check", cypher="RETURN 1 AS ok")))
    require(arbitrary["ok"], "ad-hoc read-only query should still execute")
    require(arbitrary["workflow_verification"]["updated"] == 0,
            "ad-hoc query was attached to a competency seed")
    require(arbitrary["workflow_verification"].get("qualified", 0) == 0,
            "ad-hoc query was returned as qualified handoff evidence")
    require(len(server.verified_queries) == before,
            "ad-hoc query was promoted to report verification evidence")
    require(server._current_verified_queries() == [],
            "legacy successful-query history leaked into current handoff evidence")

    print("Workflow API contract checks passed")


if __name__ == "__main__":
    asyncio.run(main_async())
