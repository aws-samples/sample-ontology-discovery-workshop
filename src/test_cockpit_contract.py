"""Browser cockpit structure, accessibility, and interaction contract checks."""
from pathlib import Path


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    html = Path("static/index.html").read_text(encoding="utf-8")

    for panel in ("stories", "events", "questions", "model", "data", "review", "actions"):
        require(f"{panel}:" in html, f"missing {panel} cockpit panel")
    require("wfStageSelect" not in html, "editable stage selector still exists")
    require("id=\"forceDialog\"" in html and "id=\"forceReason\"" in html,
            "force-reason dialog is missing")
    require("id=\"decisionDialog\"" in html and "submitDecision" in html,
            "review decision dialog is missing")
    require("id=\"decisionNote\" required" in html
            and "A decision note is required." in html,
            "cockpit decisions can be submitted without justification")
    require("action==='update'||action==='revise'" in html,
            "revise action does not require revised fields in the cockpit")
    require("aria-live=\"polite\"" in html and "role=\"status\"" in html,
            "live workflow status accessibility metadata is missing")
    require("role=\"tablist\"" in html and "aria-selected" in html,
            "evidence panel tab semantics are missing")
    require("ArrowRight" in html and "aria-controls=\"wfDetail\"" in html,
            "evidence tabs do not expose keyboard navigation and tabpanel linkage")
    require("@media (max-width:1100px)" in html and "@media (max-width:720px)" in html,
            "responsive layout rules are missing")
    require("pendingRequests" in html and "button.disabled=true" in html,
            "request locking or duplicate prevention is missing")
    require("catch(error)" in html and "setWorkflowStatus(error.message" in html,
            "request error handling is missing")
    require("report_urls" in html and "validation-checks" in html,
            "validation check drill-down or report links are missing")
    require("handoff artifact manifest" in html and "artifact_urls" in html,
            "handoff artifact manifest or download links are missing")
    for state in ("wf-confirmed", "wf-assumed", "wf-conflicting", "wf-missing"):
        require(state in html, f"graph uncertainty class {state} is missing")
    require("cy.elements().forEach" in html,
            "graph uncertainty states are not applied to both nodes and edges")
    require("['accepted','verified','available'].includes(status)?'confirmed'" in html,
            "positive readiness can erase confirmed graph-state styling")
    require("JSON.stringify(c.evidence)" in html,
            "gate drill-down does not expose predicate evidence details")
    require("item.effective_status||item.status" in html,
            "query cards do not prefer computed evidence freshness")
    require("SPARQL was not executed" in html
            and "SHACL engine conformance was not evaluated" in html,
            "static validation scope is ambiguous in the cockpit")
    require("Static RDF handoff check" in html
            and "Validate RDF/SHACL" not in html,
            "validation action label implies live SPARQL/SHACL execution")
    require("handoff_approval" in html and "fingerprint matches the packaged bundle" in html,
            "cockpit does not distinguish validation pass from current handoff approval")
    require("pendingRequests.has(key)" in html and "finally{pendingRequests.delete(key)" in html,
            "request guard is not released deterministically")

    print("Browser cockpit contract checks passed")


if __name__ == "__main__":
    main()
