"""End-to-end report package manifest and freshness checks."""
from __future__ import annotations

import asyncio
import os
import tempfile

from ontology_workshop.graph import EntityType, OntologyGraph, RelationType
from ontology_workshop import server


def require(condition, message):
    if not condition:
        raise AssertionError(message)


async def main_async():
    root = tempfile.mkdtemp(prefix="ontoforge-handoff-")
    report_dir = os.path.join("./exports", os.path.basename(root))
    server.REPORT_DIR = report_dir
    server.g = OntologyGraph(os.path.join(root, "handoff.kuzu"), fresh=True)
    server.workflow.reset()
    server.verified_queries.clear()
    server.narrations.clear()
    server.clients.clear()
    server.SESSION_PATH = os.path.join(report_dir, "session.json")

    require(server.g.add_entity_type(EntityType(
        "Product", {"id": "STRING"}, "id"))["ok"], "Product add failed")
    require(server.g.add_entity_type(EntityType(
        "Lot", {"id": "STRING"}, "id"))["ok"], "Lot add failed")
    require(server.g.add_relation_type(RelationType(
        "USES", "Product", "Lot", "N:M", {}))["ok"], "relation add failed")

    result = await server.export_report(server.ReportIn(title="Handoff manifest test"))
    manifest = result.get("handoff_manifest") or {}
    artifacts = manifest.get("artifacts") or {}
    urls = manifest.get("artifact_urls") or {}
    required = {
        "report_markdown", "report_html", "snapshot_html", "snapshot_json",
        "neptune_cypher", "neptune_nodes", "neptune_edges", "rdf_ontology",
        "rdf_instances", "rdf_jsonld", "rdf_shacl", "rdf_sparql",
        "rdf_mapping", "rdf_neptune_handoff", "workshop_zip",
    }
    require(required <= set(artifacts),
            f"handoff manifest missing artifacts: {sorted(required - set(artifacts))}")
    require(all(os.path.isfile(path) and os.path.getsize(path) > 0
                for path in artifacts.values()),
            "handoff manifest contains missing or empty files")
    require(set(urls) == set(artifacts) and all(url.startswith("/files/")
                                                for url in urls.values()),
            "handoff manifest did not expose safe report-file URLs")
    require(manifest.get("rdf_source_fingerprint")
            == server._workflow_context()["handoff_rdf_source_fingerprint"],
            "handoff manifest did not bind the packaged RDF inputs")

    state = server._workflow_payload()
    gate = state["gates"]["validation_handoff"]
    artifact_check = next(
        check for check in gate["checks"] if check["id"] == "handoff.artifacts")
    require(artifact_check["status"] == "pass",
            f"fresh handoff manifest did not pass: {artifact_check}")

    deleted_path = artifacts["rdf_mapping"]
    os.remove(deleted_path)
    missing = server._workflow_payload()["gates"]["validation_handoff"]
    missing_check = next(
        check for check in missing["checks"] if check["id"] == "handoff.artifacts")
    require(missing_check["status"] == "fail"
            and missing_check["evidence"]["files_valid"] is False,
            "deleted handoff artifact did not close the gate")
    # Regenerate before the separate stale-fingerprint assertion.
    result = await server.export_report(server.ReportIn(title="Handoff manifest test"))
    require(os.path.isfile(result["handoff_manifest"]["artifacts"]["rdf_mapping"]),
            "report regeneration did not restore the deleted artifact")

    server.workflow.add_item("claims", "claim", {
        "text": "Evidence changed after the handoff package was generated.",
        "stage": "inception",
    })
    stale = server._workflow_payload()["gates"]["validation_handoff"]
    stale_check = next(
        check for check in stale["checks"] if check["id"] == "handoff.artifacts")
    require(stale_check["status"] == "fail"
            and stale_check["evidence"]["freshness"] == "stale",
            "handoff manifest did not become stale after workflow evidence changed")

    # A pass for base IRI A cannot approve a report/RDF package generated for B.
    server.workflow.reset()
    validation = await server.workflow_validate(server.WorkflowValidateIn(
        outdir=os.path.join(report_dir, "validation-a"),
        base_iri="https://example.com/base-a/"))
    require(validation["validation"]["status"] == "pass",
            "test precondition: static RDF validation did not pass")
    await server.export_report(server.ReportIn(
        title="Different RDF base",
        rdf_base_iri="https://example.com/base-b/"))
    mismatched = server._workflow_payload()["gates"]["validation_handoff"]
    validation_check = next(
        check for check in mismatched["checks"]
        if check["id"] == "handoff.static_validation")
    require(validation_check["status"] == "fail"
            and validation_check["evidence"]["bundle_aligned"] is False,
            "validation for one RDF base IRI approved a different handoff bundle")
    require(server._workflow_payload()["last_validation"]["handoff_approval"]
            == "not_approved",
            "mismatched RDF validation remained approved in the workflow payload")

    print("Handoff manifest checks passed")


if __name__ == "__main__":
    asyncio.run(main_async())
