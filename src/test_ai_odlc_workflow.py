"""AI-ODLC quality-gate and adversarial-bypass regression checks."""
from __future__ import annotations

from ontology_workshop.workflow import STAGES, WorkflowState, _query_covers_answer_shape


GRAPH = {
    "graph": {"entities": 2, "relations": 1, "nodes": 2, "edges": 1},
    "entity_names": ["Product", "SupplierLot"],
    "relation_names": ["USES_LOT"],
    "tbox": {
        "entities": {
            "Product": {"properties": {"id": "STRING"}, "primary_key": "id"},
            "SupplierLot": {"properties": {"id": "STRING"}, "primary_key": "id"},
        },
        "relations": {
            "USES_LOT": {"src": "Product", "dst": "SupplierLot", "properties": {}},
        },
    },
    "rdf_validation_source_fingerprint": "current-rdf-source",
    "query_source_fingerprint": "current-query-source",
    "handoff_source_fingerprint": "current-handoff-source",
    "handoff_manifest_files_valid": True,
}

MANIFEST_ARTIFACTS = {
    key: f"./exports/report/{key}"
    for key in (
        "report_markdown", "report_html", "snapshot_html", "snapshot_json",
        "neptune_cypher", "neptune_nodes", "neptune_edges", "rdf_ontology",
        "rdf_instances", "rdf_jsonld", "rdf_shacl", "rdf_sparql",
        "rdf_mapping", "rdf_neptune_handoff",
        "workshop_zip",
    )
}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def raises(message, fn):
    try:
        fn()
    except ValueError:
        return
    raise AssertionError(message)


def complete_workflow() -> WorkflowState:
    wf = WorkflowState()
    story = wf.add_item("user_stories", "story", {
        "actor": "Operations manager",
        "goal": "Trace affected products",
        "decision": "Choose which lots to quarantine",
        "success_metric": "Answer the trace within ten minutes",
        "scope": "One product-lot trace scenario in this one-day workshop",
        "priority": "high",
        "status": "confirmed",
    })
    discovery_claim = wf.add_item("claims", "claim", {
        "text": "The manager traces a product to supplier lots using inspection records.",
        "stage": "discovery",
        "story_ids": [story["id"]],
        "definitions": {"Product": "An item subject to lot traceability"},
        "status": "candidate",
    })
    wf.decide_item("claims", discovery_claim["id"], "confirm",
                   note="Domain owner confirmed the scenario and working term.")
    wf.add_item("domain_events", "event", {
        "name": "LotQuarantined",
        "trigger": "A confirmed inspection failure",
        "state_change": "The lot changes from available to quarantined",
        "modeling_decision": "event_node",
        "status": "confirmed",
    })
    question = wf.add_item("competency_questions", "question", {
        "question": "Which Product instances use each SupplierLot instance?",
        "expected_answer_shape": ["Product", "SupplierLot"],
        "story_ids": [story["id"]],
        "priority": "high",
        "status": "confirmed",
    })
    for model in (
        {"kind": "entity", "name": "Product"},
        {"kind": "entity", "name": "SupplierLot"},
        {"kind": "relation", "name": "USES_LOT", "src": "Product",
         "dst": "SupplierLot"},
    ):
        wf.add_item("model_candidates", "model", {
            **model,
            "question_ids": [question["id"]],
            "status": "confirmed",
        })
    source = wf.add_item("data_sources", "source", {
        "name": "inspection_records",
        "type": "table",
        "owner": "data-platform",
        "freshness": "daily",
        "status": "confirmed",
    })
    wf.add_item("field_mappings", "mapping", {
        "source": source["name"],
        "source_field": "product_id",
        "target": "Product.id",
        "status": "available",
    })
    wf.add_item("field_mappings", "mapping", {
        "source": source["name"],
        "source_field": "supplier_lot_id",
        "target": "SupplierLot.id",
        "status": "available",
    })
    action = wf.add_item("action_items", "action", {
        "text": "Confirm the production extraction schedule.",
        "owner": "data-platform",
        "status": "open",
    })
    wf.decide_item("action_items", action["id"], "accept",
                   note="Data platform accepted the handoff follow-up.")
    wf._refresh_query_candidates(GRAPH)
    query = next(
        item for item in wf.data["validation_queries"]
        if item.get("question_id") == question["id"]
        and str(item.get("language")).lower() == "opencypher"
    )
    verification = wf.record_query_verification(
        question["question"], query["query"],
        {"ok": True, "count": 1, "columns": ["a", "r", "b"]}, GRAPH,
    )
    require(verification["updated"] == 1 and verification["qualified"] == 1,
            "matching query seed was not verified")
    wf.generate_review(GRAPH)
    for stage in STAGES[1:]:
        transition = wf.advance(stage=stage, context=GRAPH)
        require(transition["ok"], f"complete fixture could not advance to {stage}")
    wf.record_handoff_manifest({
        "source_fingerprint": GRAPH["handoff_source_fingerprint"],
        "artifacts": MANIFEST_ARTIFACTS,
    })
    return wf


