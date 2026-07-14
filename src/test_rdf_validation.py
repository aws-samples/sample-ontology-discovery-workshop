"""Bounded RDF/SPARQL/SHACL static validation checks."""
from __future__ import annotations

import os
import tempfile

from ontology_workshop import rdf_export, rdf_validation, report
from ontology_workshop.graph import EntityType, OntologyGraph, RelationType
from ontology_workshop.workflow import WorkflowState


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def _graph(root: str) -> OntologyGraph:
    graph = OntologyGraph(os.path.join(root, "validation.kuzu"), fresh=True)
    assert graph.add_entity_type(EntityType(
        "Product", {"id": "STRING", "name": "STRING"}, "id"))["ok"]
    assert graph.add_entity_type(EntityType(
        "SupplierLot", {"id": "STRING", "supplier": "STRING"}, "id"))["ok"]
    assert graph.add_relation_type(RelationType(
        "USES_LOT", "Product", "SupplierLot", "N:M",
        {"confidence": "DOUBLE"}))["ok"]
    assert graph.add_instance("Product", {"id": "P1", "name": "Widget"})["ok"]
    assert graph.add_instance(
        "SupplierLot", {"id": "L1", "supplier": "ACME"})["ok"]
    assert graph.add_edge(
        "USES_LOT", "P1", "L1", {"confidence": 0.9})["ok"]
    return graph


def main():
    os.makedirs("./exports", exist_ok=True)
    root = tempfile.mkdtemp(prefix="ontoforge-validation-")
    outdir = tempfile.mkdtemp(prefix="rdf-validation-", dir="./exports")
    graph = _graph(root)
    workflow = {
        "competency_questions": [{
            "question": "Which supplier lots are used by each product?",
            "sparql_candidate": (
                "SELECT ?product ?lot WHERE { "
                "?product :USES_LOT ?lot . } LIMIT 25"
            ),
        }],
        "validation_queries": [{
            "id": "query-001",
            "language": "SPARQL",
            "question": "Which supplier lots are used by each product?",
            "query": "SELECT ?product ?lot WHERE { ?product :USES_LOT ?lot . }",
        }],
    }

    bundle = rdf_export.export_all(
        graph, outdir, workflow, "https://example.com/validation/")
    valid = rdf_validation.validate_bundle(bundle, graph.tbox())
    require(valid["status"] == "pass", valid["summary"])
    require(len(valid["bundle_digest"]) == 64, "bundle digest is missing")
    require(valid["counts"]["failed"] == 0, "valid bundle should not fail")
    require(valid["sparql"]["query_count"] >= 1, "SPARQL seeds not detected")
    require(valid["sparql"]["executed"] is False,
            "static validation must not claim SPARQL execution")
    require(valid["shacl"]["conforms"] is None,
            "static validation must not claim SHACL conformance")
    reports = rdf_validation.write_reports(valid, outdir)
    require(all(os.path.exists(path) for path in reports.values()),
            "validation reports were not written")

    with open(bundle["sparql"], encoding="utf-8") as handle:
        upper_sparql = handle.read()
    with open(bundle["sparql"], "w", encoding="utf-8") as handle:
        handle.write(upper_sparql.replace("SELECT", "select"))
    lower_case = rdf_validation.validate_bundle(bundle, graph.tbox())
    require(lower_case["sparql"]["status"] == "pass",
            "SPARQL keywords should be case-insensitive")

    bundle = rdf_export.export_all(
        graph, outdir, workflow, "https://example.com/validation/")
    with open(bundle["sparql"], "a", encoding="utf-8") as handle:
        handle.write("\nINSERT DATA { :bad :write :operation . }\n")
    bad_sparql = rdf_validation.validate_bundle(bundle, graph.tbox())
    require(bad_sparql["status"] == "fail", "SPARQL Update should fail")
    require(any(item["id"] == "sparql.read_only" and item["status"] == "fail"
                for item in bad_sparql["checks"]),
            "SPARQL read-only failure was not reported")

    bundle = rdf_export.export_all(
        graph, outdir, workflow, "https://example.com/validation/")
    with open(bundle["shacl"], encoding="utf-8") as handle:
        shapes = handle.read()
    with open(bundle["shacl"], "w", encoding="utf-8") as handle:
        handle.write(shapes.replace("    sh:minCount 1 ;\n", "", 1))
    bad_shacl = rdf_validation.validate_bundle(bundle, graph.tbox())
    require(bad_shacl["status"] == "fail", "missing PK constraint should fail")
    require(bad_shacl["shacl"]["engine_executed"] is False,
            "static SHACL check must not claim engine execution")

    bundle = rdf_export.export_all(
        graph, outdir, workflow, "https://example.com/validation/")
    os.remove(bundle["mapping"])
    missing = rdf_validation.validate_bundle(bundle, graph.tbox())
    require(missing["status"] == "fail", "missing artifact should fail")

    state = WorkflowState({"validation_queries": workflow["validation_queries"]})
    first = state.record_static_validation(bad_sparql)
    second = state.record_static_validation(bad_sparql)
    require(first["latest_only"] and second["latest_only"],
            "validation history must stay bounded")
    require(len(state.data["review_findings"]) == 1,
            "failed reruns must not duplicate findings")
    require(len(state.data["action_items"]) == 1,
            "failed reruns must not duplicate action items")
    require(state.data["validation_queries"][0]["readiness"] == "needs_fix",
            "failed SPARQL validation should mark query needs_fix")
    state.record_static_validation(valid)
    require(state.data["validation_queries"][0]["readiness"] == "validated_static",
            "passing static validation should update SPARQL readiness")
    require(state.data["action_items"][0]["status"] == "resolved",
            "passing rerun should resolve the generated action")
    require(state.data["last_validation"]["status"] == "pass",
            "only the latest validation result should be retained")

    source = rdf_validation.source_fingerprint(
        graph.tbox(), graph.snapshot(), state.data,
        "https://example.com/validation/")
    fresh_result = dict(valid, source_fingerprint=source, freshness="current")
    state.record_static_validation(fresh_result)
    fresh = state.to_dict({"rdf_validation_source_fingerprint": source})
    stale = state.to_dict({"rdf_validation_source_fingerprint": "changed"})
    require(fresh["last_validation"]["freshness"] == "current",
            "matching source fingerprint should be current")
    require(stale["last_validation"]["freshness"] == "stale",
            "changed source fingerprint should mark validation stale")
    rendered = report.render_report_md(graph, workflow=stale)
    require("Latest RDF Handoff Static Validation" in rendered,
            "workshop report should include validation evidence")
    require("Source freshness: **stale**" in rendered,
            "workshop report should warn about stale validation")

    failed_gate_state = WorkflowState({
        "action_items": [{
            "text": "Resolve validation failures.",
            "source": "static_handoff_validation",
            "status": "open",
        }],
        "last_validation": fresh_result,
    })
    gate = failed_gate_state.gates({
        "verified_count": 1,
        "rdf_validation_source_fingerprint": source,
    })["validation_handoff"]
    require(gate["status"] != "pass",
            "an unresolved validation action must block handoff")

    print("RDF static validation checks passed")


if __name__ == "__main__":
    main()
