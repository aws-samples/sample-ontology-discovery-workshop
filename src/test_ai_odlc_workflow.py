"""AI-ODLC workflow unit checks."""
from ontology_workshop.workflow import WorkflowState


def assert_equal(actual, expected):
    if actual != expected:
        raise AssertionError(f"expected {expected!r}, got {actual!r}")


def main():
    wf = WorkflowState()
    state = wf.to_dict({"graph": {}, "verified_count": 0})
    assert_equal(state["current_stage"], "inception")
    assert_equal(state["gates"]["inception"]["status"], "fail")

    wf.add_item("user_stories", "story", {
        "actor": "Quality manager",
        "goal": "Trace product defects faster",
        "decision": "Identify supplier lots and production lines",
        "success_metric": "Reduce RCA time",
        "priority": "high",
    })
    wf.record_answer("A defect is discovered during inspection.", "discovery")
    wf.add_item("domain_events", "event", {
        "name": "DefectDetected",
        "trigger": "Inspection result",
        "state_change": "Product moves to investigation",
    })
    wf.add_item("competency_questions", "question", {
        "question": "Which supplier lots are connected to defective products?",
        "expected_answer_shape": ["Product", "SupplierLot"],
        "priority": "high",
    })
    wf.add_item("model_candidates", "model", {
        "kind": "entity",
        "name": "Product",
        "rationale": "Product anchors defect traceability.",
    })
    wf.add_item("data_sources", "source", {
        "name": "quality_inspection",
        "type": "table",
        "owner": "quality_team",
    })
    wf.add_item("field_mappings", "mapping", {
        "source": "quality_inspection",
        "source_field": "product_id",
        "target": "Product.id",
        "status": "available",
    })
    wf.add_review(
        risks=[{"text": "Supplier lot causality may require validation."}],
        action_items=[{"text": "Confirm lot keys with data owner.", "owner": "customer"}],
    )
    complete = wf.to_dict({
        "graph": {"entities": 1, "relations": 1, "nodes": 0, "edges": 0},
        "verified_count": 1,
    })
    for name, gate in complete["gates"].items():
        assert_equal(gate["status"], "pass")
    assert_equal(complete["progress"]["percent"], 100)

    exported = complete.copy()
    loaded = WorkflowState(exported).to_dict({
        "graph": {"entities": 1, "relations": 1, "nodes": 0, "edges": 0},
        "verified_count": 1,
    })
    assert_equal(len(loaded["user_stories"]), 1)
    assert_equal(loaded["progress"]["percent"], 100)

    guided = WorkflowState()
    answer = """
    {
      "user_story": {
        "actor": "Quality manager",
        "goal": "Trace product defect causes faster",
        "decision": "Identify affected supplier lots",
        "success_metric": "Reduce RCA time",
        "priority": "high"
      },
      "competency_questions": [
        {
          "question": "Which Product instances are connected to SupplierLot instances?",
          "expected_answer_shape": ["Product", "SupplierLot"],
          "priority": "high"
        }
      ],
      "tables": [
        {
          "name": "quality_inspection",
          "fields": {"product_id": "STRING", "supplier_lot_id": "STRING"},
          "mappings": {
            "product_id": "Product.id",
            "supplier_lot_id": "SupplierLot.id"
          }
        }
      ],
      "rdf_decisions": [
        {"topic": "base_iri", "value": "https://example.com/quality/"}
      ]
    }
    """
    result = guided.process_answer(
        answer, "inception", context={
            "graph": {"entities": 2, "relations": 1},
            "entity_names": ["Product", "SupplierLot"],
            "verified_count": 0,
        })
    assert_equal(result["claim"]["stage"], "inception")
    enriched = guided.to_dict({
        "graph": {"entities": 2, "relations": 1, "nodes": 0, "edges": 0},
        "entity_names": ["Product", "SupplierLot"],
        "verified_count": 0,
    })
    assert_equal(len(enriched["user_stories"]), 1)
    assert_equal(len(enriched["competency_questions"]), 1)
    assert_equal(len(enriched["data_sources"]), 1)
    assert_equal(len(enriched["field_mappings"]), 2)
    assert_equal(len(enriched["rdf_decisions"]), 1)
    assert_equal(len(enriched["validation_queries"]), 2)
    if "MATCH (a:Product)" not in enriched["validation_queries"][0]["query"]:
        raise AssertionError("openCypher query seed should use expected answer shape")
    guided.record_query_verification(
        "Which Product instances are connected to SupplierLot instances?",
        enriched["validation_queries"][0]["query"],
        {"ok": True, "count": 3, "columns": ["a", "r", "b"]},
    )
    verified = guided.to_dict({
        "graph": {"entities": 2, "relations": 1, "nodes": 0, "edges": 0},
        "entity_names": ["Product", "SupplierLot"],
        "verified_count": 1,
    })
    assert_equal(verified["validation_queries"][0]["status"], "verified")
    assert_equal(verified["competency_questions"][0]["query_readiness"], "verified")

    review = guided.generate_review({
        "graph": {"entities": 2, "relations": 1, "nodes": 0, "edges": 0},
        "verified_count": 0,
    })
    if not review["review_findings"] or not review["action_items"]:
        raise AssertionError("generated adversarial review should create findings and actions")
    print("AI-ODLC workflow checks passed")


if __name__ == "__main__":
    main()