def test_legal_transitions():
    wf = WorkflowState()
    original = wf.data["current_stage"]
    raises("answer must not jump stages", lambda: wf.record_answer("skip", "validation_handoff"))
    require(wf.data["current_stage"] == original, "rejected answer mutated current stage")
    raises("advance must not skip stages", lambda: wf.advance("model_synthesis", True, {}, "skip"))
    raises("force must require a reason", lambda: wf.advance(force=True))
    forced = wf.advance(force=True, reason="Facilitator records an explicit scope exception")
    require(forced["stage"] == "discovery", "force did not move exactly one stage")
    require(forced["transition"]["reason"], "force reason was not preserved")
    require(wf.data["transition_history"], "transition history was not preserved")
    raises("backward transition must be rejected", lambda: wf.advance("inception", True, {}, "back"))
    before = wf.data["current_stage"]
    claim = wf.record_answer("A current-stage scenario", "discovery")
    require(claim["stage"] == before == wf.data["current_stage"],
            "answer changed the workflow stage")

    extracted = WorkflowState()
    result = extracted.process_answer(
        "Capture a structured story now.", "inception", extracted={
            "user_stories": [{
                "actor": "Owner", "goal": "Decide", "decision": "Choose",
                "success_metric": "One hour", "scope": "One-day scenario",
                "priority": "high", "stage": "validation_handoff",
            }],
        })
    story = result["added"]["user_stories"][0]
    require(story["stage"] == "inception"
            and extracted.data["current_stage"] == "inception",
            "structured answer forged future-stage provenance")


def test_quality_gates_and_happy_path():
    weak = WorkflowState()
    weak.add_item("user_stories", "story", {
        "actor": "Manager", "goal": "Improve a decision", "decision": "Choose",
        "priority": "high",
    })
    require(weak.gates(GRAPH)["inception"]["status"] != "pass",
            "story without success metric and scope passed inception")
    placeholder = WorkflowState()
    placeholder.add_item("user_stories", "story", {
        "actor": "TBD", "goal": "TBD", "decision": "TBD",
        "success_metric": "TBD", "scope": "TBD", "priority": "high",
    })
    require(placeholder.gates(GRAPH)["inception"]["status"] != "pass",
            "placeholder story fields passed inception")
    conflicting_story = complete_workflow()
    conflicting_story.data["user_stories"][0]["merge_conflicts"] = [{
        "fields": {"goal": {"existing": "Trace", "incoming": "Forecast"}},
    }]
    require(conflicting_story.gates(GRAPH)["inception"]["status"] != "pass",
            "user story with an unresolved merge conflict passed inception")
    weak.add_item("competency_questions", "question", {
        "question": "What should happen?", "priority": "high",
    })
    require(weak.gates(GRAPH)["story_to_question"]["status"] != "pass",
            "question without answer shape and story link passed")
    invalid_event = WorkflowState()
    invalid_event.add_item("domain_events", "event", {
        "name": "Changed", "trigger": "A command", "state_change": "A to B",
        "modeling_decision": "whatever",
    })
    require(invalid_event.gates(GRAPH)["event_discovery"]["status"] != "pass",
            "event with an arbitrary modeling classification passed")
    conflicting_question = complete_workflow()
    conflicting_question.data["competency_questions"][0]["merge_conflicts"] = [{
        "fields": {"priority": {"existing": "high", "incoming": "low"}},
    }]
    require(conflicting_question.gates(GRAPH)["story_to_question"]["status"] != "pass",
            "competency question with an unresolved merge conflict passed")
    weak.add_item("model_candidates", "model", {
        "kind": "entity", "name": "Orphan", "claim_id": "claim-999",
    })
    require(weak.gates(GRAPH)["model_synthesis"]["status"] != "pass",
            "unlinked model candidate passed")
    fake_link = WorkflowState()
    fake_link.add_item("model_candidates", "model", {
        "kind": "entity", "name": "Product", "question_ids": ["question-999"],
    })
    require(fake_link.gates(GRAPH)["model_synthesis"]["status"] != "pass",
            "model candidate linked to a nonexistent question passed")
    wrong_endpoints = complete_workflow()
    relation = next(
        item for item in wrong_endpoints.data["model_candidates"]
        if item.get("kind") == "relation")
    relation["src"] = "SupplierLot"
    relation["dst"] = "Product"
    endpoint_check = next(
        check for check in wrong_endpoints.gates(GRAPH)["model_synthesis"]["checks"]
        if check["id"] == "model.relation_endpoints")
    require(endpoint_check["status"] == "fail",
            "relation endpoints inconsistent with the T-Box passed model synthesis")
    wrong_kind = complete_workflow()
    relation = next(
        item for item in wrong_kind.data["model_candidates"]
        if item.get("name") == "USES_LOT")
    relation["kind"] = "entity"
    trace_check = next(
        check for check in wrong_kind.gates(GRAPH)["model_synthesis"]["checks"]
        if check["id"] == "model.graph_traceability")
    require(trace_check["status"] == "fail",
            "entity candidate with a relation name satisfied T-Box relation traceability")
    unlinked_pattern = complete_workflow()
    question_id = unlinked_pattern.data["competency_questions"][0]["id"]
    product = next(
        item for item in unlinked_pattern.data["model_candidates"]
        if item.get("name") == "Product")
    product["question_ids"] = []
    product["story_ids"] = [
        unlinked_pattern.data["user_stories"][0]["id"]
    ]
    pattern_checks = {
        check["id"]: check
        for check in unlinked_pattern.gates(GRAPH)["model_synthesis"]["checks"]
    }
    require(pattern_checks["model.question_coverage"]["status"] == "pass",
            "question-pattern bypass fixture no longer exercises global name coverage")
    require(pattern_checks["model.question_patterns"]["status"] == "fail",
            "global model names passed without a question-linked answer pattern")
    question_evidence = pattern_checks["model.question_patterns"]["evidence"][
        "questions"][0]
    require(question_evidence["question_id"] == question_id
            and question_evidence["missing_elements"] == ["Product"],
            "question-pattern gate did not identify its missing linked element")
    unlinked_relation = complete_workflow()
    relation = next(
        item for item in unlinked_relation.data["model_candidates"]
        if item.get("kind") == "relation")
    relation["question_ids"] = []
    relation["story_ids"] = [
        unlinked_relation.data["user_stories"][0]["id"]
    ]
    relation_pattern = next(
        check for check in unlinked_relation.gates(GRAPH)["model_synthesis"]["checks"]
        if check["id"] == "model.question_patterns")
    require(relation_pattern["status"] == "fail"
            and not relation_pattern["evidence"]["questions"][0][
                "linked_relation_ids"],
            "multi-element answer shape passed without a question-linked relation")
    disconnected_pattern = complete_workflow()
    disconnected_question = disconnected_pattern.data["competency_questions"][0]
    disconnected_question["expected_answer_shape"] = [
        "Product", "SupplierLot", "Inspection"]
    disconnected_pattern.add_item("model_candidates", "model", {
        "kind": "entity", "name": "Inspection",
        "question_ids": [disconnected_question["id"]],
    })
    disconnected_pattern.add_item("model_candidates", "model", {
        "kind": "entity", "name": "Audit",
        "question_ids": [disconnected_question["id"]],
    })
    disconnected_pattern.add_item("model_candidates", "model", {
        "kind": "relation", "name": "HAS_AUDIT",
        "src": "Inspection", "dst": "Audit",
        "question_ids": [disconnected_question["id"]],
    })
    disconnected_check = next(
        check for check in disconnected_pattern.gates(GRAPH)[
            "model_synthesis"]["checks"]
        if check["id"] == "model.question_patterns")
    disconnected_evidence = disconnected_check["evidence"]["questions"][0]
    require(disconnected_check["status"] == "fail"
            and "Inspection" in disconnected_evidence[
                "disconnected_elements"],
            "disconnected question-linked relation fragments passed as one graph pattern")
    fake_discovery = WorkflowState()
    fake_discovery.add_item("claims", "claim", {
        "text": "A narrative with a forged story reference.",
        "stage": "discovery", "story_ids": ["story-999"],
        "definitions": {"Term": "A working definition"},
    })
    fake_discovery.data["claims"][0]["status"] = "confirmed"
    fake_discovery.add_item("user_stories", "story", {
        "actor": "Manager", "goal": "Decide", "decision": "Choose",
        "success_metric": "Within one hour", "scope": "One-day case",
        "priority": "high",
    })
    require(fake_discovery.gates(GRAPH)["discovery"]["status"] != "pass",
            "discovery claim linked to a nonexistent story passed")
    weak.add_item("data_sources", "source", {"name": "unknown_source"})
    weak.add_item("field_mappings", "mapping", {
        "source": "unknown_source", "source_field": "f", "target": "TBD.f",
        "status": "unknown",
    })
    require(weak.gates(GRAPH)["data_grounding"]["status"] != "pass",
            "unknown TBD mapping passed")
    invalid_property = complete_workflow()
    invalid_property.data["field_mappings"][0]["target"] = "Product.not_a_property"
    mapping_check = next(
        check for check in invalid_property.gates(GRAPH)["data_grounding"]["checks"]
        if check["id"] == "data.mappings")
    require(mapping_check["status"] == "fail",
            "mapping to a nonexistent T-Box property passed data grounding")
    unknown_source_field = complete_workflow()
    unknown_source_field.data["data_sources"][0]["fields"] = {
        "supplier_lot_id": "STRING",
    }
    source_field_check = next(
        check for check in unknown_source_field.gates(GRAPH)["data_grounding"]["checks"]
        if check["id"] == "data.mappings")
    require(source_field_check["status"] == "fail",
            "mapping from a field absent in the supplied source schema passed")

    complete = complete_workflow()
    gates = complete.gates(GRAPH)
    for stage in STAGES:
        require(gates[stage]["status"] == "pass",
                f"complete evidence did not pass {stage}: {gates[stage]['missing']}")
        require(gates[stage].get("checks"), f"{stage} did not expose gate checks")
    require(complete.to_dict(GRAPH)["progress"]["percent"] == 100,
            "complete workflow did not reach 100 percent")
    skipped_navigation = complete_workflow()
    skipped_navigation.data["current_stage"] = "inception"
    stage_check = next(
        check for check in skipped_navigation.gates(GRAPH)[
            "validation_handoff"]["checks"]
        if check["id"] == "handoff.stage")
    require(stage_check["status"] == "fail",
            "direct evidence injection completed handoff without stage progression")
    forged_navigation = complete_workflow()
    forged_navigation.data["transition_history"] = []
    forged_stage_check = next(
        check for check in forged_navigation.gates(GRAPH)[
            "validation_handoff"]["checks"]
        if check["id"] == "handoff.stage")
    require(forged_stage_check["status"] == "fail",
            "final-stage label without the canonical transition chain opened handoff")


def test_query_and_validation_bypasses():
    injected = WorkflowState()
    poisoned = injected.add_item("validation_queries", "query", {
        "question_id": "question-001", "question": "Injected",
        "language": "openCypher", "query": "RETURN 1 AS ok",
        "status": "verified", "readiness": "verified",
        "verification_evidence": [{"ok": True, "query_match": True}],
    })
    require(poisoned["status"] == "candidate"
            and not poisoned.get("verification_evidence"),
            "client injected forged query verification evidence")

    wf = complete_workflow()
    for query in wf.data["validation_queries"]:
        if str(query.get("language")).lower() == "opencypher":
            query["status"] = "candidate"
            query["verification_evidence"] = []
    question = wf.data["competency_questions"][0]
    arbitrary = wf.record_query_verification(
        question["question"], "RETURN 1 AS ok", {"ok": True, "count": 1}, GRAPH)
    require(arbitrary["updated"] == 0, "arbitrary successful query matched a workflow seed")
    require(wf.gates(GRAPH)["validation_handoff"]["status"] != "pass",
            "arbitrary query opened handoff")

    missing_question = complete_workflow()
    open_query = next(
        query for query in missing_question.data["validation_queries"]
        if str(query.get("language")).lower() == "opencypher")
    open_query["status"] = "candidate"
    open_query["verification_evidence"] = []
    unmatched = missing_question.record_query_verification(
        "", open_query["query"], {"ok": True, "count": 1}, GRAPH)
    require(unmatched["updated"] == 0,
            "query verification succeeded without the required question match")

    malicious_seed = complete_workflow()
    open_query = next(
        query for query in malicious_seed.data["validation_queries"]
        if str(query.get("language")).lower() == "opencypher")
    open_query["query"] = "RETURN 1 AS ok"
    open_query["status"] = "candidate"
    open_query["verification_evidence"] = []
    qtext = malicious_seed.data["competency_questions"][0]["question"]
    matched = malicious_seed.record_query_verification(
        qtext, "RETURN 1 AS ok", {"ok": True, "count": 1}, GRAPH)
    require(matched["updated"] == 1,
            "test precondition: stored arbitrary seed did not match itself")
    require(matched["qualified"] == 0
            and matched["evidence"]["answer_shape_match"] is False,
            "irrelevant execution was returned as qualified evidence")
    require(malicious_seed.gates(GRAPH)["validation_handoff"]["status"] != "pass",
            "stored RETURN 1 seed opened handoff without answer-shape coverage")
    require(open_query["status"] == "failed"
            and open_query["readiness"] == "needs_fix",
            "irrelevant RETURN 1 execution was displayed as verified")

    alias_seed = complete_workflow()
    alias_query = next(
        query for query in alias_seed.data["validation_queries"]
        if str(query.get("language")).lower() == "opencypher")
    alias_query["query"] = (
        "MATCH (n) WITH n AS Product, n AS SupplierLot RETURN 1 AS ok")
    alias_query["status"] = "candidate"
    alias_query["verification_evidence"] = []
    alias_seed.record_query_verification(
        alias_seed.data["competency_questions"][0]["question"],
        alias_query["query"], {"ok": True, "count": 1}, GRAPH)
    alias_coverage = next(
        check for check in alias_seed.gates(GRAPH)["validation_handoff"]["checks"]
        if check["id"] == "handoff.query_coverage")
    require(alias_coverage["status"] == "fail",
            "answer-shape names used only as aliases made RETURN 1 look relevant")
    require(alias_query["status"] == "failed",
            "alias-only answer-shape query was displayed as verified")

    text_only_link = complete_workflow()
    text_query = next(
        query for query in text_only_link.data["validation_queries"]
        if str(query.get("language")).lower() == "opencypher")
    text_query.pop("question_id", None)
    text_link_coverage = next(
        check for check in text_only_link.gates(GRAPH)[
            "validation_handoff"]["checks"]
        if check["id"] == "handoff.query_coverage")
    require(text_link_coverage["status"] == "fail",
            "query linked only by mutable question text satisfied coverage")

    comment_seed = complete_workflow()
    comment_query = next(
        query for query in comment_seed.data["validation_queries"]
        if str(query.get("language")).lower() == "opencypher")
    comment_query["query"] = "MATCH (n) RETURN n // Product SupplierLot"
    comment_query["status"] = "candidate"
    comment_query["verification_evidence"] = []
    comment_seed.record_query_verification(
        comment_seed.data["competency_questions"][0]["question"],
        comment_query["query"], {"ok": True, "count": 1}, GRAPH)
    require(comment_seed.gates(GRAPH)["validation_handoff"]["status"] != "pass",
            "answer-shape names in a query comment opened handoff")

    cartesian_seed = complete_workflow()
    cartesian_query = next(
        query for query in cartesian_seed.data["validation_queries"]
        if str(query.get("language")).lower() == "opencypher")
    cartesian_query["query"] = (
        "MATCH (p:Product), (lot:SupplierLot) RETURN p, lot")
    cartesian_query["status"] = "candidate"
    cartesian_query["verification_evidence"] = []
    cartesian = cartesian_seed.record_query_verification(
        cartesian_seed.data["competency_questions"][0]["question"],
        cartesian_query["query"], {"ok": True, "count": 1}, GRAPH)
    require(cartesian["qualified"] == 0
            and cartesian_seed.gates(GRAPH)["validation_handoff"]["status"] != "pass",
            "disconnected Cartesian MATCH was accepted as relationship evidence")

    many_shape = WorkflowState()
    question_item = many_shape.add_item("competency_questions", "question", {
        "question": "Which products use lots with inspections?",
        "expected_answer_shape": ["Product", "SupplierLot", "Inspection"],
        "priority": "high",
    })
    many_shape._refresh_query_candidates({
        "graph": {"entities": 3, "relations": 2},
    })
    generated = next(
        query for query in many_shape.data["validation_queries"]
        if str(query.get("language")).lower() == "opencypher")
    require("Inspection" in generated["query"]
            and "n2" in generated["query"]
            and _query_covers_answer_shape(generated, question_item),
            "generated query seed omitted or disconnected a third answer-shape element")

    warned = complete_workflow()
    warned.record_static_validation({
        "status": "warning", "source_fingerprint": "current-rdf-source",
        "counts": {"passed": 16, "warnings": 3, "failed": 0},
        "sparql": {"status": "warning", "query_count": 0},
    })
    require(warned.gates(GRAPH)["validation_handoff"]["status"] != "pass",
            "warning-only static validation opened handoff")
    empty_context = dict(GRAPH, graph={"entities": 0, "relations": 0, "nodes": 0, "edges": 0})
    warned.data["last_validation"]["status"] = "pass"
    require(warned.gates(empty_context)["validation_handoff"]["status"] != "pass",
            "empty-model static validation opened handoff")

    stale_query = complete_workflow()
    changed = dict(GRAPH, rdf_validation_source_fingerprint="changed-model",
                   query_source_fingerprint="changed-query-model",
                   handoff_source_fingerprint="changed-handoff")
    require(stale_query.gates(changed)["validation_handoff"]["status"] != "pass",
            "query evidence from an older model opened handoff")
    stale_payload = stale_query.to_dict(changed)
    stale_open_query = next(
        item for item in stale_payload["validation_queries"]
        if str(item.get("language")).lower() == "opencypher")
    require(stale_open_query["effective_status"] == "stale"
            and stale_open_query["verification_freshness"] == "stale",
            "stale query evidence remained visually verified")
    require(not stale_query.current_query_evidence(changed),
            "stale query evidence remained eligible for report handoff")

    changed_mapping = complete_workflow()
    old_query_fingerprint = GRAPH["query_source_fingerprint"]
    changed_mapping.data["field_mappings"][0]["target"] = "Product.external_id"
    changed_mapping_context = dict(
        GRAPH, query_source_fingerprint="mapping-changed-query-source")
    require(not changed_mapping.current_query_evidence(changed_mapping_context),
            "data-mapping change did not stale query evidence")
    require(old_query_fingerprint != changed_mapping_context["query_source_fingerprint"],
            "test precondition did not change query fingerprint")

    missing_file = complete_workflow()
    invalid_files = dict(GRAPH, handoff_manifest_files_valid=False)
    require(missing_file.gates(invalid_files)["validation_handoff"]["status"] != "pass",
            "manifest with missing files opened handoff")


def test_review_lifecycle_and_merge_policy():
    blank = WorkflowState()
    blank.generate_review({})
    require(blank.gates({})["adversarial_review"]["status"] != "pass",
            "reviewing a blank state opened the adversarial-review gate")

    medium = complete_workflow()
    finding = medium.add_item("review_findings", "finding", {
        "text": "A bounded review item still needs a human disposition.",
        "category": "ambiguity", "severity": "medium", "status": "open",
        "source": "automatic_adversarial_review",
    })
    require(medium.gates(GRAPH)["adversarial_review"]["status"] != "pass",
            "an unresolved automatic medium finding opened the review gate")
    medium.decide_item("review_findings", finding["id"], "accept",
                       note="Domain owner accepts the documented limitation")
    require(medium.gates(GRAPH)["adversarial_review"]["status"] == "pass",
            "explicitly accepted medium finding remained blocking")

    wf = WorkflowState()
    source = wf.add_unique_item("data_sources", "source", {
        "name": "orders", "owner": "team-a",
    })
    merged = wf.add_unique_item("data_sources", "source", {
        "name": "orders", "owner": "team-b",
    })
    require(source["id"] == merged["id"] and merged["owner"] == "team-a",
            "deduplication silently overwrote an existing value")
    require(merged.get("merge_conflicts"), "deduplication hid a conflicting value")

    mapping = wf.add_unique_item("field_mappings", "mapping", {
        "source": "orders", "source_field": "id", "target": "Order.id",
        "status": "available",
    })
    wf.add_unique_item("field_mappings", "mapping", {
        "source": "orders", "source_field": "id", "target": "Order.id",
        "status": "missing",
    })
    require(mapping["status"] == "available" and mapping.get("merge_conflicts"),
            "mapping readiness conflict was overwritten or hidden")

    risk = wf.add_item("risks", "risk", {
        "text": "A critical privacy decision is unresolved.",
        "severity": "high", "status": "open",
    })
    raises("high-risk acceptance must require an owned action",
           lambda: wf.decide_item(
               "risks", risk["id"], "accept",
               note="Track the accepted risk after the workshop"))
    raises("workflow decisions must retain a justification",
           lambda: wf.decide_item("risks", risk["id"], "reject"))
    accepted = wf.decide_item(
        "risks", risk["id"], "accept", note="Track after workshop",
        linked_action={"text": "Obtain privacy approval", "owner": "privacy-team"})
    require(accepted["status"] == "accepted" and accepted.get("linked_action_ids"),
            "accepted risk was not linked to an owned action")
    require(accepted.get("history"), "review decision history was not retained")
    require(accepted["linked_action_ids"] == accepted["history"][-1]["after"]["linked_action_ids"],
            "review decision after-history omitted its linked action")
    raises("review classification changes must be justified",
           lambda: wf.decide_item("risks", risk["id"], "update",
                                  changes={"severity": "medium"}))
    revised = wf.decide_item(
        "risks", risk["id"], "update", changes={"severity": "medium"},
        note="The privacy owner reclassified impact after reviewing the fields.")
    require(revised["severity"] == "medium"
            and revised["history"][-1]["before"]["severity"] == "high",
            "audited review classification correction was not retained")
    revision_target = wf.add_item("claims", "claim", {
        "text": "An imprecise claim", "status": "candidate",
    })
    revised_claim = wf.decide_item(
        "claims", revision_target["id"], "revise",
        changes={"text": "A precise, revised claim"},
        note="The domain owner requested this corrected wording.")
    require(revised_claim["status"] == "revision_requested"
            and revised_claim["text"] == "A precise, revised claim",
            "revise did not apply supplied changes with revision status")

    claim_a = wf.add_item("claims", "claim", {
        "text": "A term is defined one way", "subject": "Account",
        "value": "A customer login", "status": "conflicting",
    })
    claim_b = wf.add_item("claims", "claim", {
        "text": "The same term is defined differently", "subject": "Account",
        "value": "A billing contract", "status": "conflicting",
        "conflict_ids": [claim_a["id"]],
    })
    claim_a["conflict_ids"] = [claim_b["id"]]
    review = wf.generate_review(GRAPH)
    require(review["contradictions"], "semantic claim contradiction was not detected")
    contradiction = review["contradictions"][0]
    require(contradiction["severity"] == "critical", "contradiction was not critical")
    require(wf.gates(GRAPH)["adversarial_review"]["status"] != "pass",
            "unresolved critical contradiction opened the review gate")
    wf.decide_item("contradictions", contradiction["id"], "resolve",
                   note="Domain owner selected the billing-contract definition")
    require(contradiction["status"] == "resolved", "contradiction was not resolved")

    current = complete_workflow()
    require(current.gates(GRAPH)["adversarial_review"]["status"] == "pass",
            "current bounded review should pass with no open high/critical issue")
    current.add_item("claims", "claim", {
        "text": "Material evidence added after review", "stage": "discovery",
        "story_ids": [current.data["user_stories"][0]["id"]],
    })
    require(current.gates(GRAPH)["adversarial_review"]["status"] != "pass",
            "review did not become stale after material evidence changed")

    schema_review = complete_workflow()
    schema_v1 = dict(GRAPH, tbox={
        "entities": {"Product": {"properties": {"id": "STRING"}}},
        "relations": {"USES_LOT": {"src": "Product", "dst": "SupplierLot"}},
    })
    schema_v2 = dict(GRAPH, tbox={
        "entities": {"Product": {"properties": {"id": "INT64"}}},
        "relations": {"USES_LOT": {"src": "Product", "dst": "SupplierLot"}},
    })
    schema_review.generate_review(schema_v1)
    freshness = next(
        check for check in schema_review.gates(schema_v2)["adversarial_review"]["checks"]
        if check["id"] == "review.freshness")
    require(freshness["status"] == "fail",
            "T-Box property change did not make the adversarial review stale")

    incomplete_manifest = WorkflowState()
    manifest = incomplete_manifest.record_handoff_manifest({
        "status": "complete", "source_fingerprint": "forged",
        "artifacts": {"report_markdown": "./exports/report/report.md"},
    })
    require(manifest["status"] == "incomplete" and manifest["missing_artifacts"],
            "partial handoff manifest retained a forged complete status")

    empty_action = complete_workflow()
    empty_action.data["action_items"] = [{
        "id": "action-empty", "owner": "some-team", "status": "open",
    }]
    action_check = next(
        check for check in empty_action.gates(GRAPH)["validation_handoff"]["checks"]
        if check["id"] == "handoff.actions")
    require(action_check["status"] == "fail",
            "owner-only empty action item satisfied the handoff gate")
    confirmed_action = complete_workflow()
    confirmed_action.data["action_items"][0]["status"] = "confirmed"
    confirmed_action_check = next(
        check for check in confirmed_action.gates(GRAPH)["validation_handoff"]["checks"]
        if check["id"] == "handoff.actions")
    require(confirmed_action_check["status"] == "pass",
            "confirmed owner-tagged action stopped counting as handoff evidence")

    scope_change = complete_workflow()
    before_scope = scope_change.handoff_source_fingerprint("graph-source")
    scope_change.data["scope"] = "A materially different workshop scope"
    require(scope_change.handoff_source_fingerprint("graph-source") != before_scope,
            "workshop scope change did not stale the handoff fingerprint")


def test_persistence_and_start_semantics():
    wf = WorkflowState()
    wf.advance(force=True, reason="Explicit facilitator exception")
    stage = wf.data["current_stage"]
    wf.start(language="en", scope="Updated scope without reset", reset=False)
    require(wf.data["current_stage"] == stage,
            "workflow/start silently reset a non-reset session to inception")
    loaded = WorkflowState(wf.to_dict(GRAPH))
    require(loaded.data["transition_history"] == wf.data["transition_history"],
            "transition history was not preserved by load")
    require("contradictions" in loaded.data and "review_runs" in loaded.data,
            "new workflow lifecycle collections were not preserved")

    complete = complete_workflow()
    before_fingerprint = complete.handoff_source_fingerprint("roundtrip-graph")
    restored = WorkflowState(complete.to_dict(GRAPH))
    require(restored.handoff_source_fingerprint("roundtrip-graph")
            == before_fingerprint,
            "snapshot view fields changed the handoff fingerprint after restore")
    restored_query = next(
        item for item in restored.data["validation_queries"]
        if str(item.get("language")).lower() == "opencypher")
    require("effective_status" not in restored_query
            and "verification_freshness" not in restored_query,
            "view-only query fields leaked into canonical restored evidence")


def main():
    test_legal_transitions()
    test_quality_gates_and_happy_path()
    test_query_and_validation_bypasses()
    test_review_lifecycle_and_merge_policy()
    test_persistence_and_start_semantics()
    print("AI-ODLC workflow quality and bypass checks passed")


if __name__ == "__main__":
    main()
